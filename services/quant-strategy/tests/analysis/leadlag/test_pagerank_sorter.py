from analysis.leadlag.pagerank_sorter import build_lead_lag_graph, identify_leader


def test_pagerank_leader_extraction():
    # 模拟 5 只股票组成的标准图 A 是绝对老大发令人
    # A 领先 B (corr=0.9, lag=3)
    # A 领先 C (corr=0.8, lag=2)
    # A 领先 D (corr=0.85, lag=4)
    # B 领先 E (corr=0.6, lag=2)
    tlcc_results = {
        ("A", "B"): (3, 0.9),
        ("A", "C"): (2, 0.8),
        ("A", "D"): (4, 0.85),
        ("B", "E"): (2, 0.6)
    }

    g_graph = build_lead_lag_graph(tlcc_results, min_corr=0.5, min_lag=2)

    # 应包含 5 个节点
    assert g_graph.number_of_nodes() == 5

    # A 有 3 条出边
    assert g_graph.out_degree("A") == 3

    # 执行寻找老大
    leaders = identify_leader(g_graph)

    # 第一个必须是 A，且打分应该最高
    top_leader, top_score = leaders[0]
    assert top_leader == "A"
    assert top_score > leaders[1][1]

def test_fallback_outdegree_on_small_clusters():
    # 测试 <5 支个股时的小微集群触发降级 (由于小集群转移概率矩阵易引发不收敛错误)
    # 这时只要是入度最高即老大
    tlcc_results = {
        ("X", "Y"): (3, 0.9),
        ("X", "Z"): (2, 0.8)
    }
    g_graph = build_lead_lag_graph(tlcc_results, min_corr=0.5, min_lag=2)

    # 仅 3 个节点
    assert g_graph.number_of_nodes() == 3

    # X 向 Y 和 Z 发出信号，应该作为老一
    leaders = identify_leader(g_graph)
    assert leaders[0][0] == "X"
