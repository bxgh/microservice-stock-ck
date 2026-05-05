import logging

import igraph as ig  # type: ignore
import leidenalg  # type: ignore
import networkx as nx  # type: ignore

logger = logging.getLogger(__name__)

def detect_communities_leiden(g_graph: nx.Graph, resolution: float = 1.0) -> dict[str, int]:
    """
    使用 Leiden 算法进行社区发现。
    Leiden 相比于经典 Louvain 解决了局部分辨率极限（Resolution Limit）导致的小社区桥接融合问题，
    能更清晰且稳定地分割出结构紧密的子图网络（资金团伙）。

    Args:
        g_graph: networkx 格式的无向加权图
        resolution: 控制社区划分的粒度。> 1.0 倾向于更小且多的社区，< 1.0 倾向于更大且少的社区。默认为 1.0。

    Returns:
        Dict[str, int]: {stock_code: cluster_id} 映射字典，表示每只活跃股票所属的群落ID。
    """
    if g_graph.number_of_nodes() == 0:
        logger.warning("NetworkX graph is empty. No communities to detect.")
        return {}

    logger.info("Converting NetworkX graph to iGraph for optimized Leiden execution...")
    # 保证节点能在字符串（股票代码）和整数（iGraph索引）之间无损双向映射
    nodes = list(g_graph.nodes())
    node_to_idx = {n: i for i, n in enumerate(nodes)}

    edges = []
    weights = []

    # 提取 nx 的边和权重，打平成 iGraph 需要的参数格式
    for u, v, data in g_graph.edges(data=True):
        edges.append((node_to_idx[u], node_to_idx[v]))
        weights.append(data.get('weight', 1.0))

    ig_graph = ig.Graph(n=len(nodes), edges=edges, directed=False)
    ig_graph.es['weight'] = weights

    logger.info(f"Running Leiden algorithms on {len(nodes)} nodes with resolution={resolution}...")

    # 采用由 weight 驱动的 ModularityVertexPartition 模块度优化
    # 这是发现网络深层结构的最常用目标函数配置
    partition = leidenalg.find_partition(
        ig_graph,
        leidenalg.ModularityVertexPartition,
        weights='weight',
        resolution_parameter=resolution
    )

    # 将包含整数索引的划分集合结果映射回调回股票代码
    clusters: dict[str, int] = {}
    for cluster_id, node_indices in enumerate(partition):
        for idx in node_indices:
            stock_code = nodes[idx]
            clusters[stock_code] = cluster_id

    logger.info(f"Leiden detection successfully finished. Established {len(partition)} isolated communities.")
    return clusters
