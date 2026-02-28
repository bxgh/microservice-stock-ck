import logging
from collections import defaultdict

import numpy as np
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)

def filter_small_clusters(
    clusters: dict[str, int],
    min_size: int = 3
) -> dict[str, int]:
    """
    【规则1】剔除成员数过少的孤立簇。
    量化特征上的 2 只股票共振很有可能是随机巧合，
    至少 3 只股票的异动才能形成“资金团”的统计显著性。
    """
    # 统计各个 cluster 的频次
    cluster_counts: dict[int, int] = defaultdict(int)
    for cid in clusters.values():
        cluster_counts[cid] += 1

    filtered_clusters = {}
    removed_count = 0

    for stock, cid in clusters.items():
        if cluster_counts[cid] >= min_size:
            filtered_clusters[stock] = cid
        else:
            removed_count += 1

    logger.info(f"Filter [Small Clusters]: Removed {removed_count} stocks belonging to clusters < {min_size}.")
    return filtered_clusters


def filter_market_beta_clusters(
    clusters: dict[str, int],
    stock_returns: dict[str, np.ndarray],
    benchmark_return: np.ndarray,
    correlation_threshold: float = 0.9
) -> dict[str, int]:
    """
    【规则2】大盘 Beta 中和剔除。
    如果一个 Cluster 的平均收益率走势与基准指数（如沪深300）呈现极端高相关（>0.9），
    则说明该群组上涨只是随波逐流的“大盘共振 Beta 成分”，而非真正的“主动资金 Alpha 独立团伙”，必须被全量剔除。
    """
    # 先把同一个群组的股票归拢按 ID 存放
    cid_to_stocks = defaultdict(list)
    for stock, cid in clusters.items():
        cid_to_stocks[cid].append(stock)

    valid_clusters = {}
    removed_cids = set()

    for cid, stock_list in cid_to_stocks.items():
        # 获取群内所有有效序列
        valid_series = []
        for s in stock_list:
            if s in stock_returns and len(stock_returns[s]) == len(benchmark_return):
                valid_series.append(stock_returns[s])

        if not valid_series:
            # 缺乏收益率参考数据，默认放行
            continue

        # 计算 Cluster 的平均走势
        avg_series = np.mean(np.array(valid_series), axis=0)

        # 为了防止除以零或者标准差为0带来的警告
        if np.std(avg_series) < 1e-8 or np.std(benchmark_return) < 1e-8:
            corr = 0.0
        else:
            corr, _ = pearsonr(avg_series, benchmark_return)

        if abs(corr) > correlation_threshold:
            removed_cids.add(cid)
            logger.info(f"Filter [Market Beta]: Cluster {cid} extremely correlated ({corr:.3f}) with benchmark. Removed.")

    # 只保留存活的群组
    for stock, cid in clusters.items():
        if cid not in removed_cids:
            valid_clusters[stock] = cid

    return valid_clusters


def filter_industry_homogeneity(
    clusters: dict[str, int],
    stock_industry: dict[str, str],
    homogeneity_threshold: float = 0.8
) -> dict[str, int]:
    """
    【规则3】剔除极度同质化的行业板块轮动。
    如果一个群组内超过 80% 的个股属于同一个行业，
    那这就是宏观级别的“板块贝塔”，而非我们希望寻找的“隐秘游资跨界联动”。依规直接剔除。
    """
    cid_to_stocks = defaultdict(list)
    for stock, cid in clusters.items():
        cid_to_stocks[cid].append(stock)

    valid_clusters = {}
    removed_cids = set()

    for cid, stock_list in cid_to_stocks.items():
        total_valid = 0
        ind_counts: dict[str, int] = defaultdict(int)

        for s in stock_list:
            if s in stock_industry:
                ind_counts[stock_industry[s]] += 1
                total_valid += 1

        if total_valid == 0:
            continue

        # 找出占比最高的行业
        max_ratio = max(ind_counts.values()) / total_valid
        if max_ratio > homogeneity_threshold:
            removed_cids.add(cid)
            logger.info(f"Filter [Industry Homogeneity]: Cluster {cid} exceeds threshold with {max_ratio*100:.1f}% in same industry. Removed.")

    for stock, cid in clusters.items():
        if cid not in removed_cids:
            valid_clusters[stock] = cid

    return valid_clusters


def filter_low_turnover_clusters(
    clusters: dict[str, int],
    turnover_data: dict[str, float],
    min_avg_turnover: float = 0.02
) -> dict[str, int]:
    """
    【规则4】剔除死水微澜（低换手率）群落。
    日均换手率极低说明群体处于无主动资金交易的冻结状态或停牌近似状态。
    其引发的相似距极有可能是数学计算巧合，应该整体剔除。
    """
    cid_to_stocks = defaultdict(list)
    for stock, cid in clusters.items():
        cid_to_stocks[cid].append(stock)

    valid_clusters = {}
    removed_cids = set()

    for cid, stock_list in cid_to_stocks.items():
        valid_turnover = [turnover_data[s] for s in stock_list if s in turnover_data]
        if not valid_turnover:
            continue

        avg_turnover = np.mean(valid_turnover)
        if avg_turnover < min_avg_turnover:
            removed_cids.add(cid)
            logger.info(f"Filter [Low Turnover]: Cluster {cid} avg turnover {avg_turnover:.3f} is below min limit. Removed.")

    for stock, cid in clusters.items():
        if cid not in removed_cids:
            valid_clusters[stock] = cid

    return valid_clusters
