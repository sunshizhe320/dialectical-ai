"""
智能共识矩阵计算模块 - 改进版
更精准的态度分析，减少误判
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ConsensusMatrix:
    """智能共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_viewpoints_step1(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[str]]:
        """提取观点"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            message_count = len(user_messages)
            
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages[-20:]
            ])
            
            if len(discussion_text) > 3000:
                discussion_text = discussion_text[:3000]
            
            # 根据消息数量调整
            if message_count == 1:
                range_text = "exactly 1"
            elif message_count <= 2:
                range_text = "1-2"
            elif message_count <= 4:
                range_text = "1-2"
            else:
                range_text = "2-3"
            
            prompt = f"""Extract the MAIN VIEWPOINTS from this discussion.

STRICT RULE: Only extract viewpoints that are EXPLICITLY stated. Do NOT invent or interpret.

Number of messages: {message_count}

DISCUSSION:
{discussion_text}

Extract {range_text} distinct viewpoints that are actually discussed.

FORMAT - List each viewpoint on a new line starting with a number:
1. [Viewpoint 1 - quoted or paraphrased from discussion]
2. [Viewpoint 2 - quoted or paraphrased from discussion]"""
            
            response = generate_response(llm_mode, prompt, group_id="system", user="System")
            
            if not response:
                return None
            
            viewpoints = self._parse_numbered_list(response)
            
            # 限制数量
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
        """分析态度"""
        try:
            stances_dict = {p: {} for p in participants}
            
            # 为每个参与者和每个观点分析
            for viewpoint in viewpoints:
                for participant in participants:
                    stance = self._analyze_single_stance(
                        participant,
                        viewpoint,
                        messages,
                        llm_mode
                    )
                    stances_dict[participant][viewpoint] = stance
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ analyze_stances_step2 错误: {e}")
            return None
    
    def _analyze_single_stance(
        self,
        participant: str,
        viewpoint: str,
        messages: List[Dict],
        llm_mode: str
    ) -> str:
        """分析单个参与者对单个观点的态度 - 最精准版本"""
        from ai_agent import generate_response
        
        # 提取该参与者的所有消息
        participant_msgs = [
            m.get('message', '') 
            for m in messages 
            if m.get('user') == participant and m.get('message', '')
        ]
        
        # 如果参与者没有发言，返回中立
        if not participant_msgs:
            print(f"    {participant}: (未发言) → △")
            return '△'
        
        participant_text = "\n".join(participant_msgs)
        
        # 简化提示词，只关注关键信息
        prompt = f"""Analyze {participant}'s stance ONLY based on their exact statements.

VIEWPOINT:
"{viewpoint}"

{participant}'s STATEMENTS:
{participant_text}

TASK: Based on what {participant} said, do they agree or disagree with the viewpoint above?

Output ONLY one symbol:
✅ if {participant} supports/agrees
❌ if {participant} opposes/disagrees
△ if {participant} doesn't mention it or unclear

Your answer:"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return '△'
        
        # 从响应中提取第一个有效符号
        response_clean = response.strip()
        
        for char in response_clean:
            if char == '✅':
                print(f"    {participant}: (支持) → ✅")
                return '✅'
            elif char == '❌':
                print(f"    {participant}: (反对) → ❌")
                return '❌'
        
        print(f"    {participant}: (未确定) → △")
        return '△'
    
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