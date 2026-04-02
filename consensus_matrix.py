"""
增强的共识矩阵计算模块
支持增量更新和实时计算
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from ai_agent import generate_response


@dataclass
class ViewpointAnalysis:
    """观点分析结果"""
    viewpoint: str
    participant_stances: Dict[str, str]  # {participant: '✅'|'❌'|'△'}
    consensus_level: float  # 0-1
    agreement_count: int
    disagreement_count: int
    neutral_count: int


class ConsensusMatrix:
    """增强的共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
    
def extract_viewpoints_step1(
    self, 
    messages: List[Dict], 
    participants: List[str],
    llm_mode: str = "AI-Scaffolded"
) -> Optional[List[str]]:
    """
    动态提取讨论中的所有观点 - 无数量限制
    """
    try:
        from ai_agent import generate_response
        
        user_messages = [m for m in messages if m.get('user') != 'AI']
        
        if not user_messages:
            return None
        
        # 组织讨论文本
        discussion_text = "\n\n".join([
            f"{m.get('user')}: {m.get('message', '')}"
            for m in user_messages
        ])
        
        if len(discussion_text) > 4000:
            discussion_text = discussion_text[:4000]
        
        participants_str = ", ".join(participants)
        message_count = len(user_messages)
        
        # 动态提示词 - 根据消息数量调整
        prompt = f"""You are an expert at analyzing group discussions. Extract ALL MAIN VIEWPOINTS or CLAIMS being discussed.

DISCUSSION CONTEXT:
- Number of messages: {message_count}
- Participants: {participants_str}
- Number of participants: {len(participants)}

IMPORTANT RULES:
1. Extract ALL distinct viewpoints mentioned by ANY participant
2. Do NOT create viewpoints that don't exist
3. Each viewpoint should be concise (10-20 words)
4. Extract as many viewpoints as actually discussed (1-10+)
5. Group similar viewpoints together but keep distinct perspectives separate

DISCUSSION:
{discussion_text}

RESPOND IN JSON FORMAT ONLY:
{{
  "viewpoints": [
    "Viewpoint 1: distinct perspective/claim",
    "Viewpoint 2: different perspective/claim",
    "Viewpoint 3: another perspective/claim"
  ]
}}"""
        
        response = generate_response(
            llm_mode,
            prompt,
            group_id="system",
            user="System"
        )
        
        if not response:
            return None
        
        viewpoints = self._parse_viewpoints_json(response)
        
        # 至少返回 1 个观点，无上限
        return viewpoints if len(viewpoints) >= 1 else None
    
    except Exception as e:
        print(f"❌ 观点提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def _parse_viewpoints_json(self, response: str) -> List[str]:
    """解析所有观点 - 无数量限制"""
    try:
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            viewpoints = data.get('viewpoints', [])
            
            # 清理和验证 - 不限制数量
            viewpoints = [
                vp.strip() 
                for vp in viewpoints 
                if isinstance(vp, str) and vp.strip() and len(vp.strip()) > 3
            ]
            
            return viewpoints  # 无上限返回所有观点
    except Exception as e:
        print(f"JSON 解析失败: {e}")
    
    return self._parse_viewpoints_fallback(response)

def _parse_viewpoints_fallback(self, response: str) -> List[str]:
    """备用文本解析方法 - 支持多个观点"""
    viewpoints = []
    lines = response.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配数字开头
        if line and line[0].isdigit() and '.' in line:
            vp = line.split('.', 1)[1].strip()
            if vp and len(vp) > 3:
                viewpoints.append(vp)
        # 匹配符号开头
        elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
            vp = line[1:].strip()
            if vp and len(vp) > 3:
                viewpoints.append(vp)
    
    return viewpoints  # 无上限