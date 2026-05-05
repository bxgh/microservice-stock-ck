# Story 1.3: 策略基类设计 (BaseStrategy)

## 目标
定义所有策略必须遵循的接口规范。

## 任务分解
1. 设计 `BaseStrategy` 抽象类，包含 `initialize`, `on_bar`, `on_tick`, `generate_signal` 等方法。
2. 定义标准化的 `Signal` 数据结构（标的、方向、强度、时间、逻辑）。
3. 实现策略注册机制（Registry Pattern），支持策略自动发现与管理。
4. 编写基类和注册机制的单元测试。
5. 补充开发文档，说明接口规范和扩展方式。