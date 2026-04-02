"""
共识矩阵计算模块 - 增强版
支持多人讨论和动态观点识别
带有更好的 JSON 解析和后备方案
"""

import json
import re
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
        """提取讨论中的核心观点 - 动态调整期望数量"""
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
            
            # 根据消息数量动态调整观点期望
            message_count = len(user_messages)
            if message_count == 1:
                viewpoint_range = "exactly 1"
                examples = "Example: 1. AI should be used in education"
            elif message_count <= 2:
                viewpoint_range = "1-2"
                examples = "Example:\n1. First viewpoint\n2. Second viewpoint"
            elif message_count <= 4:
                viewpoint_range = "2-3"
                examples = "Example:\n1. First viewpoint\n2. Second viewpoint\n3. Third viewpoint"
            else:
                viewpoint_range = "3-5"
                examples = "Example:\n1. Viewpoint A\n2. Viewpoint B\n3. Viewpoint C"
            
            prompt = f"""Extract the MAIN VIEWPOINTS from this discussion. 
IMPORTANT: Extract ONLY viewpoints that are EXPLICITLY mentioned, do NOT create new ones.

Number of messages: {message_count}
Participants: {len(participants)}

DISCUSSION:
{discussion_text}

TASK: Extract {viewpoint_range} distinct viewpoints that are actually discussed.
DO NOT invent viewpoints. If only 1 viewpoint is discussed, return only 1.

FORMAT:
{examples}"""
            
            response = generate_response(
                llm_mode,
                prompt,
                group_id="system",
                user="System"
            )
            
            if not response:
                return None
            
            viewpoints = self._parse_numbered_list(response)
            
            # 验证提取的观点数量合理性
            if message_count == 1 and len(viewpoints) > 1:
                viewpoints = viewpoints[:1]
            elif message_count <= 2 and len(viewpoints) > 2:
                viewpoints = viewpoints[:2]
            elif message_count <= 4 and len(viewpoints) > 3:
                viewpoints = viewpoints[:3]
            elif len(viewpoints) > 5:
                viewpoints = viewpoints[:5]
            
            print(f"📊 提取了 {len(viewpoints)} 个观点 (来自 {message_count} 条消息)")
            
            return viewpoints if viewpoints else None
        
        except Exception as e:
            print(f"❌ extract_viewpoints_step1 错误: {e}")
            return None
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # 匹配 "1. text" 或 "1) text" 格式
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if len(item) > 3 and len(item) < 200:
                    items.append(item)
        
        return items
    
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
            participants_str = ", ".join(participants)
            
            prompt = f"""For each participant, decide if they AGREE (✅), DISAGREE (❌), or are NEUTRAL (△) on each viewpoint.

VIEWPOINTS:
{viewpoints_str}

PARTICIPANTS: {participants_str}

DISCUSSION:
{discussion_text}

RULES:
- ✅ = participant EXPLICITLY agrees or supports
- ❌ = participant EXPLICITLY disagrees or opposes  
- △ = participant doesn't mention it or is unclear/neutral

FORMAT - Return ONLY (no other text):
participant_name,viewpoint_number,symbol

Examples:
test,1,✅
amber,1,❌
test,2,△"""
            
            response = generate_response(
                llm_mode,
                prompt,
                group_id="system",
                user="System"
            )
            
            if not response:
                return None
            
            stances_dict = self._parse_stance_csv(response, participants, viewpoints)
            return stances_dict if stances_dict else None
        
        except Exception as e:
            print(f"❌ analyze_stances_step2 错误: {e}")
            return None
    
    def _parse_stance_csv(
        self, 
        text: str, 
        participants: List[str],
        viewpoints: List[str]
    ) -> Dict:
        """解析 CSV 格式的态度"""
        
        # 初始化所有参与者和观点为中立
        result = {p: {vp: '△' for vp in viewpoints} for p in participants}
        
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or ',' not in line:
                continue
            
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 3:
                continue
            
            participant_name = parts[0]
            try:
                viewpoint_idx = int(parts[1]) - 1
            except:
                continue
            
            stance = parts[2].strip()
            
            if stance not in ['✅', '❌', '△']:
                continue
            
            # 匹配参与者
            matched_p = None
            for p in participants:
                if p.lower() == participant_name.lower():
                    matched_p = p
                    break
            
            # 验证观点索引
            if matched_p and 0 <= viewpoint_idx < len(viewpoints):
                result[matched_p][viewpoints[viewpoint_idx]] = stance
        
        return result
    
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