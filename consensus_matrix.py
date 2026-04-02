"""
共识矩阵 - 最终版本
"""

import json
import re
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
        """提取观点"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            message_count = len(user_messages)
            
            discussion_text = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 3500:
                discussion_text = discussion_text[:3500]
            
            print(f"📊 提取观点 ({message_count} 条消息)")
            
            prompt = f"""Extract all MAIN viewpoints from this discussion.

Discussion:
{discussion_text}

List all distinct viewpoints. Keep them complete and clear.

FORMAT:
1. viewpoint 1
2. viewpoint 2"""
            
            response = generate_response(llm_mode, prompt, group_id="system", user="System")
            
            if not response:
                return None
            
            raw_viewpoints = self._parse_numbered_list(response)
            
            print(f"  提取 {len(raw_viewpoints)} 个观点，进行智能缩写...")
            simplified = [self._smart_abbreviate(vp) for vp in raw_viewpoints]
            
            # 限制数量
            if message_count == 1:
                simplified = simplified[:1]
            elif message_count <= 2:
                simplified = simplified[:2]
            elif message_count <= 4:
                simplified = simplified[:3]
            else:
                simplified = simplified[:5]
            
            print(f"✓ 最终 {len(simplified)} 个观点\n")
            
            return simplified if simplified else None
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def _smart_abbreviate(self, viewpoint: str) -> str:
        """智能缩写观点"""
        if len(viewpoint) <= 25:
            return viewpoint
        
        words = viewpoint.split('。')[0].split('、')[0].strip()
        
        if len(words) > 20:
            try:
                import jieba
                words_seg = list(jieba.cut(words))
                keywords = [w for w in words_seg if len(w) > 1][:4]
                core = ''.join(keywords)
                return core if core else words[:20]
            except:
                return words[:20]
        
        return words
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if len(item) > 2 and len(item) < 500:
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
            print(f"📊 分析态度 ({len(participants)}人 × {len(viewpoints)}观点)\n")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取已发言的参与者
            speakers = set([m.get('user') for m in messages if m.get('user') != 'AI'])
            
            full_discussion = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in messages
            ])
            
            if len(full_discussion) > 4000:
                full_discussion = full_discussion[:4000]
            
            for participant in participants:
                print(f"👤 {participant}")
                
                # 【关键】未发言的参与者直接标记为△
                if participant not in speakers:
                    print(f"   (未发言) △\n")
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                    continue
                
                participant_msgs = [
                    m.get('message', '')
                    for m in messages
                    if m.get('user') == participant
                ]
                
                participant_text = "\n".join(participant_msgs)
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
                
                prompt = f"""Analyze {participant}'s stance on each viewpoint.

DISCUSSION:
{full_discussion}

VIEWPOINTS:
{viewpoints_str}

{participant}'s STATEMENTS:
{participant_text}

OUTPUT (only):
1:���
2:△
3:❌"""
                
                from ai_agent import generate_response
                response = generate_response(llm_mode, prompt, group_id="system", user="System")
                
                stances = self._parse_stance_response(response, len(viewpoints))
                
                for idx, stance in enumerate(stances):
                    if idx < len(viewpoints):
                        stances_dict[participant][viewpoints[idx]] = stance
                        emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                        print(f"   {viewpoints[idx][:20]}... → {emoji}")
                
                print()
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def _parse_stance_response(self, response: str, num_viewpoints: int) -> List[str]:
        """解析态度"""
        stances = ['△'] * num_viewpoints
        
        matches = re.finditer(r'(\d+)\s*:\s*([✅❌△])', response or "")
        for match in matches:
            try:
                idx = int(match.group(1)) - 1
                stance = match.group(2)
                if 0 <= idx < num_viewpoints:
                    stances[idx] = stance
            except:
                pass
        
        return stances
    
    def calculate_consensus_metrics(
        self,
        viewpoints: List[str],
        stances_dict: Dict
    ) -> Dict:
        """计算指标"""
        metrics = {}
        
        for vp in viewpoints:
            stances = [stances_dict.get(p, {}).get(vp, '△') for p in stances_dict.keys()]
            
            agree = stances.count('✅')
            disagree = stances.count('❌')
            neutral = stances.count('△')
            total = len(stances) or 1
            
            metrics[vp] = {
                'agreement': agree,
                'disagreement': disagree,
                'neutral': neutral,
                'consensus_level': max(agree, disagree, neutral) / total
            }
        
        return metrics