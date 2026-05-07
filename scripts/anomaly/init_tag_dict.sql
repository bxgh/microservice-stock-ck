-- ============================================
-- 任务 ID: [E1-S9-T1]
-- 描述: 初始化标签字典数据 (v1.1)
-- ============================================

INSERT INTO `dim_tag_dictionary` (`tag_code`, `tag_name_cn`, `tag_category`, `tag_subcategory`, `tag_description`, `display_order`) VALUES
-- 价格行为 (Price Action)
('zt', '涨停', 'price', 'state', '当日收盘封死涨停', 10),
('dt', '跌停', 'price', 'state', '当日收盘封死跌停', 20),
('first_board', '首板', 'price', 'board', '从非连板状态进入首个涨停', 30),
('lian_2', '二连板', 'price', 'board', '连续第二个涨停', 40),
('lian_3', '三连板', 'price', 'board', '连续第三个涨停', 50),
('lian_n', '高标连板', 'price', 'board', '四连板及以上', 60),
('breakout_60d', '60日新高', 'price', 'breakout', '收盘价创60个交易日新高', 70),
('breakout_250d', '年线突破', 'price', 'breakout', '放量突破250日均线', 80),

-- 资金流向 (Capital Flow)
('main_inflow_strong', '主力强流入', 'capital', 'inflow', '当日主力净流入超5000万且占比超10%', 110),
('lhb_inst_buy', '机构席位买入', 'capital', 'lhb', '龙虎榜显示机构净买入', 120),
('capital_rank_jump', '资金排名跃升', 'capital', 'rank', '资金流入排名较前5日平均跃升50%以上', 130),
('north_buy_strong', '北向强增仓', 'capital', 'north', '当日北向资金大幅增持(仅限24-08-19前或整体大盘)', 140),

-- 板块地位 (Sector Position)
('sector_leader', '板块龙头', 'sector', 'status', '当日涨幅居所属申万一级行业前3', 210),
('mainline_resonance', '主线共振', 'sector', 'resonance', '个股异动且所属行业整体走强', 220),

-- 形态特征 (Shape/Pattern)
('pre_zt_consolidation', '涨停前缩量平台', 'pattern', 'setup', '涨停前经历3-5日缩量横盘', 310),
('zt_one_word', '一字板', 'pattern', 'board', '开盘即涨停且未开板', 320),
('breakout_box_60d', '箱体突破', 'pattern', 'breakout', '突破过去60日的震荡箱体上沿', 330),
('ma_alignment_bull', '均线多头排列', 'pattern', 'ma', 'MA5 > MA10 > MA20 > MA60', 340),

-- 异常状态 (Anomaly)
('st', 'ST股', 'anomaly', 'risk', '风险警示股', 410),
('new_stock', '次新股', 'anomaly', 'time', '上市不满60个交易日', 420),
('micro_cap', '微盘股', 'anomaly', 'size', '市值处于全市场后5%且流动性低', 430),

-- 外部共振 (External)
('sox_up_overnight', '美股半导体走强', 'external', 'global', '费城半导体指数隔夜涨幅超2%', 510),
('us_tech_strong', '美股科技股强势', 'external', 'global', '纳斯达克100隔夜表现强劲', 520)
ON DUPLICATE KEY UPDATE 
    `tag_name_cn` = VALUES(`tag_name_cn`),
    `tag_category` = VALUES(`tag_category`),
    `tag_description` = VALUES(`tag_description`),
    `display_order` = VALUES(`display_order`);
