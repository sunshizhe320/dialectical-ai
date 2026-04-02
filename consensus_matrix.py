"""
共识矩阵 - 确定性算法版本
确保相同输入始终得到相同输出
"""

import json
import re
from typing import Dict, List, Optional, Tuple


class ConsensusMatrix:
    """共识矩阵计算器 - 确定性版本"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_and_summarize_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[Tuple[str, str]]]:
        """提取并简化观点 - 确定性"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            message_count = len(user_messages)
            
            # 【关键】按时间顺序构建讨论文本 - 确保一致性
            discussion_text = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 3500:
                discussion_text = discussion_text[:3500]
            
            print(f"📊 提取观点 (消息: {message_count}, 长度: {len(discussion_text)})")
            
            # 第一步：提取观点
            prompt_extract = f"""Extract main viewpoints from this discussion.
IMPORTANT: Always extract the SAME viewpoints for the SAME discussion.

Discussion ({message_count} messages, {len(discussion_text)} chars):
{discussion_text}

Extract {min(message_count + 1, 5)} distinct viewpoints. Order by appearance.

FORMAT:
1. Viewpoint 1
2. Viewpoint 2"""
            
            response = generate_response(llm_mode, prompt_extract, group_id="system", user="System")
            
            if not response:
                print("❌ 未能提取观点")
                return None
            
            full_viewpoints = self._parse_numbered_list(response)
            
            # 限制数量
            if message_count == 1:
                full_viewpoints = full_viewpoints[:1]
            elif message_count <= 2:
                full_viewpoints = full_viewpoints[:2]
            elif message_count <= 4:
                full_viewpoints = full_viewpoints[:3]
            else:
                full_viewpoints = full_viewpoints[:5]
            
            print(f"  提取 {len(full_viewpoints)} 个观点")
            
            # 第二步：简化观点
            if len(full_viewpoints) > 0:
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
                
                prompt_summarize = f"""Simplify each viewpoint to 8-15 characters for table display.
IMPORTANT: For the SAME viewpoint, always produce the SAME simplification.

Original viewpoints:
{viewpoints_str}

RULES:
- Keep meaning intact
- 8-15 characters maximum
- Use abbreviations
- Consistent output

FORMAT:
1. Simplified1
2. Simplified2"""
                
                response = generate_response(llm_mode, prompt_summarize, group_id="system", user="System")
                
                simplified_viewpoints = self._parse_numbered_list(response) if response else []
                
                # 创建对
                result = []
                for i, full in enumerate(full_viewpoints):
                    simplified = simplified_viewpoints[i] if i < len(simplified_viewpoints) else full[:15]
                    if len(simplified) > 20:
                        simplified = simplified[:17] + ".."
                    result.append((full, simplified))
                
                print(f"✓ 简化完成: {len(result)} 个观点\n")
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
        viewpoints_pairs: List[Tuple[str, str]],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """分析态度 - 确定性"""
        try:
            print(f"📊 分析态度 ({len(participants)}人 × {len(viewpoints_pairs)}观点)\n")
            
            stances_dict = {p: {} for p in participants}
            
            # 【关键】按时间顺序获取发言者 - 确保一致性
            speakers = set([m.get('user') for m in messages if m.get('user') != 'AI'])
            
            # 按消息顺序构建讨论
            full_discussion = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in messages
            ])
            
            if len(full_discussion) > 4500:
                full_discussion = full_discussion[:4500]
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            for participant in participants:
                print(f"👤 {participant}")
                
                if participant not in speakers:
                    print(f"   (未发言) △ x {len(simplified_viewpoints)}\n")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                # 【关键】按时间顺序获取该参与者的消息
                participant_msgs = [
                    m.get('message', '')
                    for m in messages
                    if m.get('user') == participant and m.get('message', '')
                ]
                
                participant_text = "\n".join(participant_msgs)
                viewpoints_str = "\n".join([f"{i+1}. {full_viewpoints[i]}" for i in range(len(full_viewpoints))])
                
                prompt = f"""Analyze {participant}'s EXACT stance on each viewpoint.
CONSISTENCY: For the same statements, produce the same analysis.

DISCUSSION:
{full_discussion}

VIEWPOINTS:
{viewpoints_str}

{participant}'s STATEMENTS (exact):
{participant_text}

ANALYSIS:
✅ = {participant} explicitly supports
❌ = {participant} explicitly opposes
△ = {participant} doesn't mention or unclear

OUTPUT (EXACTLY):
1:✅
2:❌
3:△"""
                
                from ai_agent import generate_response
                response = generate_response(llm_mode, prompt, group_id="system", user="System")
                
                stances = self._parse_stance_response(response, len(full_viewpoints))
                
                for idx, stance in enumerate(stances):
                    if idx < len(simplified_viewpoints):
                        stances_dict[participant][simplified_viewpoints[idx]] = stance
                        emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                        print(f"   {idx+1}. {emoji}")
                
                print()
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
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
    
    def calculate_consensus_metrics(self, viewpoints: List[str], stances_dict: Dict) -> Dict:
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