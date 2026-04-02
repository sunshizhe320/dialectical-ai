"""
智能共识矩阵计算模块 - 稳健版本
简化提示词，确保态度正确识别
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
                for m in user_messages
            ])
            
            if len(discussion_text) > 3000:
                discussion_text = discussion_text[:3000]
            
            print(f"\n📊 [观点提取] 消息: {message_count}")
            
            # 简化为单轮提取
            prompt = f"""Extract all MAIN viewpoints from this discussion.

Messages: {message_count}

Discussion:
{discussion_text}

Extract all distinct viewpoints. For each, include original quote or paraphrase.

FORMAT - numbered list only:
1. viewpoint 1
2. viewpoint 2
3. viewpoint 3"""
            
            response = generate_response(llm_mode, prompt, group_id="system", user="System")
            
            if not response:
                return None
            
            viewpoints = self._parse_numbered_list(response)
            
            # 限制数量
            if message_count == 1:
                viewpoints = viewpoints[:1]
            elif message_count <= 2:
                viewpoints = viewpoints[:2]
            elif message_count <= 4:
                viewpoints = viewpoints[:3]
            else:
                viewpoints = viewpoints[:5]
            
            print(f"✓ 提取 {len(viewpoints)} 个观点\n")
            
            return viewpoints if viewpoints else None
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
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
                if len(item) > 3 and len(item) < 300:
                    items.append(item)
        
        return items
    
    def analyze_stances_step2(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """分析态度 - 超稳健版本"""
        try:
            print(f"\n📊 [态度分析] {len(participants)} 人 × {len(viewpoints)} 观点\n")
            
            stances_dict = {p: {} for p in participants}
            
            # 构建讨论文本
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in messages
            ])
            
            if len(discussion_text) > 3000:
                discussion_text = discussion_text[:3000]
            
            # 为每个参与者分析所有观点
            for participant in participants:
                print(f"👤 {participant}")
                
                # 获取该参与者的消息
                participant_msgs = [
                    m.get('message', '')
                    for m in messages
                    if m.get('user') == participant
                ]
                
                if not participant_msgs:
                    print(f"   (未发言) → 所有观点 △\n")
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                    continue
                
                participant_text = "\n".join(participant_msgs)
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
                
                # 构建简单清晰的提示
                prompt = f"""Analyze {participant}'s stance on each viewpoint.

VIEWPOINTS:
{viewpoints_str}

{participant}'s statements:
{participant_text}

For EACH viewpoint, output ONLY the number and one symbol:
- ✅ if {participant} CLEARLY supports it
- ❌ if {participant} CLEARLY opposes it  
- △ if NOT mentioned or unclear

OUTPUT FORMAT (one per line):
1:✅
2:△
3:❌
...

Do NOT include any other text."""
                
                from ai_agent import generate_response
                response = generate_response(llm_mode, prompt, group_id="system", user="System")
                
                if response:
                    # 解析响应
                    stances = self._parse_stance_response(response, len(viewpoints))
                    
                    for idx, stance in enumerate(stances):
                        if idx < len(viewpoints):
                            stances_dict[participant][viewpoints[idx]] = stance
                            emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                            print(f"   {viewpoints[idx][:30]}... → {emoji}")
                else:
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                
                print()
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_stance_response(self, response: str, num_viewpoints: int) -> List[str]:
        """解析态度响应 - 超稳健"""
        stances = ['△'] * num_viewpoints
        
        # 查找所有 "N:符号" 的模式
        matches = re.finditer(r'(\d+)\s*:\s*([✅❌△])', response)
        
        for match in matches:
            try:
                idx = int(match.group(1)) - 1
                stance = match.group(2)
                
                if 0 <= idx < num_viewpoints:
                    stances[idx] = stance
            except:
                pass
        
        # 如果没找到，尝试逐行解析
        if all(s == '△' for s in stances):
            for line in response.split('\n'):
                line = line.strip()
                if ':' in line and len(line) < 20:
                    # 尝试从行中提取
                    for i in range(1, num_viewpoints + 1):
                        if str(i) in line:
                            if '✅' in line:
                                stances[i-1] = '✅'
                            elif '❌' in line:
                                stances[i-1] = '❌'
                            break
        
        return stances
    
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