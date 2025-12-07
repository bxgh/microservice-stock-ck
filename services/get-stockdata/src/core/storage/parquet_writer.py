import pandas as pd
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ParquetWriter:
    """
    Parquet 存储引擎
    专为高频快照数据设计，支持按时间分片、Snappy 压缩和自动清理
    """
    
    def __init__(self, base_path: str = "/app/data/snapshots", retention_days: int = 180):
        """
        初始化存储引擎
        
        Args:
            base_path: 数据存储根目录
            retention_days: 数据保留天数（默认180天）
        """
        self.base_path = Path(base_path)
        self.retention_days = retention_days
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Parquet Writer initialized: {self.base_path}, Retention: {retention_days} days")
    
    def save_snapshot(self, df: pd.DataFrame, timestamp: Optional[datetime] = None) -> str:
        """
        保存快照数据
        
        Args:
            df: 快照数据 DataFrame
            timestamp: 时间戳（默认使用当前时间）
        
        Returns:
            str: 保存的文件路径
        """
        if df is None or df.empty:
            return ""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # 1. 构造目录结构: YYYY-MM-DD/HH/
        # 相比旧版 (YYYYMMDD)，使用 ISO 格式更标准
        date_str = timestamp.strftime('%Y-%m-%d')
        hour_str = timestamp.strftime('%H')
        time_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        save_dir = self.base_path / date_str / hour_str
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. 构造文件名: snapshot_YYYYMMDD_HHMMSS.parquet
        # 每个快照一个独立文件，避免追加模式的性能损耗
        filename = f"snapshot_{time_str}.parquet"
        file_path = save_dir / filename
        
        try:
            # 3. 写入文件 (使用 snappy 压缩)
            # 需要 pyarrow 库支持
            df.to_parquet(
                file_path,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            # logger.debug(f"💾 Saved parquet: {filename} ({len(df)} rows)")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to save parquet snapshot: {e}")
            return ""
            
    def cleanup_old_files(self):
        """清理过期文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            logger.info(f"🧹 Cleaning up files older than {cutoff_date.date()}...")
            
            # 遍历一级目录 (YYYY-MM-DD)
            for date_dir in self.base_path.iterdir():
                if not date_dir.is_dir():
                    continue
                    
                # 解析目录日期
                try:
                    # 尝试解析 YYYY-MM-DD
                    dir_date = datetime.strptime(date_dir.name, '%Y-%m-%d')
                    if dir_date < cutoff_date:
                        shutil.rmtree(date_dir)
                        logger.info(f"🗑️ Deleted old directory: {date_dir}")
                except ValueError:
                    # 尝试解析旧格式 YYYYMMDD (为了兼容清理旧数据)
                    try:
                        dir_date = datetime.strptime(date_dir.name, '%Y%m%d')
                        if dir_date < cutoff_date:
                            shutil.rmtree(date_dir)
                            logger.info(f"🗑️ Deleted old directory (legacy format): {date_dir}")
                    except ValueError:
                        continue
                    
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def get_stats(self, date: Optional[str] = None) -> dict:
        """
        获取存储统计信息
        
        Args:
            date: 日期（支持 YYYYMMDD 或 YYYY-MM-DD），默认为今天
        
        Returns:
            dict: 统计信息
        """
        if date is None:
            date_obj = datetime.now()
        else:
            try:
                if '-' in date:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                else:
                    date_obj = datetime.strptime(date, '%Y%m%d')
            except:
                return {}

        # 优先检查新格式目录
        date_str_new = date_obj.strftime('%Y-%m-%d')
        date_dir = self.base_path / date_str_new
        
        # 如果不存在，检查旧格式目录
        if not date_dir.exists():
            date_str_old = date_obj.strftime('%Y%m%d')
            date_dir = self.base_path / date_str_old
            if not date_dir.exists():
                return {"date": date_str_new, "files": 0, "total_size": 0}
        
        # 递归统计所有文件 (包括子目录)
        files = list(date_dir.rglob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "date": date_dir.name,
            "files": len(files),
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2)
        }

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    writer = ParquetWriter("/tmp/test_snapshots")
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'code': ['600000', '600001', '600002'],
        'price': [11.48, 12.50, 8.88],
        'bid1': [11.47, 12.49, 8.87],
        'ask1': [11.48, 12.50, 8.88]
    })
    
    # 保存
    path = writer.save_snapshot(test_data)
    print(f"Saved to: {path}")
    
    # 获取统计
    stats = writer.get_stats()
    print(f"Stats: {stats}")
