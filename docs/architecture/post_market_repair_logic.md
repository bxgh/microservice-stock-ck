# 盘后数据修复逻辑流程 (Post-Market Repair Logic)

该流程图详细描述了系统如何根据数据缺失规模（Zone 1/2/3）智能选择修复策略。

```mermaid
flowchart TD
    Start((开始)) --> Audit[深度数据审计: <br/>完整性与连续性校验]
    
    Audit --> Calc[统计缺失与异常指标]
    Calc --> CheckCount{缺失数量范围?}
    
    %% Zone 1: Green
    CheckCount -- "缺失 < 50只 (Zone 1)" --> Zone1[🟢 绿色区域: 忽略]
    Zone1 --> Log1[记录日志: 正常冗余/无需立即修复]
    Log1 --> End((结束))
    
    %% Zone 2: Yellow
    CheckCount -- "50 <= 缺失 <= 500只 (Zone 2)" --> Zone2[🟡 黄色区域: AI 智能审计]
    Zone2 --> AI_Audit[调用 AI Gatekeeper 逐个分析]
    
    subgraph AI_Process [AI 判决流程]
        AI_Audit --> AI_Check{AI 判断结论?}
        AI_Check -- "停牌/涨跌停/非交易" --> MarkValid[标记为正常 (Ignore)]
        AI_Check -- "采集失败/无数据" --> MarkBad[加入 Confirmed List]
    end
    
    MarkValid --> CheckList{列表处理完?}
    MarkBad --> CheckList
    
    CheckList -- "否" --> AI_Audit
    CheckList -- "是" --> FinalList{Confirmed List 为空?}
    
    FinalList -- "是" --> Log2[记录日志: AI 判定均无需修复] --> End
    FinalList -- "否" --> DistributedRepair[🔵 执行分布式定向修复]
    DistributedRepair --> Supp[执行个股深度补充] --> End
    
    %% Zone 3: Red
    CheckCount -- "缺失 > 500只 (Zone 3)" --> Zone3[🔴 红色区域: 灾难恢复]
    Zone3 --> FailoverLog[触发 Plan B: 中央代偿机制]
    FailoverLog --> ForceMaster[Master 节点强制接管]
    ForceMaster --> LocalMode[配置: 强制本地模式 & 禁用分发]
    LocalMode --> BatchRepair[🟠 执行全量暴力补采]
    BatchRepair --> End

    style Zone1 fill:#e6fffa,stroke:#38b2ac
    style Zone2 fill:#faf089,stroke:#d69e2e
    style Zone3 fill:#feb2b2,stroke:#e53e3e
    style DistributedRepair fill:#bee3f8,stroke:#3182ce
    style BatchRepair fill:#fc8181,stroke:#c53030
```

## 逻辑说明

1.  **Zone 1 (Green)**: 少量缺失被视为系统的正常噪音（如少量停牌），为了避免频繁启动修复任务消耗资源，选择**忽略**。
2.  **Zone 2 (Yellow)**: 中等规模缺失，可能是部分数据源不稳定或特定板块异常。此时**启用 AI** 进行精细化筛选，剔除不需要修复的股票，只针对真正的故障进行**分布式修复**。
3.  **Zone 3 (Red)**: 大规模缺失（雪崩），通常意味着严重的集群故障（如分片节点宕机）。此时 AI 逐个审核效率太低，系统直接进入**Failover 模式**，由 Master 节点采用**本地模式**强行补采所有缺失数据，优先保全数据完整性。
