"""
互动循环追踪
"""

from typing import List, Dict


def identify_discussion_round(messages: List[Dict], participants: List[str]) -> int:
    """
    识别讨论轮次
    Round 1: 每个参与者都发表了初始观点
    Round 2: 有人进行了回应
    Round 3: 有综合或共识表述
    """
    
    if not messages:
        return 1
    
    # 检查参与者覆盖
    speakers = set(msg.get('user') for msg in messages)
    all_participated = all(p in speakers for p in participants)
    
    if not all_participated:
        return 1
    
    # 检查回应
    has_response = any("Related" in str(msg) for msg in messages)
    
    if not has_response:
        return 1
    
    # 检查综合
    has_synthesis = any("Synthesis" in str(msg) for msg in messages)
    
    return 3 if has_synthesis else 2


def suggest_next_round(
    current_round: int, 
    messages: List[Dict], 
    convergence_progress: float
) -> str:
    """推荐下一轮时机"""
    
    if current_round == 1:
        return "所有参与者都已表达初始观点，请进入 Round 2：互相评价"
    elif current_round == 2:
        if convergence_progress < 0.3:
            return "有多个议题还有分歧，建议继续 Round 2 讨论"
        else:
            return "大部分议题已收敛，可以进入 Round 3：综合共识"
    else:
        return "讨论已进入综合阶段，继续深化共识"


def get_round_status(current_round: int, messages: List[Dict], participants: List[str]) -> Dict:
    """获取每一轮的状态"""
    
    status = {
        1: {"name": "初始表达", "icon": "📍", "progress": 0},
        2: {"name": "相互评价", "icon": "💬", "progress": 0},
        3: {"name": "综合共识", "icon": "🤝", "progress": 0}
    }
    
    if current_round >= 1:
        speakers = set(msg.get('user') for msg in messages)
        progress = len(speakers) / max(len(participants), 1)
        status[1]["progress"] = min(1, progress)
    
    if current_round >= 2:
        response_count = sum(1 for msg in messages if "Related" in str(msg))
        progress = min(1, response_count / max(len(participants), 1))
        status[2]["progress"] = progress
    
    if current_round >= 3:
        synthesis_count = sum(1 for msg in messages if "Synthesis" in str(msg))
        progress = min(1, synthesis_count / max(len(participants), 1))
        status[3]["progress"] = progress
    
    return status