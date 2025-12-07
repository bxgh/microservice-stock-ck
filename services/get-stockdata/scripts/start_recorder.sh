#!/bin/bash
# 实时快照录制服务启动脚本

echo "🚀 Starting Snapshot Recorder Service..."

# 1. 初始化 Mootdx 配置
echo "📡  Initializing Mootdx..."
python -m mootdx bestip

# 2.  启动录制器
echo "🎯 Starting recorder..."
python -m src.core.recorder.snapshot_recorder

echo "✅ Service completed"
