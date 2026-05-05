"""
Tushare 估值数据同步任务桥接 (Wrapper)
负责触发 tushare-debug-container 中的增量同步脚本
"""
import subprocess
import logging
import sys
from datetime import datetime
from core.job_context import job_ctx

logger = logging.getLogger(__name__)

async def main():
    logger.info("启动 Tushare 估值同步任务 (Daily Basic)")
    
    # 执行外部容器中的同步脚本
    # 假设宿主机或 gsd-worker 容器有权限执行 docker exec
    cmd = ["docker", "exec", "tushare-debug-container", "python3", "/app/scripts/sync_daily_basic.py"]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        output_lines = []
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(f"[Tushare] {line}")
                output_lines.append(line)
        
        process.wait()
        
        if process.returncode == 0:
            logger.info("✅ Tushare 估值同步任务成功完成")
            job_ctx.update_output({
                "status": "success",
                "last_sync": datetime.now().isoformat(),
                "logs": output_lines[-5:]
            })
            return 0
        else:
            logger.error(f"❌ Tushare 估值同步失败，退出码: {process.returncode}")
            job_ctx.set_output("status", "failed")
            job_ctx.set_output("error", f"Exit code {process.returncode}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ 任务运行异常: {e}")
        job_ctx.set_output("status", "failed")
        job_ctx.set_output("error", str(e))
        return 1
    finally:
        job_ctx.flush_output()

if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
