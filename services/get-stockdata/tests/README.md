# Tests Directory

## 目录结构说明

本目录包含 get-stockdata 微服务的测试文件和调试工具。

## 文件说明

### 🛠️ 调试工具
- **fenbi.py** - fenbi分笔数据获取调试工具
  - 独立的命令行调试脚本
  - 用于开发阶段测试分笔数据获取功能
  - 支持多种输出格式和调试模式
  - 使用方法: `python fenbi.py --symbol 000001 --date 20251120 --debug`

### 🧪 单元测试
- **test_data_deduplicator.py** - 数据去重器单元测试
- **test_statistics_generator.py** - 统计生成器单元测试
- **test_time_formatter.py** - 时间格式化器单元测试

## 使用方法

### 运行fenbi调试工具
```bash
cd tests/
python fenbi.py --symbol 000001 --date 20251120 --format both --debug
```

### 运行单元测试
```bash
cd tests/
python -m pytest test_*.py -v
```

## 注意事项

- 本目录中的文件仅用于开发和测试目的
- 生产环境应使用 src/services/ 中的正式实现
- fenbi.py 作为调试工具，功能与生产服务可能存在差异
- 测试文件可以随时删除或修改，不影响核心功能

## 架构说明

- **生产服务**: 使用 `guaranteed_success_strategy.py` 作为API引擎
- **调试工具**: 使用 `fenbi.py` 进行独立测试和调试
- **职责分离**: 测试代码与生产代码完全分离