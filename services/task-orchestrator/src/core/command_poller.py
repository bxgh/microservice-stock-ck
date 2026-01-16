import asyncio
import logging
import json
import os
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
    
    def __init__(self, mysql_pool, scheduler, docker_client=None, task_config=None, poll_interval: int = 15, shard_id: Optional[int] = None):
        self.mysql_pool = mysql_pool
        self.scheduler = scheduler
        self.docker_client = docker_client
        self.task_config = task_config
        self.poll_interval = poll_interval
        self.shard_id = shard_id
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
        
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 1. 获取针对当前分片的 PENDING 命令 (FOR UPDATE 锁行)
                if self.shard_id is None:
                    # 主控节点: 处理全局任务 (无 shard_id) 或 Shard 0 任务
                    sql = """
                        SELECT id, task_id, params 
                        FROM alwaysup.task_commands 
                        WHERE status = 'PENDING' 
                          AND (JSON_EXTRACT(params, '$.shard_id') IS NULL 
                               OR JSON_EXTRACT(params, '$.shard_id') = 0)
                        ORDER BY created_at ASC
                        LIMIT 1 FOR UPDATE
                    """
                    await cursor.execute(sql)
                else:
                    # 远程分片节点: 仅处理匹配自己 id 的任务
                    sql = """
                        SELECT id, task_id, params 
                        FROM alwaysup.task_commands 
                        WHERE status = 'PENDING' 
                          AND JSON_EXTRACT(params, '$.shard_id') = %s
                        ORDER BY created_at ASC
                        LIMIT 1 FOR UPDATE
                    """
                    await cursor.execute(sql, (self.shard_id,))
                
                cmd = await cursor.fetchone()
                
                if not cmd:
                    return
                
                cmd_id = cmd['id']
                task_id = cmd['task_id']
                params_json = cmd['params']
                
                params = {}
                if params_json:
                    try:
                        if isinstance(params_json, str):
                            params = json.loads(params_json)
                        else:
                            params = params_json
                    except Exception as e:
                        logger.warning(f"解析参数失败 #{cmd_id}: {e}")
                
                logger.info(f"⚡ 收到命令 #{cmd_id}: {task_id} params={params}")

                # 2. 更新状态为 RUNNING
                await cursor.execute(
                    "UPDATE alwaysup.task_commands SET status='RUNNING', executed_at=NOW() WHERE id=%s",
                    (cmd_id,)
                )
                await conn.commit()
                
                # 3. 执行任务
                status = "DONE"
                result = "SUCCESS"
                
                # 3. 执行任务
                status = "DONE"
                result = "SUCCESS"
                
                try:
                    # 查找任务定义
                    task_def = next((t for t in self.task_config.tasks if t.id == task_id), None)
                    if not task_def:
                        all_ids = [t.id for t in self.task_config.tasks]
                        logger.error(f"❌ 任务 {task_id} 未找到. 当前可用任务: {all_ids}")
                        raise ValueError(f"任务 {task_id} 未在本地注册. 可用任务: {all_ids}")

                    # 如果是 Docker 任务且有参数，使用 DockerExecutor 动态执行
                    if params and self.docker_client and task_def.type == "docker":
                        from executor.docker_executor import DockerExecutor
                        executor = DockerExecutor(self.docker_client)
                        
                        # 构建命令
                        original_cmd = task_def.target.get('command', [])
                        # 确保是 list
                        if isinstance(original_cmd, str):
                            cmd_list = original_cmd.split()
                        else:
                            cmd_list = list(original_cmd)
                            
                        # 追加参数: --key value
                        for k, v in params.items():
                            cmd_list.append(f"--{k}")
                            if v is not None and str(v) != "":
                                cmd_list.append(str(v))
                        
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
                                        host_path = os.path.join(settings.BASE_DIR, host_path.lstrip('./'))
                                    volumes_config[host_path] = {'bind': parts[1], 'mode': parts[2] if len(parts) > 2 else 'rw'}

                        task_vols = task_def.target.get('volumes', [])
                        for v in task_vols:
                            parts = v.split(':')
                            if len(parts) >= 2:
                                host_path = parts[0]
                                if host_path.startswith('.'):
                                    host_path = os.path.join(settings.BASE_DIR, host_path.lstrip('./'))
                                volumes_config[host_path] = {'bind': parts[1], 'mode': parts[2] if len(parts) > 2 else 'rw'}

                        cid = executor.run_worker(
                            command=cmd_list,
                            environment=task_def.target.get('environment'),
                            volumes=volumes_config,
                            name_suffix=f"adhoc-{cmd_id}"
                        )
                        
                        # 等待执行完成 (会阻塞轮询线程，但 Poller 本身是独立的 Task)
                        wait_res = executor.wait_for_container(cid)
                        exit_code = wait_res.get('StatusCode', 1)
                        
                        # 获取日志
                        try:
                            container = self.docker_client.containers.get(cid)
                            logs = container.logs().decode('utf-8')[-2000:] # 取最后2000字符
                            container.remove() # 清理容器
                        except Exception as e:
                            logs = f"无法获取日志: {e}"
                            
                        if exit_code != 0:
                            raise Exception(f"容器退出码 {exit_code}.\nLogs:\n{logs}")
                            
                        result = f"Success (Ad-hoc). Logs tail:\n{logs[-500:]}"
                        
                    else:
                        # 默认回退到 Scheduler 触发 (不支持参数或非 Docker 任务)
                        if params:
                            logger.warning(f"任务 {task_id} 不支持动态参数 (Type={task_def.type}), 参数将被忽略")
                            
                        self.scheduler.modify_job(task_id, next_run_time=datetime.now())
                        result = "Triggered via Scheduler (Params ignored)"
                        
                except Exception as e:
                    status = "FAILED"
                    result = str(e)
                    logger.error(f"❌ 命令 #{cmd_id} 执行失败: {e}")
                
                # [Fix] 移除结果中的 4字节 UTF-8 字符 (如 emoji)，防止 utf8 字符集的 MySQL 报错
                import re
                try:
                    # 匹配任何非 BMP 字符 (U+10000 及以上)
                    non_bmp = re.compile(r'[^\u0000-\uFFFF]')
                    result = non_bmp.sub('', result)
                except Exception as e:
                    logger.warning(f"清洗结果字符串失败: {e}")

                # 4. 更新结果
                await cursor.execute(
                    "UPDATE alwaysup.task_commands SET status=%s, result=%s WHERE id=%s",
                    (status, result, cmd_id)
                )
                await conn.commit()

                # 5. [方案 A] 自动化联动：修复任务完成后自动触发门禁审计 (Re-Audit)
                if status == "DONE":
                    REAUDIT_MAP = {
                        "daily_stock_collection": "pre_market_gate",
                        "repair_tick": "post_market_gate",
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
