"""
共识矩阵 - 完整提炼版本
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
        """提取��整观点 - 不切断"""
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
            
            # 提取完整观点
            prompt = f"""Extract all MAIN viewpoints from this discussion.
Keep each viewpoint COMPLETE - do not cut off or shorten.

Discussion:
{discussion_text}

Extract 1-{min(message_count + 1, 5)} distinct viewpoints. Keep full text.

FORMAT:
1. Complete viewpoint 1
2. Complete viewpoint 2
3. Complete viewpoint 3"""
            
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
            
            print(f"✓ 提取 {len(viewpoints)} 个完整观点\n")
            
            return viewpoints if viewpoints else None
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表 - 完整保留"""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                # 完整保留，不切断
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
        """分析态度 - 超强版本"""
        try:
            print(f"📊 分析态度 ({len(participants)}人 × {len(viewpoints)}观点)\n")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取已发言的参与者
            speakers = set([m.get('user') for m in messages if m.get('user') != 'AI'])
            
            # 完整讨论上下文
            full_discussion = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in messages
            ])
            
            if len(full_discussion) > 4500:
                full_discussion = full_discussion[:4500]
            
            for participant in participants:
                print(f"👤 {participant}")
                
                # 未发言 → 中立
                if participant not in speakers:
                    print(f"   (未发言) △\n")
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                    continue
                
                # 获取该参与者的所有消息
                participant_msgs = [
                    m.get('message', '')
                    for m in messages
                    if m.get('user') == participant and m.get('message', '')
                ]
                
                participant_text = "\n".join(participant_msgs)
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
                
                # 超强提示词
                prompt = f"""Analyze {participant}'s stance on EACH viewpoint.
Use the FULL DISCUSSION CONTEXT to understand implicit positions.

FULL DISCUSSION:
{full_discussion}

VIEWPOINTS TO ANALYZE:
{viewpoints_str}

{participant}'s STATEMENTS:
{participant_text}

ANALYSIS RULES:
1. Read participant's exact words
2. Look for: "支持/同意/赞成" = ✅
3. Look for: "反对/不同意/问题" = ❌
4. Look for: "可能/也许/取决于" = △
5. If mentioned issue/concern = often ❌
6. If agrees with others = ✅
7. If raises limitations = △

FOR EACH VIEWPOINT output EXACTLY:
1:✅
2:❌
3:△

NO OTHER TEXT, ONLY NUMBERS AND SYMBOLS."""
                
                from ai_agent import generate_response
                response = generate_response(llm_mode, prompt, group_id="system", user="System")
                
                stances = self._parse_stance_response_advanced(response, len(viewpoints))
                
                for idx, stance in enumerate(stances):
                    if idx < len(viewpoints):
                        stances_dict[participant][viewpoints[idx]] = stance
                        emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                        print(f"   {viewpoints[idx][:25]}... → {emoji}")
                
                print()
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_stance_response_advanced(self, response: str, num_viewpoints: int) -> List[str]:
        """超强态度解析 - 多层解析"""
        stances = ['△'] * num_viewpoints
        response_str = response or ""
        
        # 方法1：查找 "N:符号" 模式
        matches = re.finditer(r'(\d+)\s*:\s*([✅❌△])', response_str)
        for match in matches:
            try:
                idx = int(match.group(1)) - 1
                stance = match.group(2)
                if 0 <= idx < num_viewpoints:
                    stances[idx] = stance
            except:
                pass
        
        # 方法2：如果没有找到，查找关键词
        if all(s == '△' for s in stances):
            lines = response_str.split('\n')
            for line in lines:
                line = line.strip()
                # 提取数字
                num_match = re.match(r'^(\d+)', line)
                if num_match:
                    idx = int(num_match.group(1)) - 1
                    if 0 <= idx < num_viewpoints:
                        # 找符号
                        if '✅' in line or '支持' in line.lower() or 'support' in line.lower():
                            stances[idx] = '✅'
                        elif '❌' in line or '反对' in line.lower() or 'oppose' in line.lower():
                            stances[idx] = '❌'
                        elif '△' in line:
                            stances[idx] = '△'
        
        # 方法3：如果还是全△，逐个字符检查
        if all(s == '△' for s in stances):
            for i in range(num_viewpoints):
                for char in response_str:
                    if char in ['✅', '❌', '△']:
                        stances[i] = char
                        break
        
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