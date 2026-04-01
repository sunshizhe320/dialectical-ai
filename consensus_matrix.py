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
    STEP 1: 提取讨论中的核心观点
    支持增量提取新消息中的观点
    """
    try:
        from ai_agent import generate_response
        
        user_messages = [m for m in messages if m.get('user') != 'AI']
        
        if not user_messages:
            return None
        
        discussion_text = "\n\n".join([
            f"{m.get('user')}: {m.get('message', '')}"
            for m in user_messages[-30:]
        ])
        
        if len(discussion_text) > 2500:
            discussion_text = discussion_text[:2500]
        
        participants_str = ", ".join(participants)
        
        # 改进的提示词 - 更精确的指导
        prompt = f"""You are an expert at analyzing discussions. Extract the MAIN VIEWPOINTS or CLAIMS being discussed.

IMPORTANT RULES:
1. Only extract viewpoints that are EXPLICITLY stated in the discussion
2. Do NOT create viewpoints that don't exist
3. Extract 1-3 viewpoints maximum based on what's actually discussed
4. Each viewpoint should be concise (under 12 words)
5. If there's only 1 message, extract the main points from that message

DISCUSSION:
{discussion_text}

TASK: Extract the core viewpoints being discussed. Be precise and only extract what is actually there.

RESPOND IN THIS JSON FORMAT ONLY (no other text):
{{
  "viewpoints": [
    "Viewpoint 1 - concise claim",
    "Viewpoint 2 - concise claim"
  ]
}}

Example:
{{
  "viewpoints": [
    "AI poses data security risks for minors",
    "AI reduces teacher administrative work"
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
        
        # 改进的解析逻辑 - 使用 JSON 解析
        viewpoints = self._parse_viewpoints_json(response)
        
        # 需要至少 1 个观点
        return viewpoints if len(viewpoints) >= 1 else None
    
    except Exception as e:
        print(f"❌ 观点提取失败: {e}")
        return None

def _parse_viewpoints_json(self, response: str) -> List[str]:
    """使用 JSON 解析观点 - 更准确"""
    try:
        import json
        
        # 尝试提取 JSON
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            viewpoints = data.get('viewpoints', [])
            
            # 清理和验证
            viewpoints = [
                vp.strip() 
                for vp in viewpoints 
                if isinstance(vp, str) and vp.strip() and len(vp.strip()) > 3
            ]
            
            return viewpoints[:5]  # 最多 5 个观点
    except:
        pass
    
    # 备用方案：文本解析
    return self._parse_viewpoints(response)

def _parse_viewpoints(self, response: str) -> List[str]:
    """备用文本解析方法"""
    viewpoints = []
    lines = response.split('\n')
    in_viewpoints = False
    
    for line in lines:
        if 'VIEWPOINT' in line.upper() or 'viewpoints' in line.lower():
            in_viewpoints = True
            continue
        
        if in_viewpoints and line.strip():
            # 匹配数字开头的行
            if line.strip() and line.strip()[0].isdigit() and '.' in line:
                vp = line.split('.', 1)[1].strip()
                if vp and len(vp) > 3 and len(vp) < 150:
                    viewpoints.append(vp)
            elif '-' in line and not line.strip()[0].isdigit():
                vp = line.split('-', 1)[1].strip()
                if vp and len(vp) > 3 and len(vp) < 150:
                    viewpoints.append(vp)
    
    return viewpoints[:5]  # 最多 5 个观点
    
    def _parse_stances(
        self,
        response: str,
        participants: List[str],
        viewpoints: List[str]
    ) -> Dict:
        """解析LLM返回的态度"""
        stances_dict = {p: {} for p in participants}
        lines = response.split('\n')
        in_stances = False
        
        for line in lines:
            if 'STANCE' in line.upper():
                in_stances = True
                continue
            
            if in_stances and ':' in line and ('✅' in line or '❌' in line or '△' in line):
                parts = [p.strip() for p in line.split(':')]
                if len(parts) >= 3:
                    participant = parts[0].strip()
                    viewpoint_text = parts[1].strip()
                    stance = parts[2].strip()
                    
                    # 匹配参与者
                    matched_p = None
                    for p in participants:
                        if p.lower() == participant.lower():
                            matched_p = p
                            break
                    
                    # 匹配观点
                    matched_vp = None
                    for vp in viewpoints:

                        if viewpoint_text.lower() in vp.lower() or vp.lower() in viewpoint_text.lower():
                            matched_vp = vp
                            break
                    
                    if matched_p and matched_vp:
                        if '✅' in stance:
                            stances_dict[matched_p][matched_vp] = '✅'
                        elif '❌' in stance:
                            stances_dict[matched_p][matched_vp] = '❌'
                        else:
                            stances_dict[matched_p][matched_vp] = '△'
        
        # 填充缺失值
        for p in participants:
            for vp in viewpoints:
                if vp not in stances_dict[p]:
                    stances_dict[p][vp] = '△'
        
        return stances_dict
    
    def calculate_consensus_metrics(
        self,
        viewpoints: List[str],
        stances_dict: Dict
    ) -> Dict:
        """计算共识指标"""
        metrics = {}
        
        for viewpoint in viewpoints:
            stances = [stances_dict.get(p, {}).get(viewpoint, '△') for p in stances_dict.keys()]
            
            agree_count = stances.count('✅')
            disagree_count = stances.count('❌')
            neutral_count = stances.count('△')
            
            total = len(stances)
            if total > 0:
                consensus_level = max(agree_count, disagree_count, neutral_count) / total
            else:
                consensus_level = 0
            
            metrics[viewpoint] = {
                'agreement': agree_count,
                'disagreement': disagree_count,
                'neutral': neutral_count,
                'consensus_level': consensus_level,
                'dominant': max(['✅', '❌', '△'], key=lambda x: stances.count(x))
            }
        
        return metrics
    
    def generate_full_matrix(
        self,
        messages: List[Dict],
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """生成完整矩阵"""
        viewpoints = self.extract_viewpoints_step1(messages, participants, llm_mode)
        if not viewpoints:
            return None
        
        stances_dict = self.analyze_stances_step2(messages, participants, viewpoints, llm_mode)
        if not stances_dict:
            return None
        
        metrics = self.calculate_consensus_metrics(viewpoints, stances_dict)
        
        return {
            'viewpoints': viewpoints,
            'stances': stances_dict,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }