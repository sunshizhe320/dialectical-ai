"""
讨论质量指标计算
"""

from typing import List, Dict


def calculate_participation_balance(messages: List[Dict], participants: List[str]) -> float:
    """
    计算参与均衡度 (0-1)
    所有参与者发言数量是否相近
    """
    
    if not participants:
        return 0.0
    
    msg_counts = {p: 0 for p in participants}
    for msg in messages:
        user = msg.get('user')
        if user in msg_counts:
            msg_counts[user] += 1
    
    counts = list(msg_counts.values())
    if not counts or sum(counts) == 0:
        return 0.0
    
    avg = sum(counts) / len(counts)
    max_count = max(counts)
    
    if max_count == 0:
        return 0.0
    
    # 计算均匀度：越接近平均值越高
    balance = 1 - (max_count - avg) / max_count
    return max(0, min(1, balance))


def calculate_argument_completeness(messages: List[Dict]) -> float:
    """
    计算论据完整度 (0-1)
    是否有具体例子、数据、证据
    """
    
    evidence_words = ['数据', 'data', '研究', 'study', '例如', 'example', '证据', 'evidence', '因为', 'because']
    
    complete_msgs = 0
    for msg in messages:
        content = msg.get('message', '').lower()
        if any(word in content for word in evidence_words):
            complete_msgs += 1
    
    if not messages:
        return 0.0
    
    return complete_msgs / len(messages)


def calculate_interaction_depth(messages: List[Dict], participants: List[str]) -> float:
    """
    计算交互深度 (0-1)
    是否在互相回应而非各说各话
    """
    
    if len(participants) < 2:
        return 0.0
    
    response_words = ['但是', 'but', '然而', 'however', '同意', 'agree', '赞同']
    
    interactive_msgs = 0
    for msg in messages:
        content = msg.get('message', '').lower()
        if any(word in content for word in response_words):
            interactive_msgs += 1
    
    if not messages:
        return 0.0
    
    return interactive_msgs / len(messages)


def calculate_convergence_progress(messages: List[Dict], consensus_matrix: Dict) -> float:
    """
    计算收敛进度 (0-1)
    共识矩阵中已收敛的议题比例
    """
    
    if not consensus_matrix:
        return 0.0
    
    converged = 0
    total = 0
    
    for viewpoint, stances in consensus_matrix.items():
        if isinstance(stances, dict):
            total += 1
            # 检查是否所有参与者都同意
            stance_values = list(stances.values())
            if len(set(stance_values)) == 1:  # 所有值相同
                converged += 1
    
    if total == 0:
        return 0.0
    
    return converged / total


def get_quality_suggestions(metrics: Dict[str, float]) -> List[str]:
    """根据指标生成改进建议"""
    
    suggestions = []
    
    if metrics.get('participation_balance', 0) < 0.6:
        suggestions.append("💡 某些参与者表达不足，请鼓励所有人都发言")
    
    if metrics.get('argument_completeness', 0) < 0.5:
        suggestions.append("💡 需要更多具体例子和数据支持论点")
    
    if metrics.get('interaction_depth', 0) < 0.5:
        suggestions.append("💡 请尝试互相回应，而不是各说各话")
    
    if metrics.get('convergence_progress', 0) < 0.3:
        suggestions.append("💡 还有多个议题存在分歧，需要进入 Round 2 深入讨论")
    
    return suggestions