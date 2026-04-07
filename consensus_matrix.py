"""
共识矩阵 - 完整版本
实时提取观点和分析态度
"""

import json
import re
from typing import Dict, List, Tuple, Optional


class ConsensusMatrix:
    """共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control"
    ) -> Optional[List[Tuple[str, str]]]:
        """
        提取观点并生成简化版本
        返回: [(完整观点, 简化观点), ...]
        """
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            # 构建讨论文本
            discussion_text = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 3000:
                discussion_text = discussion_text[:3000]
            
            print(f"📊 提取观点 ({len(user_messages)} 条消息)")
            
            # 第一步：提取完整观点
            prompt_extract = f"""Extract 1-5 KEY viewpoints from this discussion.

Discussion:
{discussion_text}

Output format (numbered list):
1. Complete viewpoint 1
2. Complete viewpoint 2
...

Rules:
- Extract ONLY actual viewpoints mentioned by participants
- NO invented viewpoints
- Keep the original meaning
- Each viewpoint 1-2 sentences"""
            
            response = generate_response(
                llm_mode, 
                prompt_extract, 
                group_id="system", 
                user="System"
            )
            
            if not response:
                print("❌ 无法提取观点")
                return None
            
            full_viewpoints = self._parse_numbered_list(response)
            print(f"✓ 提取了 {len(full_viewpoints)} 个观点")
            
            # 第二步：生成简化版本
            if full_viewpoints:
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
                
                prompt_simplify = f"""Simplify each viewpoint to 8-15 Chinese characters.

Original viewpoints:
{viewpoints_str}

Output format (numbered list):
1. 简化版本1
2. 简化版本2
...

Rules:
- Keep the KEY meaning
- 8-15 characters ONLY
- Use simple words
- No complex sentences

Examples:
"Remote work saves commute time" → "节省通勤时间"
"远程办公可以节省上班时间" → "节省通勤"
"""
                
                response = generate_response(
                    llm_mode, 
                    prompt_simplify, 
                    group_id="system", 
                    user="System"
                )
                
                simplified_viewpoints = self._parse_numbered_list(response) if response else []
                
                # 创建 (完整, 简化) 对
                result = []
                for i, full in enumerate(full_viewpoints):
                    simplified = simplified_viewpoints[i] if i < len(simplified_viewpoints) else full[:15]
                    # 确保不超过 20 字
                    if len(simplified) > 20:
                        simplified = simplified[:17] + ".."
                    result.append((full, simplified))
                
                print(f"✓ 简化完成\n")
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ 提取观点错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def analyze_stances(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints_pairs: List[Tuple[str, str]],
        llm_mode: str = "Control"
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """
        分析每个参与者对每个观点的态度
        返回: {参与者: {简化观点: '✅/❌/△'}}
        """
        try:
            from ai_agent import generate_response
            
            print(f"📊 分析态度 ({len(participants)} 人 × {len(viewpoints_pairs)} 观点)")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取发言者
            speakers = set([m.get('user') for m in messages if m.get('user') != 'AI'])
            
            # 完整讨论文本
            full_discussion = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in messages
            ])
            
            if len(full_discussion) > 4000:
                full_discussion = full_discussion[:4000]
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            for participant in participants:
                print(f"👤 {participant}")
                
                # 未发言 → 全部中立
                if participant not in speakers:
                    print(f"   (未发言) 标记为中立")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                # 获取该参与者的消息
                participant_msgs = [
                    m.get('message', '')
                    for m in messages
                    if m.get('user') == participant and m.get('message', '')
                ]
                
                participant_text = "\n".join(participant_msgs)
                viewpoints_str = "\n".join([f"{i+1}. {full_viewpoints[i]}" for i in range(len(full_viewpoints))])
                
                prompt = f"""Analyze {participant}'s stance on EACH viewpoint.

DISCUSSION:
{full_discussion}

VIEWPOINTS:
{viewpoints_str}

{participant}'s STATEMENTS:
{participant_text}

For each viewpoint (1-{len(full_viewpoints)}), output:
1:✅
2:❌
3:△
...

Rules:
✅ = {participant} explicitly supports
❌ = {participant} explicitly opposes  
△ = {participant} doesn't mention or unclear"""
                
                response = generate_response(
                    llm_mode, 
                    prompt, 
                    group_id="system", 
                    user="System"
                )
                
                stances = self._parse_stances(response, len(full_viewpoints))
                
                for idx, stance in enumerate(stances):
                    if idx < len(simplified_viewpoints):
                        stances_dict[participant][simplified_viewpoints[idx]] = stance
                        emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                        print(f"   {idx+1}. {emoji}")
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ 分析态度错误: {e}")
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
    
    def _parse_stances(self, response: str, num_viewpoints: int) -> List[str]:
        """解析态度响应"""
        stances = ['△'] * num_viewpoints
        
        if not response:
            return stances
        
        # 查找 "数字:符号" 格式
        matches = re.finditer(r'(\d+)\s*:\s*([✅❌△])', response)
        for match in matches:
            try:
                idx = int(match.group(1)) - 1
                stance = match.group(2)
                if 0 <= idx < num_viewpoints:
                    stances[idx] = stance
            except:
                pass
        
        return stances