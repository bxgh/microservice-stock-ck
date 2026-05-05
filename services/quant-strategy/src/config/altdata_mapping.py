"""
另类数据标签 -> A 股同花顺概念映射表。

供 CandidatePoolService 的加分漏斗使用。
当 GitHub 某标签探测到 HOT/EXTREME 时，相关的概念成分股将在此映射指导下获得选股加分红利。
"""
from typing import List, Dict

# Mapping of alternative data tech label to actual China A-share concept identifiers/names.
ALTDATA_CONCEPT_MAPPING: Dict[str, List[str]] = {
    # 比如在开源搜集端定义的 label : 映射在 mootdx-source 查出来的同花顺具体概念名或主键
    "deepseek": ["人工智能", "AIGC概念", "算力租赁", "大模型"],
    "vllm": ["算力租赁", "CPO概念", "服务器"],
    "pytorch": ["人工智能", "软件开发"],
    "paddlepaddle": ["百度概念", "人工智能"],
    "huggingface": ["AIGC概念", "数据要素"],
    # 硬件算力标签 (Story 18.3)
    "nvidia": ["算力租赁", "CPO概念", "服务器", "液冷服务器"],
    "ascend": ["华为概念", "国产算力", "昇腾概念", "信创"],
    "metax": ["芯片概念", "国产算力", "智算中心"],
    "hygon": ["海光信息", "国产算力", "信创", "服务器"],
    "computecenter": ["智算中心", "算力租赁", "数据中心"]
}

def get_concepts_for_label(label: str) -> List[str]:
    """获取被引爆的技术标签所关联的国内映射概念名词"""
    return ALTDATA_CONCEPT_MAPPING.get(label.lower(), [])
