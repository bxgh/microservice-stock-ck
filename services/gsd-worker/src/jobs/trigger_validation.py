import asyncio
import logging
import sys
import argparse
from core.post_market_gate_service import PostMarketGateService
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/trigger_validation.log")
    ]
)

logger = logging.getLogger("TriggerValidationJob")

async def main():
    parser = argparse.ArgumentParser(description="Trigger Remote Validation")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)", required=False)
    # parser.add_argument("--target", type=str, help="Target (market or stock_code)", default="market") # 目前 PostMarketGateService 主要是 Market Level
    
    args = parser.parse_args()
    
    logger.info(f"🛡️ Starting Remote Validation Trigger... Args: {args}")
    
    service = PostMarketGateService()
    try:
        await service.initialize()
        
        # 1. 设置日期
        target_date = args.date
        if not target_date:
            target_date = service._get_target_trading_date()
        
        logger.info(f"🎯 Target Date: {target_date}")
        
        # 2. 执行校验
        # 目前 PostMarketGateService.run_gate_check() 内部会根据日期 (today/history) 自动选择逻辑
        # 但它目前依赖自己内部的 _get_target_trading_date()，我们需要稍微改造一下 service 使其支持传入 date
        # 或者我们临时修改 _get_target_trading_date 方法? 
        # 不，最好的方式是重构 run_gate_check 接受 date 参数。
        # 但为了不破坏现有逻辑，我们可以继承或直接调用内部方法，或者修改 run_gate_check 签名 (带默认值)
        
        # 让我们先看看 run_gate_check 的源码:
        # def run_gate_check(self) -> Dict[str, Any]:
        #     today = self._get_target_trading_date()
        
        # 我们需要修改 PostMarketGateService.run_gate_check 让其接受 date_str
        # 既然我们无法在不修改 service 的情况下传入 date，那我们先修改 service。
        # 假设我们已经修改了 service (下一步会修改)
        
        report = await service.run_gate_check(date_str=target_date)
        
        logger.info(f"✅ Validation Complete. Status: {report['status']}")
        
    except Exception as e:
        logger.error(f"❌ Validation Job Failed: {e}", exc_info=True)
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
