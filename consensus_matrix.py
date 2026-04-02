"""
共识矩阵计算模块 - 完整版本
支持多人讨论和动态观点识别
"""

import json
from datetime import datetime
from typing import Dict, List, Optional


class ConsensusMatrix:
    """共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_viewpoints_step1(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[str]]:
        """提取讨论中的核心观点"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages[-20:]
            ])
            
            if len(discussion_text) > 3000:
                discussion_text = discussion_text[:3000]
            
            prompt = f"""Extract the MAIN VIEWPOINTS from this discussion.

DISCUSSION:
{discussion_text}

Extract 1-5 distinct viewpoints. Format as JSON:
{{"viewpoints": ["viewpoint1", "viewpoint2", ...]}}"""
            
            response = generate_response(
                llm_mode,
                prompt,
                group_id="system",
                user="System"
            )
            
            if not response:
                return None
            
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    data = json.loads(json_str)
                    viewpoints = data.get('viewpoints', [])
                    viewpoints = [v.strip() for v in viewpoints if v.strip()]
                    return viewpoints[:10] if viewpoints else None
            except:
                pass
            
            return None
        
        except Exception as e:
            print(f"❌ extract_viewpoints_step1 错误: {e}")
            return None
    
    def analyze_stances_step2(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """分析每个参与者的态度"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages[-20:]
            ])
            
            if len(discussion_text) > 3000:
                discussion_text = discussion_text[:3000]
            
            viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
            
            prompt = f"""Analyze each participant's stance on these viewpoints.

VIEWPOINTS:
{viewpoints_str}

DISCUSSION:
{discussion_text}

For each participant and viewpoint, use:
✅ = agrees, ❌ = disagrees, △ = neutral

Return JSON:
{{"stances": {{"participant_name": {{"viewpoint": "✅"}}, ...}}}}"""
            
            response = generate_response(
                llm_mode,
                prompt,
                group_id="system",
                user="System"
            )
            
            if not response:
                return None
            
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    data = json.loads(json_str)
                    stances = data.get('stances', {})
                    
                    # 确保所有参与者和观点都有数据
                    result = {}
                    for p in participants:
                        result[p] = {}
                        for vp in viewpoints:
                            stance = '△'
                            if p in stances:
                                if isinstance(stances[p], dict):
                                    for key, val in stances[p].items():
                                        if vp.lower() in key.lower() or key.lower() in vp.lower():
                                            stance = val if val in ['✅', '❌', '△'] else '△'
                                            break
                            result[p][vp] = stance
                    
                    return result
            except:
                pass
            
            # 返回默认值
            return {p: {vp: '△' for vp in viewpoints} for p in participants}
        
        except Exception as e:
            print(f"❌ analyze_stances_step2 错误: {e}")
            return None
    
    def calculate_consensus_metrics(
        self,
        viewpoints: List[str],
        stances_dict: Dict
    ) -> Dict:
        """计算共识指标"""
        metrics = {}
        
        for viewpoint in viewpoints:
            stances = [stances_dict.get(p, {}).get(viewpoint, '△') for p in stances_dict.keys()]
            
            agree = stances.count('✅')
            disagree = stances.count('❌')
            neutral = stances.count('△')
            total = len(stances)
            
            consensus_level = max(agree, disagree, neutral) / total if total > 0 else 0
            
            metrics[viewpoint] = {
                'agreement': agree,
                'disagreement': disagree,
                'neutral': neutral,
                'consensus_level': consensus_level
            }
        
        return metrics