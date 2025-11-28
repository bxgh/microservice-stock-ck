import pandas as pd
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

class ParquetWriter:
    """
    Parquet 存储引擎
    专为高频快照数据设计，支持按时间分片
    """
    
    def __init__(self, base_path: str = "/app/data/snapshots"):
        """
        初始化存储引擎
        
        Args:
            base_path: 数据存储根目录
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Parquet Writer initialized: {self.base_path}")
    
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
            print("⚠️ Empty DataFrame, skipping save")
            return ""
        
        # 使用当前时间作为默认时间戳
        if timestamp is None:
            timestamp = datetime.now()
        
        # 文件组织策略：/data/snapshots/20251128/snapshot_14.parquet
        date_str = timestamp.strftime('%Y%m%d')
        hour_str = timestamp.strftime('%H')
        
        # 创建日期目录
        date_dir = self.base_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径
        filename = f"snapshot_{hour_str}.parquet"
        file_path = date_dir / filename
        
        # 添加时间戳列（如果没有）
        if 'snapshot_time' not in df.columns:
            df = df.copy()
            df['snapshot_time'] = timestamp
        
        try:
            # 如果文件已存在，追加；否则新建
            if file_path.exists():
                # 读取现有数据
                existing_df = pd.read_parquet(file_path)
                # 合并数据
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                # 写回
                combined_df.to_parquet(file_path, compression='gzip', index=False)
                print(f"📝 Appended {len(df)} rows to {file_path.name}")
            else:
                # 新文件
                df.to_parquet(file_path, compression='gzip', index=False)
                print(f"✨ Created new file {file_path.name} with {len(df)} rows")
            
            return str(file_path)
            
        except Exception as e:
            print(f"❌ Failed to save snapshot: {e}")
            return ""
    
    def get_stats(self, date: Optional[str] = None) -> dict:
        """
        获取存储统计信息
        
        Args:
            date: 日期（YYYYMMDD），默认为今天
        
        Returns:
            dict: 统计信息
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        date_dir = self.base_path / date
        
        if not date_dir.exists():
            return {"date": date, "files": 0, "total_size": 0}
        
        files = list(date_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "date": date,
            "files": len(files),
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2)
        }

if __name__ == "__main__":
    # 测试代码
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
