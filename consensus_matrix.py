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
            
            prompt = f"""Read this discussion carefully. Identify the 3-4 MAIN VIEWPOINTS or CLAIMS that participants are discussing.

DISCUSSION:
{discussion_text}

PARTICIPANTS: {participants_str}

TASK: Extract the core viewpoints being discussed. These should be distinct positions or concerns raised.

RESPOND IN THIS FORMAT ONLY:

VIEWPOINTS:
1. [Viewpoint 1 - concise, max 10 words]
2. [Viewpoint 2 - concise, max 10 words]
3. [Viewpoint 3 - concise, max 10 words]

Example format:
VIEWPOINTS:
1. AI poses data security risks for minors
2. AI can reduce teacher administrative work
3. AI helps address educational inequality"""
            
            response = generate_response(
                llm_mode,
                prompt,
                group_id="system",
                user="System"
            )
            
            if not response:
                return None
            
            viewpoints = self._parse_viewpoints(response)
            return viewpoints if len(viewpoints) >= 3 else None
        
        except Exception as e:
            print(f"❌ 观点提取失败: {e}")
            return None
    
    def _parse_viewpoints(self, response: str) -> List[str]:
        """解析LLM返回的观点"""
        viewpoints = []
        lines = response.split('\n')
        in_viewpoints = False
        
        for line in lines:
            if 'VIEWPOINT' in line.upper():
                in_viewpoints = True
                continue
            if in_viewpoints and line.strip():
                if line.strip()[0].isdigit() and '.' in line:
                    vp = line.split('.', 1)[1].strip()
                    if vp and len(vp) > 3:
                        viewpoints.append(vp[:100])
                elif not line.strip()[0].isdigit():
                    break
        
        return viewpoints
    
    def analyze_stances_step2(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """
        STEP 2: 分析每个参与者对每个观点的立场
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            
            discussion_text = "\n\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages[-30:]
            ])
            
            if len(discussion_text) > 2500:
                discussion_text = discussion_text[:2500]
            
            viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
            participants_str = ", ".join(participants)
            
            prompt = f"""Analyze each participant's stance on these viewpoints. Read CAREFULLY.

VIEWPOINTS:
{viewpoints_str}

DISCUSSION:
{discussion_text}

PARTICIPANTS: {participants_str}

RULES:
- Use ✅ only if participant EXPLICITLY or STRONGLY agrees/supports the viewpoint
- Use ❌ only if participant EXPLICITLY or STRONGLY disagrees/opposes the viewpoint
- Use △ if participant did NOT discuss it, or is unclear/neutral

RESPOND IN THIS FORMAT ONLY:

STANCES:
Participant_Name: Viewpoint_1: [✅ or ❌ or △]
Participant_Name: Viewpoint_2: [✅ or ❌ or △]
Participant_Name: Viewpoint_3: [✅ or ❌ or △]
(repeat for all participants and viewpoints)

Example:
STANCES:
Amber: AI poses data security risks for minors: △
Amber: AI can reduce teacher administrative work: ✅
test: AI poses data security risks for minors: ✅
test: AI can reduce teacher administrative work: △"""
            
            response = generate_response(
                llm_mode,
                prompt,
                group_id="system",
                user="System"
            )
            
            if not response:
                return None
            
            stances_dict = self._parse_stances(response, participants, viewpoints)
            return stances_dict
        
        except Exception as e:
            print(f"❌ 态度分析失败: {e}")
            return None
    
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