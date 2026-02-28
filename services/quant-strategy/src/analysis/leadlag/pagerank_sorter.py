import logging

import networkx as nx  # type: ignore

logger = logging.getLogger(__name__)

def build_lead_lag_graph(
    tlcc_results: dict[tuple[str, str], tuple[int, float]],
    min_corr: float = 0.5,
    min_lag: int = 2
) -> nx.DiGraph:
    """
    根据 TLCC 生成的时滞计算结果，将无向的“资金团伙”重构为“带方向的跟随关系网”。
    边的指向逻辑：Leader -> Follower。
    边的粗细表示影响力度的大小 (`corr`)。

    Args:
        tlcc_results: 组合股票对与其跑出的最大拉平特征的字典
            格式: {(stock_a, stock_b): (best_lag, max_corr)}
        min_corr: 时差拉平后的最小业务关联。小于该值认为时差属于巧合而非因果。
        min_lag: 最小时间差距。如果相差过小 (<2分钟) 认为是绝对同步异动，缺乏明确的上下级因果发令。

    Returns:
        DiGraph: NetworkX 发令传压有向图
    """
    g_graph = nx.DiGraph()

    for (stock_a, stock_b), (lag, corr) in tlcc_results.items():
        if corr > min_corr and abs(lag) >= min_lag:
            if lag > 0:
                # lag > 0，说明 A 位于时间前置，A 作为 Leader
                g_graph.add_edge(stock_a, stock_b, weight=corr)
            else:
                # lag < 0，说明 B 前置，B 作为 Leader
                g_graph.add_edge(stock_b, stock_a, weight=corr)

    return g_graph


def identify_leader(g_graph: nx.DiGraph) -> list[tuple[str, float]]:
    """
    通过页面排名算法 (PageRank) 在有向影响力关系图中锁定核心发号施令节点。

    如果在网络图中所有节点都高度听从于某一个源发节点，
    说明它具有最高的领袖号召力。
    由于标准的 PageRank 是投票机制（入度越高得分越高），但在我们的初始图中，
    边是 Leader -> Follower，这会导致处于图边缘最末端的“终极小弟”积攒最高分数。
    因此，计算 PageRank 时我们需要对图的反转 (reverse) 进行计算，使得投票从 Follower 流回 Leader。
    
    当图结构的节点极度稀疏不稳定时（<5 个节点），将智能隐退为加权出度估算。

    Returns:
        List[Tuple[stock_code, score]]: 按领导力排行降序的列表
    """
    if g_graph.number_of_nodes() == 0:
        return []

    if g_graph.number_of_nodes() < 5:
        logger.info(f"Leader identifying degradation: small cluster of {g_graph.number_of_nodes()} stocks. Using Out-Degree fallback.")
        # Node 出度大，代表主动发起的影响多
        weighted_outdegree = {
            node: sum(data.get('weight', 1.0) for _, _, data in g_graph.out_edges(node, data=True))
            for node in g_graph.nodes()
        }
        # 如果出度全部为0，证明大家都只是被动响应没有领导关系，退回平均分数
        if max(weighted_outdegree.values(), default=0.0) == 0.0:
            return [(n, 1.0 / g_graph.number_of_nodes()) for n in g_graph.nodes()]

        sorted_ranks = sorted(weighted_outdegree.items(), key=lambda x: x[1], reverse=True)
        return sorted_ranks

    # 正常 PageRank
    # 我们需要反转图，让跟随者把 "选票" 投给领导者，这样真正的领导者才能获得高分
    reversed_graph = g_graph.reverse()
    pagerank = nx.pagerank(reversed_graph, alpha=0.85, weight='weight')
    return sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
