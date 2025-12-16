# Story 6.1: Infrastructure & gRPC Interface Definition

## 目标
建立各种数据源微服务共享的基础设施，包括 gRPC 协议定义、代码生成流程以及项目目录结构的调整。

## 成功标准 (Acceptance Criteria)
1.  [ ] `data_source.proto` 文件已创建，包含完整的数据类型枚举和请求/响应结构。
2.  [ ] 能够通过脚本自动生成 Python gRPC 代码。
3.  [ ] 创建 `common/proto` 目录，生成的代码可被 `data-api` 和其他 `source` 服务引用。
4.  [ ] 项目根目录结构已调整，为后续微服务拆分做好准备。

## 任务拆解

### 1. 协议定义
- [ ] 创建 `proto/datasource/v1/data_source.proto`
    - 定义 `enum DataType` (QUOTES, TICK, HISTORY, etc.)
    - 定义 `message DataRequest` (type, codes, params)
    - 定义 `message DataResponse` (success, data_bytes, error)
    - 定义 `service DataSourceService`

### 2. 构建工具
- [ ] 编写 `scripts/codegen.sh` 脚本
    - 使用 `python -m grpc_tools.protoc` 命令
    - 自动将 protobuf 编译为 python 代码
    - 处理 import 路径问题

### 3. 全新项目结构搭建
- [ ] 创建 `proto` 目录 (根目录下)
    - 存放 `.proto` 定义文件
- [ ] 创建 `libs/common` 目录
    - 存放生成的 gRPC Python 代码
    - 存放共享工具类
- [ ] 确认新服务目录规划 (services/)
    - `services/mootdx-source/`
    - `services/akshare-source/`
    - `services/data-api/` (全新的 API 网关服务)
    - **注意**：现有 `services/get-stockdata` 保持原样，互不干扰，直到迁移完成。
