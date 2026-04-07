"""
共识矩阵 - 完整的 AI 智能版本
自动提取观点、简化、分析态度
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
            
            # 控制长度
            if len(discussion_text) > 2000:
                discussion_text = discussion_text[:2000]
            
            print(f"\n📊 Extracting viewpoints from {len(user_messages)} messages...")
            
            # 提取观点
            prompt_extract = f"""Analyze this discussion and extract the MAIN viewpoints/arguments mentioned.

DISCUSSION:
{discussion_text}

TASK: Extract 2-5 distinct viewpoints that people mentioned.

OUTPUT FORMAT (numbered list, ONLY the viewpoint, nothing else):
1. Viewpoint 1
2. Viewpoint 2
3. Viewpoint 3

RULES:
- Extract ACTUAL viewpoints from the discussion
- NO invented viewpoints
- Keep original meaning
- Each 1-2 sentences max
- Different perspectives/arguments only"""
            
            response = generate_response(
                llm_mode, 
                prompt_extract, 
                group_id="system", 
                user="System"
            )
            
            if not response:
                print("❌ Failed to extract viewpoints")
                return None
            
            full_viewpoints = self._parse_numbered_list(response)
            
            if not full_viewpoints:
                print("❌ No viewpoints parsed from response")
                print(f"Response: {response}")
                return None
            
            print(f"✓ Extracted {len(full_viewpoints)} viewpoints")
            for i, vp in enumerate(full_viewpoints, 1):
                print(f"  {i}. {vp[:50]}...")
            
            # 简化观点到 8-15 字
            if full_viewpoints:
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
                
                prompt_simplify = f"""Simplify each viewpoint to 8-15 Chinese characters.

VIEWPOINTS:
{viewpoints_str}

TASK: Create a simplified version for each viewpoint (8-15 characters)

OUTPUT FORMAT (numbered list):
1. 简化观点1
2. 简化观点2
3. 简化观点3

RULES:
- Keep the KEY meaning
- Exactly 8-15 characters
- Simple words
- Can use phrases"""
                
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
                    # 检查长度
                    if len(simplified) > 20:
                        simplified = simplified[:17] + "…"
                    result.append((full, simplified))
                
                print(f"✓ Simplified viewpoints:")
                for i, (full, simp) in enumerate(result, 1):
                    print(f"  {i}. {simp}")
                
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ Error extracting viewpoints: {e}")
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
            
            print(f"\n📈 Analyzing stances for {len(participants)} participants...")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取发言者
            speakers = set([m.get('user') for m in messages if m.get('user') != 'AI'])
            
            # 完整讨论文本
            full_discussion = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in messages
                if m.get('user') != 'AI'
            ])
            
            if len(full_discussion) > 3000:
                full_discussion = full_discussion[:3000]
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                # 未发言 → 全部中立
                if participant not in speakers:
                    print("(not spoken) → all neutral")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                # 获取该参与者的消息
                participant_msgs = [
                    m.get('message', '')
                    for m in messages
                    if m.get('user') == participant and m.get('message', '')
                ]
                
                if not participant_msgs:
                    print("(no messages) → all neutral")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_text = "\n".join(participant_msgs)
                viewpoints_str = "\n".join([f"{i+1}. {full_viewpoints[i]}" for i in range(len(full_viewpoints))])
                
                prompt = f"""Analyze {participant}'s stance on each viewpoint.

DISCUSSION:
{full_discussion}

VIEWPOINTS TO ANALYZE:
{viewpoints_str}

{participant}'s STATEMENTS:
{participant_text}

TASK: For each viewpoint, determine {participant}'s stance.

OUTPUT FORMAT (only numbers and symbols):
1:✅
2:❌
3:△

RULES:
✅ = {participant} SUPPORTS/AGREES with this viewpoint
❌ = {participant} OPPOSES/DISAGREES with this viewpoint
△ = {participant} doesn't mention or NEUTRAL on this viewpoint

Return ONLY the numbered list with symbols, nothing else."""
                
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
                
                # 显示结果
                results = [f"{i+1}:{s}" for i, s in enumerate(stances)]
                print(" | ".join(results))
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error analyzing stances: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # 匹配 "1. " 或 "1) " 格式
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                # 过滤空和太长的项
                if 2 < len(item) < 500:
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
        
        # 如果没找到足够的结果，尝试备用解析
        if stances.count('△') == len(stances):
            # 查找符号后跟数字
            for i in range(1, num_viewpoints + 1):
                if f"✅" in response and f"{i}" in response:
                    stances[i-1] = '✅'
                elif f"❌" in response and f"{i}" in response:
                    stances[i-1] = '❌'
        
        return stances