-- ============================================
-- Story 9.2: Financial and Valuation Persistence
-- Purpose: Create tables for financial and valuation data
-- ============================================

USE stock_data;

-- ============================================
-- 表: 财务指标数据 (financial_indicators)
-- ============================================
CREATE TABLE IF NOT EXISTS financial_indicators (
    stock_code String COMMENT '股票代码',
    report_date Date COMMENT '报表日期',
    report_type String COMMENT '报表类型 (Q1, Q2, Q3, Annual)',
    
    -- 收益表
    revenue Decimal(18, 4) COMMENT '营业收入 (亿元)',
    operating_cost Decimal(18, 4) COMMENT '营业成本 (亿元)',
    operating_profit Decimal(18, 4) COMMENT '营业利润 (亿元)',
    net_profit Decimal(18, 4) COMMENT '净利润 (亿元)',
    
    -- 资产负债表
    total_assets Decimal(18, 4) COMMENT '总资产 (亿元)',
    net_assets Decimal(18, 4) COMMENT '净资产 (亿元)',
    goodwill Decimal(18, 4) COMMENT '商誉 (亿元)',
    monetary_funds Decimal(18, 4) COMMENT '货币资金 (亿元)',
    interest_bearing_debt Decimal(18, 4) COMMENT '有息负债 (亿元)',
    accounts_receivable Decimal(18, 4) COMMENT '应收账款 (亿元)',
    inventory Decimal(18, 4) COMMENT '存货 (亿元)',
    accounts_payable Decimal(18, 4) COMMENT '应付账款 (亿元)',
    
    -- 现金流量表
    operating_cash_flow Decimal(18, 4) COMMENT '经营性现金流净额 (亿元)',
    
    -- 额外指标
    major_shareholder_pledge_ratio Decimal(8, 4) COMMENT '大股东质押率',
    
    data_source String DEFAULT 'akshare' COMMENT '数据来源',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
    
) ENGINE = ReplacingMergeTree()
PARTITION BY toYear(report_date)
ORDER BY (stock_code, report_date)
COMMENT '股票财务指标历史数据表';

-- ============================================
-- 表: 估值数据 (valuation_data)
-- ============================================
CREATE TABLE IF NOT EXISTS valuation_data (
    stock_code String COMMENT '股票代码',
    trade_date Date COMMENT '交易日期',
    
    total_market_cap Decimal(18, 4) COMMENT '总市值 (亿元)',
    circulating_market_cap Decimal(18, 4) COMMENT '流通市值 (亿元)',
    
    pe_ttm Decimal(10, 4) COMMENT '市盈率 (TTM)',
    pe_static Decimal(10, 4) COMMENT '市盈率 (静态)',
    pb_ratio Decimal(10, 4) COMMENT '市净率 (PB)',
    ps_ratio Decimal(10, 4) COMMENT '市销率 (PS)',
    pcf_ratio Decimal(10, 4) COMMENT '市现率 (PCF)',
    dividend_yield_ttm Decimal(10, 4) COMMENT '股息率 (TTM)',
    
    data_source String DEFAULT 'akshare' COMMENT '数据来源',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
    
) ENGINE = ReplacingMergeTree()
PARTITION BY toYear(trade_date)
ORDER BY (stock_code, trade_date)
COMMENT '股票估值指标历史数据表';

-- ============================================
-- 表: 行业信息表 (industry_info) - 增量更新
-- ============================================
CREATE TABLE IF NOT EXISTS industry_info (
    stock_code String COMMENT '股票代码',
    industry String COMMENT '所属行业',
    sector String COMMENT '所属板块',
    list_date Date COMMENT '上市日期',
    total_shares Int64 COMMENT '总股本',
    
    data_source String DEFAULT 'akshare' COMMENT '数据来源',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY stock_code
COMMENT '股票行业及基本信息表';
