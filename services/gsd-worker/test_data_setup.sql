-- K线同步自适应调度器测试数据准备脚本
-- 在云端MySQL alwaysup库执行

-- 1. 清理旧的测试数据
DELETE FROM sync_progress 
WHERE task_name = 'full_market_sync' 
  AND DATE(updated_at) >= DATE_SUB(CURDATE(), INTERVAL 2 DAY);

-- 2. 插入"昨日"历史记录（用于历史预测）
INSERT INTO sync_progress (task_name, status, total_records, updated_at, error_message)
VALUES ('full_market_sync', 'completed', 5000, DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL 18 HOUR + INTERVAL 55 MINUTE, NULL);

-- 3. 插入"今日"完成记录（用于信号检测）
INSERT INTO sync_progress (task_name, status, total_records, updated_at, error_message)
VALUES ('full_market_sync', 'completed', 5100, NOW(), NULL);

-- 4. 验证插入结果
SELECT 
    task_name,
    status,
    total_records,
    updated_at,
    CASE 
        WHEN DATE(updated_at) = CURDATE() THEN '今日'
        WHEN DATE(updated_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) THEN '昨日'
        ELSE '其他'
    END AS date_label
FROM sync_progress 
WHERE task_name = 'full_market_sync'
ORDER BY updated_at DESC
LIMIT 5;
