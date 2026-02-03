import asyncio
import logging
import os
import re
import json
from datetime import datetime
import aiomysql
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class CommandPoller:
    """
    轮询云端 MySQL 的 task_commands 表，执行待处理命令。
    仅当 status='PENDING' 时提取并执行。
    """
    
    def __init__(self, mysql_pool, scheduler, docker_client=None, task_config=None, poll_interval: int = 15, shard_id: Optional[int] = None, flow_controller=None):
        self.mysql_pool = mysql_pool
        self.scheduler = scheduler
        self.docker_client = docker_client
        self.task_config = task_config
        self.poll_interval = poll_interval
        self.shard_id = shard_id
        self.flow_controller = flow_controller
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动轮询"""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"🔄 CommandPoller 启动，轮询间隔 {self.poll_interval}s")
    
    async def stop(self):
        """停止轮询"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 CommandPoller 已停止")
    
    async def _loop(self):
        while self._running:
            try:
                await self._poll_and_execute()
            except Exception as e:
                logger.error(f"CommandPoller 轮询异常: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _poll_and_execute(self):
        # 注意: 这里使用 aiomysql 连接池
        # 假设 alwaysup 是 cloud 库，需要在 settings.py 确认是否配置了云端库连接
        # 如果当前 mysql_pool 连接的是本地库，则需要使用不同的连接或确保该池可访问云端库(通过隧道)
        # 根据设计，task-orchestrator 应连接到云端库 (通过 36301 端口隧道)
        
        tasks_count = len(self.task_config.tasks)
        task_ids = [t.id for t in self.task_config.tasks]
        logger.info(f"🔎 CommandPoller checking for tasks... (Count: {tasks_count}, IDs: {task_ids})")
        
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 1. 获取针对当前分片的 PENDING 命令 (FOR UPDATE 锁行)
                if self.shard_id is None:
                    # 主控节点: 处理全局任务 (无 shard_id/shard_index) 或 Shard 0 任务
                    sql = """
                        SELECT id, run_id, task_id, params, input_context 
                        FROM alwaysup.task_commands 
                        WHERE status = 'PENDING' 
                          AND (
                              (JSON_EXTRACT(params, '$.shard_id') IS NULL AND JSON_EXTRACT(params, '$.shard_index') IS NULL)
                              OR JSON_EXTRACT(params, '$.shard_id') = 0
                              OR JSON_EXTRACT(params, '$.shard_index') = 0
                          )
                        ORDER BY created_at ASC
                        LIMIT 1 FOR UPDATE SKIP LOCKED
                    """
                    await cursor.execute(sql)
                else:
                    # 远程分片节点: 仅处理匹配自己 id 的任务
                    sql = """
                        SELECT id, run_id, task_id, params, input_context 
                        FROM alwaysup.task_commands 
                        WHERE status = 'PENDING' 
                          AND (JSON_EXTRACT(params, '$.shard_id') = %s
                               OR JSON_EXTRACT(params, '$.shard_index') = %s)
                        ORDER BY created_at ASC
                        LIMIT 1 FOR UPDATE SKIP LOCKED
                    """
                    await cursor.execute(sql, (self.shard_id, self.shard_id))
                
                cmd = await cursor.fetchone()
                
                if not cmd:
                    # [Debug] 如果没捡到任务，查一下表里到底有没有 PENDING
                    await cursor.execute("SELECT count(*) FROM alwaysup.task_commands WHERE status='PENDING'")
                    total_pending = (await cursor.fetchone())['count(*)']
                    if total_pending > 0:
                         logger.debug(f"ℹ️ Found {total_pending} PENDING tasks, but none match shard filter (shard={self.shard_id})")
                    return
                
                cmd_id = cmd['id']
                run_id = cmd.get('run_id')
                task_id = cmd['task_id']
                logger.info(f"✅ Picked Command #{cmd_id}: {task_id} (Run: {run_id})")
                params_json = cmd['params']
                input_ctx_json = cmd.get('input_context')
                
                params = {}
                if params_json:
                    try:
                        if isinstance(params_json, str):
                            params = json.loads(params_json)
                        else:
                            params = params_json
                    except Exception as e:
                        logger.warning(f"解析参数失败 #{cmd_id}: {e}")

                input_ctx = "{}"
                if input_ctx_json:
                    if isinstance(input_ctx_json, str):
                        input_ctx = input_ctx_json
                    else:
                        input_ctx = json.dumps(input_ctx_json)
                
                logger.info(f"⚡ 收到命令 #{cmd_id}: {task_id} params={params}")

                # 2. 参数标准化: shard_index -> shard_id (向后兼容)
                if params and 'shard_index' in params and 'shard_id' not in params:
                    params['shard_id'] = params['shard_index']
                    logger.debug(f"参数标准化: shard_index={params['shard_index']} -> shard_id={params['shard_id']}")

                # 3. 更新状态为 RUNNING
                await cursor.execute(
                    "UPDATE alwaysup.task_commands SET status='RUNNING', executed_at=NOW() WHERE id=%s",
                    (cmd_id,)
                )
                await conn.commit()
                
                # [Refactored V4.0] 移除 repair_tick 自动分片逻辑
                # 历史采集现由 Node 41 集中执行，不再拆分为 shard_id 任务。
                
                # 3. 执行任务
                status = "DONE"
                result = "SUCCESS"
                output_context = {}
                
                try:
                    # 查找任务定义
                    logger.info(f"🔍 CommandPoller looking for task_id: '{task_id}' (length: {len(task_id)})")
                    task_def = next((t for t in self.task_config.tasks if t.id == task_id), None)
                    if not task_def:
                        all_ids = [t.id for t in self.task_config.tasks]
                        logger.error(f"❌ 任务 '{task_id}' 未找到 in {all_ids}")
                        raise ValueError(f"任务 {task_id} 未在本地注册. 可用任务: {all_ids}")

                    # 如果是 Docker 任务且有参数，使用 DockerExecutor 动态执行
                    if params and self.docker_client and task_def.type == "docker":
                        # [Optimization] Silent Skip check
                        # If a diagnostic step (like AI Review) decides we should SKIP, 
                        # the subsequent repair step can check this 'mode' or 'repair_mode'.
                        if params.get('mode') == 'skip' or params.get('repair_mode') == 'skip':
                            logger.info(f"⏭️ Task {task_id} SILENT SKIP requested via params (mode=skip)")
                            status = "DONE"
                            result = "SKIPPED_BY_DESIGN"
                            output_context = {"skipped": True}
                        elif task_id == "repair_tick" and not (params.get('stocks') or params.get('stock_codes') or params.get('stock-codes')) and params.get('mode') == 'repair':
                            # Even if mode is not skip, empty stocks in repair mode is effectively a skip
                            logger.info(f"⏭️ Task {task_id} SILENT SKIP: Mode is 'repair' but 'stocks' list is empty.")
                            status = "DONE"
                            result = "SKIPPED_NO_STOCKS"
                            output_context = {"skipped": True}
                        else:
                            from executor.docker_executor import DockerExecutor
                            executor = DockerExecutor(self.docker_client)
                        
                            # 构建命令
                            original_cmd = task_def.target.get('command', [])
                            # 确保是 list
                            if isinstance(original_cmd, str):
                                cmd_list = original_cmd.split()
                            else:
                                cmd_list = list(original_cmd)
                                
                            # 追加参数: --key value (支持列表参数)
                            for k, v in params.items():
                                # 将下划线转换为破折号 (argparse 兼容: shard_index -> shard-index)
                                # [Fix] 强制映射 stocks -> stock-codes 以适配 repair_tick
                                if k == 'stocks':
                                    cli_key = 'stock-codes'
                                else:
                                    cli_key = k.replace('_', '-')
                                
                                cmd_list.append(f"--{cli_key}")
                                
                                if v is not None and str(v) != "":
                                    # [Refactored] 增强对字符串形式列表的支持 (针对 Workflow 传参场景)
                                    val_to_process = v
                                    is_list_processed = False
                                    
                                    # 尝试将 JSON 字符串解析为列表
                                    if isinstance(v, str) and (v.startswith('[') and v.endswith(']')):
                                        try:
                                            parsed = json.loads(v)
                                            if isinstance(parsed, list):
                                                val_to_process = parsed
                                        except:
                                            # 如果 JSON 解析失败，尝试手动去除非法字符 (针对 '["code"]' 这种可能带单引号的非标准 JSON)
                                            clean_str = v.strip("[]").replace("'", "").replace('"', "").replace(" ", "")
                                            val_to_process = clean_str.split(',')
                                            
                                    # 统一处理列表
                                    if isinstance(val_to_process, list):
                                        if k in ['stocks', 'stock_codes', 'stock-codes']:
                                            cmd_list.append(','.join(str(item) for item in val_to_process))
                                        elif k in ['data_types', 'data-types']:
                                            cmd_list.pop() # 移除刚才加的 key，因为 extend 会加多个
                                            for item in val_to_process:
                                                cmd_list.append(f"--{cli_key}")
                                                cmd_list.append(str(item))
                                        else:
                                            cmd_list.append(json.dumps(val_to_process))
                                        is_list_processed = True
                                    
                                    # 处理字典
                                    elif isinstance(val_to_process, dict):
                                        cmd_list.append(json.dumps(val_to_process))
                                        
                                    # 处理普通值
                                    else:
                                        if not is_list_processed:
                                            cmd_list.append(str(val_to_process))
                            
                            logger.info(f"🚀 动态执行任务 {task_id}: {cmd_list}")
                        
                            # 执行容器
                            
                            # 准备挂载 (从 task_def 获取)
                            volumes_config = {}
                            if self.task_config and self.task_config.global_ and self.task_config.global_.docker:
                                default_vols = self.task_config.global_.docker.get('default_volumes', [])
                                for v in default_vols:
                                    parts = v.split(':')
                                    if len(parts) >= 2:
                                        host_path = parts[0]
                                        if host_path.startswith('.'):
                                            host_path = os.path.join(settings.HOST_BASE_DIR, host_path.lstrip('./'))
                                        volumes_config[host_path] = {'bind': parts[1], 'mode': parts[2] if len(parts) > 2 else 'rw'}
    
                            task_vols = task_def.target.get('volumes', [])
                            for v in task_vols:
                                parts = v.split(':')
                                if len(parts) >= 2:
                                    host_path = parts[0]
                                    if host_path.startswith('.'):
                                        host_path = os.path.join(settings.HOST_BASE_DIR, host_path.lstrip('./'))
                                    volumes_config[host_path] = {'bind': parts[1], 'mode': parts[2] if len(parts) > 2 else 'rw'}
    
                            output_context = {}
                            cid = None
                            try:
                                cid = executor.run_worker(
                                    command=cmd_list,
                                    environment=task_def.target.get('environment'),
                                    volumes=volumes_config,
                                    input_context=input_ctx,
                                    name_suffix=f"adhoc-{cmd_id}",
                                    network_mode=task_def.target.get('network_mode')
                                )
                            
                                # 等待执行完成
                                wait_res = executor.wait_for_container(cid)
                                exit_code = wait_res.get('StatusCode', 1)
                                
                                # 获取日志
                                output_context = {}
                                logs = "" # [Fix] 确保 logs 变量始终被定义
                                try:
                                    container = self.docker_client.containers.get(cid)
                                    full_logs = container.logs().decode('utf-8')
                                    logs = full_logs[-2000:] 
    
                                    # 尝试从日志中提取结构化输出 (n8n 风格)
                                    # 寻找格式为: GSD_OUTPUT_JSON: {...}
                                    marker = "GSD_OUTPUT_JSON:"
                                    if marker in full_logs:
                                        try:
                                            start_idx = full_logs.find(marker) + len(marker)
                                            content = full_logs[start_idx:].strip()
                                            # 寻找第一个 { 和最后一个 }
                                            first_brace = content.find('{')
                                            last_brace = content.rfind('}')
                                            if first_brace != -1 and last_brace != -1:
                                                json_str = content[first_brace:last_brace+1]
                                                # 清理不可见字符 (如 \r, \n 或 Docker 混合流头部)
                                                import re
                                                json_str = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_str)
                                                output_context = json.loads(json_str)
                                                logger.info(f"✨ 捕获到结构化输出 (长度: {len(json_str)})")
                                        except Exception as e:
                                            logger.warning(f"解析结构化输出失败: {e}")
                                except Exception as e:
                                    logs = f"系统捕获日志异常: {e}"
                                    
                                if exit_code != 0:
                                    # Prepare error context for AI diagnosis
                                    output_context["error_logs"] = logs
                                    raise Exception(f"容器退出码 {exit_code}")
                                    
                                result = f"Success (Ad-hoc). Logs tail:\n{logs[-500:]}"
                            finally:
                                if cid:
                                    try:
                                        container = self.docker_client.containers.get(cid)
                                        container.remove(force=True)
                                        logger.info(f"🗑️ 已清理临时容器: {cid[:12]}")
                                    except:
                                        pass
                        
                        
                    elif task_def.type == "workflow_trigger" and self.flow_controller:
                        # 核心优化：直接调用 FlowController 触发工作流，绕过定时调度
                        workflow_id = task_def.target.get('workflow_id')
                        logger.info(f"⚡ [Direct] Triggering Workflow: {workflow_id} (Params: {params})")
                        
                        # 1. 准备上下文 (合并 yml 配置与 SQL 传入参数)
                        # [DENSE DEBUG] 详细追踪上下文构建
                        base_ctx = task_def.target.get('initial_context', {})
                        ctx = dict(base_ctx)
                        if params:
                            for pk, pv in params.items():
                                logger.info(f"DEBUG_FLOW: Applying override {pk} = {pv}")
                                ctx[pk] = pv
                        
                        ctx['trigger_time'] = datetime.now().isoformat()
                        
                        # Handle specific placeholders
                        if ctx.get('target_date') == '{{today_nodash}}':
                             ctx['target_date'] = datetime.now().strftime("%Y%m%d")
                        
                        logger.info(f"DEBUG_FLOW: Final Merged Context: {ctx}")

                        # 2. 从数据库加载定义
                        async with self.mysql_pool.acquire() as inner_conn:
                            async with inner_conn.cursor(aiomysql.DictCursor) as inner_cursor:
                                await inner_cursor.execute(
                                    "SELECT definition FROM alwaysup.workflow_definitions WHERE id = %s",
                                    (workflow_id,)
                                )
                                row = await inner_cursor.fetchone()
                                if row:
                                    from core.workflow_parser import WorkflowDefinition
                                    def_json = json.loads(row['definition']) if isinstance(row['definition'], str) else row['definition']
                                    wf_def = WorkflowDefinition.model_validate(def_json)
                                    
                                    # 3. 创建运行实例
                                    run_id = await self.flow_controller.create_run(workflow_id, wf_def, ctx)
                                    result = f"Directly triggered Workflow Run: {run_id}"
                                    output_context = {"run_id": run_id}
                                else:
                                    raise ValueError(f"Workflow ID '{workflow_id}' not found in DB")
                        
                    else:
                        # 默认回退到 Scheduler 触发 (不支持参数或非 Docker 任务)
                        self.scheduler.modify_job(task_id, next_run_time=datetime.now(), kwargs={'params': params})
                        result = f"Triggered via Scheduler (Dynamic Params: {list(params.keys()) if params else 'None'})"
                        output_context = {}
                            
                except Exception as e:
                    status = "FAILED"
                    result = str(e)
                    # Preserve existing output_context (like error_logs)
                    if not output_context:
                        output_context = {}
                    output_context["error"] = str(e)
                    logger.error(f"❌ 命令 #{cmd_id} 执行失败: {e}")
                
                # [Fix] 移除结果中的 4字节 UTF-8 字符 (如 emoji)，防止 utf8 字符集的 MySQL 报错
                try:
                    # 匹配任何非 BMP 字符 (U+10000 及以上)
                    import re
                    non_bmp = re.compile(r'[^\u0000-\uFFFF]')
                    result = non_bmp.sub('', result)
                except Exception as e:
                    logger.warning(f"清洗结果字符串失败: {e}")

                # 4. 更新结果
                await cursor.execute(
                    "UPDATE alwaysup.task_commands SET status=%s, result=%s, output_context=%s WHERE id=%s",
                    (status, result, json.dumps(output_context), cmd_id)
                )
                await conn.commit()

                # 5. [方案 A] 自动化联动：修复任务完成后自动触发门禁审计 (Re-Audit)
                if status == "DONE":
                    REAUDIT_MAP = {
                        "daily_stock_collection": "pre_market_gate",
                        # "repair_tick": "post_market_gate",  # DISABLED: 防止无限循环
                        "repair_kline": "post_market_gate"
                    }
                    if task_id in REAUDIT_MAP and self.scheduler:
                        gate_id = REAUDIT_MAP[task_id]
                        logger.info(f"🔄 任务 {task_id} 执行成功，自动刷新门禁状态: {gate_id}")
                        try:
                            # 立即触发门禁任务 (不带参数，运行标准审计)
                            self.scheduler.modify_job(gate_id, next_run_time=datetime.now())
                        except Exception as e:
                            logger.error(f"自动触发门禁 {gate_id} 失败: {e}")
