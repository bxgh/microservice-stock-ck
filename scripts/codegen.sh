#!/bin/bash
set -e

# 确保在项目根目录运行
PROJECT_ROOT=$(pwd)
PROTO_DIR="$PROJECT_ROOT/proto"
OUTPUT_DIR="$PROJECT_ROOT/libs/common"

echo "Using Project Root: $PROJECT_ROOT"

# 创建并激活虚拟环境以隔离依赖
VENV_DIR="$PROJECT_ROOT/scripts/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# 使用虚拟环境的 pip 和 python
PIP_CMD="$VENV_DIR/bin/pip"
PYTHON_CMD="$VENV_DIR/bin/python"

# 安装依赖
echo "Installing/checking grpcio-tools in venv..."
"$PIP_CMD" install grpcio-tools --quiet

# 创建输出目录结构
mkdir -p "$OUTPUT_DIR/datasource/v1"
touch "$OUTPUT_DIR/__init__.py"
touch "$OUTPUT_DIR/datasource/__init__.py"
touch "$OUTPUT_DIR/datasource/v1/__init__.py"

echo "Generating Python code from proto..."

# 生成代码
# -I 指定 import 搜索路径
# --python_out 生成 message 类
# --grpc_python_out 生成 server/stub 类
# --pyi_out 生成类型提示
"$PYTHON_CMD" -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUTPUT_DIR" \
    --grpc_python_out="$OUTPUT_DIR" \
    --pyi_out="$OUTPUT_DIR" \
    "$PROTO_DIR/datasource/v1/data_source.proto"

echo "Fixing imports for Python 3..."
# Python 3生成代码中 import 路径通常是绝对的，或者需要 hack
# 这里的 output 结构是 libs/common/datasource/v1/data_source_pb2.py
# 默认生成的 import 是 "import datasource.v1.data_source_pb2"
# 只要我们将 libs/common 加入 PYTHONPATH，这个 import 就是合法的

echo "Done. Code generated in $OUTPUT_DIR"
