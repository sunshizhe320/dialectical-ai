"""
AI 支架式教学模块
- 消息分类
- 支架问题生成
- 观点提取
"""

import streamlit as st
from typing import List, Dict


def classify_message_type(message: str, all_messages: List[Dict], user: str) -> str:
    """
    分类消息类型
    """
    message_lower = message.lower()
    
    # 检测综合标记
    synthesis_words = ['综合', 'combine', '结合', '折中', 'both', '都有道理']
    if any(w in message_lower for w in synthesis_words):
        return "Synthesis"
    
    # 检测回应标记
    response_words = ['但是', 'but', '然而', 'however', '不同意', 'disagree', '不对', '反对']
    if any(w in message_lower for w in response_words):
        return "Related"
    
    # 检测新证据标记
    evidence_words = ['数据', 'data', '研究', 'study', '例如', 'example', '证据', 'evidence']
    if any(w in message_lower for w in evidence_words):
        return "Additional"
    
    # 默认为初始观点
    return "Initial Position"


def extract_core_viewpoints(messages: List[Dict]) -> List[str]:
    """提取讨论的核心观点"""
    
    viewpoints = set()
    
    # 关键词映射
    keywords = {
        "算法": "算法影响",
        "推荐": "推荐系统",
        "个人": "个人选择",
        "教育": "教育作用",
        "平台": "平台责任",
        "用户": "用户自主性"
    }
    
    for msg in messages:
        content = msg.get('message', '').lower()
        for keyword, viewpoint in keywords.items():
            if keyword in content:
                viewpoints.add(viewpoint)
    
    return list(viewpoints)[:4] if viewpoints else ["观点A", "观点B", "观点C"]


def generate_scaffolding_questions(
    message: str, 
    user: str, 
    other_users: List[str],
    discussion_round: int
) -> Dict[str, str]:
    """
    生成 4 层支架问题
    """
    
    # 提取关键词
    keywords = extract_keywords(message)
    key_term = keywords[0] if keywords else "这个观点"
    other_user = other_users[0] if other_users else "其他参与者"
    
    questions = {
        "L1_Clarify": f"🔵 **澄清层**: 你能解释一下'{key_term}'的具体含义吗？",
        "L2_Compare": f"🟢 **比较层**: 这与{other_user}的观点有什么区别？",
        "L3_Synthesize": f"🟠 **综合层**: 你觉得两个观点中哪些可以结合起来？",
        "L4_Reflect": f"🔴 **反思层**: 如果反过来考虑，你的论点是否仍然有效？"
    }
    
    return questions


def extract_keywords(text: str) -> List[str]:
    """提取文本中的关键词"""
    
    keywords = [
        "算法", "推荐", "个人", "教育", "平台", 
        "用户", "数据", "创意", "效率", "协作"
    ]
    
    found = [kw for kw in keywords if kw in text.lower()]
    return found[:2]