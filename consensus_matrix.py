"""
共识矩阵 - 增强的 AI 智能版本
更好的观点提取和态度分析
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
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 2000:
                discussion_text = discussion_text[:2000]
            
            print(f"\n📊 Extracting viewpoints from {len(user_messages)} messages...")
            print(f"Discussion length: {len(discussion_text)} chars")
            
            # 第一次尝试：提取观点
            prompt = f"""Extract 2-5 main viewpoints/arguments from this discussion.

DISCUSSION:
{discussion_text}

List each viewpoint clearly, numbered 1-5. One complete viewpoint per line.
Example format:
1. Remote work saves commute time
2. Work-life balance improves with remote options
3. Team collaboration is harder remotely

Extract REAL viewpoints only - no "I don't know" or filler."""
            
            response = generate_response(
                llm_mode, 
                prompt, 
                group_id="system", 
                user="System"
            )
            
            print(f"AI Response:\n{response}\n")
            
            if not response or len(response) < 10:
                print("❌ Empty response from AI")
                return None
            
            # 解析多种格式
            full_viewpoints = self._parse_viewpoints_smart(response)
            
            if not full_viewpoints:
                print("❌ No viewpoints parsed")
                return None
            
            print(f"✓ Extracted {len(full_viewpoints)} viewpoints:")
            for i, vp in enumerate(full_viewpoints, 1):
                print(f"  {i}. {vp}")
            
            # 第二步：简化观点
            viewpoints_str = "\n".join([f"{i}. {vp}" for i, vp in enumerate(full_viewpoints, 1)])
            
            prompt_simplify = f"""Simplify each viewpoint to 8-15 Chinese characters. Keep the core meaning.

VIEWPOINTS:
{viewpoints_str}

Return ONLY a numbered list like this:
1. 核心观点简化版
2. 另一个观点
etc.

Be concise. 8-15 characters each."""
            
            response = generate_response(
                llm_mode, 
                prompt_simplify, 
                group_id="system", 
                user="System"
            )
            
            print(f"Simplification Response:\n{response}\n")
            
            simplified_viewpoints = self._parse_viewpoints_smart(response) if response else []
            
            # 配对完整和简化版本
            result = []
            for i, full in enumerate(full_viewpoints):
                if i < len(simplified_viewpoints):
                    simplified = simplified_viewpoints[i]
                else:
                    # 自动简化（如果 AI 没有提供）
                    simplified = self._auto_simplify(full)
                
                # 确保不超过 20 字
                if len(simplified) > 20:
                    simplified = simplified[:17] + "…"
                
                result.append((full, simplified))
            
            print(f"✓ Final viewpoints:")
            for i, (full, simp) in enumerate(result, 1):
                print(f"  {i}. [{simp}]")
            
            return result if result else None
        
        except Exception as e:
            print(f"❌ Error in extract_and_simplify: {e}")
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
                f"{m.get('user')}: {m.get('message', '')}"
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
                viewpoints_str = "\n".join([f"{i}. {full_viewpoints[i]}" for i in range(len(full_viewpoints))])
                
                prompt = f"""Analyze {participant}'s stance on each viewpoint.

DISCUSSION:
{full_discussion}

VIEWPOINTS:
{viewpoints_str}

{participant}'s MESSAGES:
{participant_text}

For each viewpoint, does {participant} SUPPORT (✅), OPPOSE (❌), or is NEUTRAL (△)?

Return as a list like:
1. ✅
2. ❌
3. △
etc.

Answer each line with ONLY the number and symbol."""
                
                response = generate_response(
                    llm_mode, 
                    prompt, 
                    group_id="system", 
                    user="System"
                )
                
                print(f"Response: {response}")
                
                stances = self._parse_stances_smart(response, len(full_viewpoints))
                
                for idx, stance in enumerate(stances):
                    if idx < len(simplified_viewpoints):
                        stances_dict[participant][simplified_viewpoints[idx]] = stance
                
                # 显示结果
                results = [f"{i+1}:{s}" for i, s in enumerate(stances)]
                print(" | ".join(results))
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error in analyze_stances: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints_smart(self, text: str) -> List[str]:
        """智能解析各种格式的观点列表"""
        if not text:
            return []
        
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # 匹配多种格式
            # 格式1: "1. 观点"
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 3 <= len(item) <= 500:
                    items.append(item)
                continue
            
            # 格式2: "- 观点"
            match = re.match(r'^[-•*]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 3 <= len(item) <= 500:
                    items.append(item)
                continue
            
            # 格式3: 纯文本（如果前面没有列表，可能整行就是观点）
            if len(line) > 10 and line[0].isalpha():
                items.append(line)
        
        return items[:5]  # 最多 5 个观点
    
    def _parse_stances_smart(self, response: str, num_viewpoints: int) -> List[str]:
        """智能解析态度"""
        stances = ['△'] * num_viewpoints
        
        if not response:
            return stances
        
        # 方法1: 查找 "数字. 符号" 或 "数字) 符号"
        matches = re.finditer(r'(\d+)[\.\)]\s*([✅❌△])', response)
        found_count = 0
        for match in matches:
            try:
                idx = int(match.group(1)) - 1
                stance = match.group(2)
                if 0 <= idx < num_viewpoints:
                    stances[idx] = stance
                    found_count += 1
            except:
                pass
        
        if found_count > 0:
            return stances
        
        # 方法2: 行按行查找符号
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if i >= num_viewpoints:
                break
            
            if '✅' in line:
                stances[i] = '✅'
            elif '❌' in line:
                stances[i] = '❌'
            elif '△' in line:
                stances[i] = '△'
        
        return stances
    
    def _auto_simplify(self, text: str) -> str:
        """自动简化文本到 8-15 字"""
        # 提取关键词
        words = text.split()
        
        # 简单的启发式方法
        key_phrases = []
        for word in words:
            if len(word) > 2 and word not in ['the', 'and', 'or', 'can', 'is', 'are']:
                key_phrases.append(word)
        
        # 组合成 8-15 字
        result = ' '.join(key_phrases[:3])
        if len(result) > 20:
            result = result[:17] + "…"
        elif len(result) < 5:
            result = text[:15]
        
        return result