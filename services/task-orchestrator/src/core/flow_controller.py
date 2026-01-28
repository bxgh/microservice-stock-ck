import logging
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiomysql
import re

from core.workflow_parser import WorkflowDefinition, WorkflowStep, StepType, RetryPolicy
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.schemas import DiagnosisResult

logger = logging.getLogger(__name__)

class FlowController:
    """
    Workflow 4.0 Engine: Database-backed flow control with AI diagnosis.
    Manages workflow_runs and task_commands.
    """
    
    def __init__(self, mysql_pool, docker_client, agent_engine: SmartDecisionEngine):
        self.mysql_pool = mysql_pool
        self.docker_client = docker_client
        self.agent = agent_engine
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("🚀 FlowController started")

    async def _loop(self):
        while self._running:
            try:
                await self._monitor_running_commands()
                await self._process_active_runs()
            except Exception as e:
                logger.error(f"FlowController loop error: {e}")
            await asyncio.sleep(10)

    async def create_run(self, workflow_id: str, definition: WorkflowDefinition, initial_context: Dict[str, Any] = None) -> str:
        """Create a new workflow run instance"""
        run_id = str(uuid.uuid4())
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO alwaysup.workflow_runs (run_id, workflow_id, status, context) VALUES (%s, %s, %s, %s)",
                    (run_id, workflow_id, "RUNNING", json.dumps(initial_context or {}))
                )
                await conn.commit()
        logger.info(f"✨ Created workflow run {run_id} for {workflow_id}")
        return run_id

    async def _process_active_runs(self):
        """Find RUNNING workflows and advance them"""
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    "SELECT r.run_id, r.workflow_id, r.context, d.definition "
                    "FROM alwaysup.workflow_runs r "
                    "JOIN alwaysup.workflow_definitions d ON r.workflow_id = d.id "
                    "WHERE r.status = 'RUNNING'"
                )
                runs = await cursor.fetchall()
                logger.info(f"🔍 Found {len(runs)} active runs: {[r['run_id'] for r in runs]}")
                
                for run in runs:
                    try:
                        await self._advance_run(run)
                    except Exception as e:
                        logger.error(f"Failed to advance run {run['run_id']}: {e}")

    async def _advance_run(self, run: Dict[str, Any]):
        """Analyze current state of a run and emit next steps"""
        run_id = run['run_id']
        logger.info(f"⏩ Advancing run {run_id} ({run['workflow_id']})")
        
        definition = run['definition']
        if isinstance(definition, str):
            definition = json.loads(definition)
        wf_def = WorkflowDefinition.model_validate(definition)
        
        context = run['context'] or {}
        if isinstance(context, str):
            context = json.loads(context)
        
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 1. Get all commands for this run
                await cursor.execute(
                    "SELECT step_id, status, output_context FROM alwaysup.task_commands WHERE run_id = %s",
                    (run_id,)
                )
                commands = await cursor.fetchall()
                cmd_map = {c['step_id']: c for c in commands}
                
                # 2. Check for overall completion or terminal failure
                all_done = True
                any_failed_permanently = False
                
                for step in wf_def.steps:
                    cmd = cmd_map.get(step.id)
                    if not cmd or cmd['status'] != 'DONE':
                        all_done = False
                    
                    if cmd and cmd['status'] == 'FAILED':
                        # If a mandatory step failed and AI didn't retry it (or exhausted retries),
                        # the workflow might be stuck or failed.
                        # For now, if AI diagnosed as something else than RETRY, we might consider it failed.
                        # However, to keep it simple: if all dependencies of a terminal set of steps can't be met, it fails.
                        pass

                if all_done:
                    logger.info(f"🏁 Workflow run {run_id} COMPLETED")
                    await cursor.execute(
                        "UPDATE alwaysup.workflow_runs SET status = 'COMPLETED', end_time = %s WHERE run_id = %s",
                        (datetime.now(), run_id)
                    )
                    await conn.commit()
                    return

                # 3. Find ready steps
                logger.info(f"🔍 Run {run_id} checking {len(wf_def.steps)} steps. Commands in DB: {list(cmd_map.keys())}")
                for step in wf_def.steps:
                    if step.id in cmd_map:
                        logger.debug(f"  ▪ Step '{step.id}' already exists (status: {cmd_map[step.id]['status']})")
                        continue # Already emitted/running/done
                    
                    # Check dependencies
                    deps_met = True
                    for dep_id in step.depends_on:
                        dep_cmd = cmd_map.get(dep_id)
                        if not dep_cmd or dep_cmd['status'] != 'DONE':
                            logger.info(f"  ▪ Step '{step.id}' waiting for '{dep_id}' (not DONE)")
                            deps_met = False
                            break
                    
                    if deps_met:
                        logger.info(f"  ✅ Step '{step.id}' is READY to emit!")
                        await self._emit_step(run_id, step, context)
                        return # Only emit one step per loop

    async def _emit_step(self, run_id: str, step: WorkflowStep, context: Dict[str, Any]):
        """Create a command for a workflow step"""
        logger.info(f"📤 Emitting step {step.id} for run {run_id}")
        
        # Prepare input context for the step
        input_ctx = context.copy()
        
        # Resolve parameters from context using simple regex-like search & replace
        resolved_params = {}
        for k, v in step.params.items():
            if isinstance(v, str):
                # 编译正则以支持 {{ var }} 带空格的情况
                # 执行正则替换
                def replacer(match):
                    var_name = match.group(1).strip()
                    logger.info(f"🔍 Searching for variable '{var_name}' in context keys: {list(context.keys())}")
                    
                    # 1. Try Direct Lookup
                    if var_name in context:
                        val = context[var_name]
                        logger.info(f"✅ Resolved param '{k}': {match.group(0)} -> {val}")
                        return str(val)
                    
                    if "." in var_name:
                        parts = var_name.split(".")
                        # Try to find a key that matches a prefix of the variable name
                        # E.g. "audit_decision.output.confirmed_bad_codes" -> Try "audit_decision.output" key
                        for i in range(len(parts), 0, -1):
                            prefix = ".".join(parts[:i])
                            if prefix in context:
                                current = context[prefix]
                                remaining_parts = parts[i:]
                                found_prop = True
                                for part in remaining_parts:
                                    if isinstance(current, dict) and part in current:
                                        current = current[part]
                                    elif hasattr(current, part):
                                        current = getattr(current, part)
                                    else:
                                        found_prop = False
                                        break
                                
                                if found_prop:
                                    logger.info(f"✅ Resolved param '{k}' via prefix '{prefix}': {var_name} -> {current}")
                                    return str(current)

                    logger.warning(f"⚠️ Variable '{var_name}' not found in context for step {step.id}")
                    return match.group(0)

                resolved_v = re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, v)
                
                # 如果是精准匹配 "{{var}}"，尝试恢复原始类型 (int/float/bool)
                if re.fullmatch(r"\{\{\s*(.*?)\s*\}\}", v.strip()):
                    var_name = re.search(r"\{\{\s*(.*?)\s*\}\}", v).group(1).strip()
                    
                    found_val = None
                    if var_name in context:
                        found_val = context[var_name]
                    elif "." in var_name: 
                         # Try traversal for exact match too
                        parts = var_name.split(".")
                        for i in range(len(parts), 0, -1):
                            prefix = ".".join(parts[:i])
                            if prefix in context:
                                current = context[prefix]
                                remaining_parts = parts[i:]
                                found_prop = True
                                for part in remaining_parts:
                                    if isinstance(current, dict) and part in current:
                                        current = current[part]
                                    elif hasattr(current, part):
                                        current = getattr(current, part)
                                    else:
                                        found_prop = False
                                        break
                                
                                if found_prop:
                                    found_val = current
                                    break

                    if found_val is not None:
                        resolved_v = found_val
                        logger.info(f"💎 Restored original type for '{k}': {type(resolved_v)}")
                
                resolved_params[k] = resolved_v
            else:
                resolved_params[k] = v
        
        logger.info(f"🔄 Final resolved params for {step.id}: {resolved_params}")

        
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                task_id = step.task_id or step.id
                await cursor.execute(
                    "INSERT INTO alwaysup.task_commands (run_id, step_id, task_id, params, input_context, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (run_id, step.id, task_id, json.dumps(resolved_params), json.dumps(input_ctx), "PENDING")
                )
                await conn.commit()

    async def _monitor_running_commands(self):
        """Check for FAILED commands and trigger AI diagnosis"""
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # Find FAILED commands in an active workflow that haven't been diagnosed yet
                # We use a special result prefix or a new field to track diagnosis
                await cursor.execute(
                    "SELECT c.*, r.workflow_id "
                    "FROM alwaysup.task_commands c "
                    "JOIN alwaysup.workflow_runs r ON c.run_id = r.run_id "
                    "WHERE c.status = 'FAILED' AND r.status = 'RUNNING' "
                    "AND c.result NOT LIKE 'AI_DIAGNOSED:%'"
                )
                failed_cmds = await cursor.fetchall()
                
                for cmd in failed_cmds:
                    await self._diagnose_and_recover(cmd)

                # Find DONE commands and merge their output_context back to workflow_runs
                # Logic: Only merge if not already merged? 
                # Let's use a simpler way: periodically update RUNNING workflow contexts from their commands
                await cursor.execute(
                    "SELECT run_id, context FROM alwaysup.workflow_runs WHERE status = 'RUNNING'"
                )
                runs = await cursor.fetchall()
                for run in runs:
                    rid = run['run_id']
                    current_ctx = json.loads(run['context']) if isinstance(run['context'], str) else run['context']
                    
                    await cursor.execute(
                        "SELECT step_id, output_context FROM alwaysup.task_commands WHERE run_id = %s AND status = 'DONE'",
                        (rid,)
                    )
                    outputs = await cursor.fetchall()
                    
                    merged = current_ctx.copy()
                    for out in outputs:
                        out_ctx = out['output_context']
                        if out_ctx:
                            if isinstance(out_ctx, str):
                                out_ctx = json.loads(out_ctx)
                            # 存储为 step_id.output 支持 Workflow 表达式
                            obj_key = f"{out['step_id']}.output"
                            merged[obj_key] = out_ctx
                            logger.info(f"➕ Added step output key: {obj_key}")
                            # 同时保留顶级 Key 兼容性 (可选)
                            if isinstance(out_ctx, dict):
                                merged.update(out_ctx)
                    
                    if merged != current_ctx:
                        logger.info(f"🔄 Merging context for run {rid}")
                        await cursor.execute(
                            "UPDATE alwaysup.workflow_runs SET context = %s WHERE run_id = %s",
                            (json.dumps(merged), rid)
                        )
                await conn.commit()

    async def _diagnose_and_recover(self, cmd: Dict[str, Any]):
        """ engage gsd-agent to decide what to do with a failed step """
        cmd_id = cmd['id']
        task_id = cmd['task_id']
        error_logs = ""
        output_ctx = cmd.get('output_context') or {}
        if isinstance(output_ctx, str):
            output_ctx = json.loads(output_ctx)
        
        error_logs = output_ctx.get("error_logs", "") or cmd.get('result', "")
        
        logger.info(f"🧠 AI Diagnosing failure for command #{cmd_id} ({task_id})")
        
        try:
            diagnosis: DiagnosisResult = await self.agent.run(
                prompt_template="ops_diagnosis",
                inputs={
                    "task_name": task_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "logs": error_logs
                },
                response_model=DiagnosisResult,
                priority="fast"
            )
            
            logger.info(f"🤖 AI Diagnosis: {diagnosis.action_type} - {diagnosis.reasoning}")
            
            async with self.mysql_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Mark as diagnosed
                    await cursor.execute(
                        "UPDATE alwaysup.task_commands SET result = %s WHERE id = %s",
                        (f"AI_DIAGNOSED: {diagnosis.action_type} | {diagnosis.reasoning}", cmd_id)
                    )
                    
                    if diagnosis.action_type in ["RETRY_IMMEDIATE", "RETRY_WITH_PROXY"]:
                        # Clone command to RETRY
                        logger.info(f"🔄 AI requested RETRY for {task_id}")
                        await cursor.execute(
                            "INSERT INTO alwaysup.task_commands (run_id, step_id, task_id, params, input_context, status) "
                            "SELECT run_id, step_id, task_id, params, input_context, 'PENDING' "
                            "FROM alwaysup.task_commands WHERE id = %s",
                            (cmd_id,)
                        )
                    elif diagnosis.action_type == "SKIP":
                        logger.warning(f"⏭️ AI requested SKIP for {task_id}")
                        await cursor.execute(
                            "UPDATE alwaysup.task_commands SET status = 'DONE', result = %s WHERE id = %s",
                            (f"AI_SKIPPED: {diagnosis.reasoning}", cmd_id)
                        )
                    
                    await conn.commit()
                    
        except Exception as e:
            logger.error(f"AI Diagnosis failed for cmd #{cmd_id}: {e}")
