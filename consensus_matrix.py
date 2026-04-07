"""
共识矩阵 - 精确版本
基于实际发言内容分析态度
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
        提取观点 - 保留完整表达
        返回: [(完整观点, 完整观点), ...]
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
            
            if len(discussion_text) > 2500:
                discussion_text = discussion_text[:2500]
            
            print(f"\n📊 Extracting viewpoints from {len(user_messages)} messages...")
            
            # 提取观点
            prompt = f"""Extract 2-5 distinct viewpoints/arguments mentioned in this discussion.

DISCUSSION:
{discussion_text}

TASK: Identify the main viewpoints or arguments. Express each viewpoint COMPLETELY and CLEARLY.

OUTPUT FORMAT:
1. [Complete viewpoint with full context]
2. [Another complete viewpoint]
3. [etc]

RULES:
- Extract REAL viewpoints only
- Express each viewpoint FULLY and CLEARLY (not abbreviated)
- Different perspectives/arguments only
- Keep original meaning
- Each viewpoint can be 1-3 sentences"""
            
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
            
            # 解析观点
            full_viewpoints = self._parse_viewpoints_smart(response)
            
            if not full_viewpoints:
                print("❌ No viewpoints parsed")
                return None
            
            print(f"✓ Extracted {len(full_viewpoints)} viewpoints:")
            for i, vp in enumerate(full_viewpoints, 1):
                print(f"  {i}. {vp[:60]}...")
            
            # 返回 (完整, 完整) 对
            result = [(vp, vp) for vp in full_viewpoints]
            
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
        精确分析态度 - 基于每个参与者的实际发言
        返回: {参与者: {观点: '✅/❌/△'}}
        """
        try:
            from ai_agent import generate_response
            
            print(f"\n📈 Analyzing stances for {len(participants)} participants...")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取发言者及其消息
            speaker_messages = {}
            for m in messages:
                user = m.get('user')
                if user and user != 'AI':
                    if user not in speaker_messages:
                        speaker_messages[user] = []
                    speaker_messages[user].append(m.get('message', ''))
            
            viewpoints = [vp[0] for vp in viewpoints_pairs]
            
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                # 未发言 → 全部中立
                if participant not in speaker_messages:
                    print("(not spoken) → all △")
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                    continue
                
                participant_msgs = speaker_messages[participant]
                participant_text = "\n".join(participant_msgs)
                
                # 对每个观点分别分析
                for idx, viewpoint in enumerate(viewpoints):
                    # 更精确的提示词
                    prompt = f"""Based on {participant}'s actual statements, determine their stance on this viewpoint.

VIEWPOINT TO ANALYZE:
"{viewpoint}"

{participant}'s ACTUAL STATEMENTS:
{participant_text}

IMPORTANT: Look at the EXACT WORDS and STATEMENTS {participant} made.

Does {participant}'s statements indicate:
1. ✅ SUPPORT or AGREE with this viewpoint? (They explicitly support it, give examples supporting it, or argue in favor of it)
2. ❌ OPPOSE or DISAGREE with this viewpoint? (They explicitly oppose it, give counterarguments, or argue against it)
3. △ NEUTRAL or NOT MENTIONED? (They don't mention this viewpoint, or are ambiguous/balanced)

Respond with ONLY the symbol and a brief reason:
✅ [brief reason]
or
❌ [brief reason]
or
△ [brief reason]"""
                    
                    response = generate_response(
                        llm_mode, 
                        prompt, 
                        group_id="system", 
                        user="System"
                    )
                    
                    # 精确解析
                    stance = self._extract_stance_from_response(response, participant_text, viewpoint)
                    stances_dict[participant][viewpoint] = stance
                    print(stance, end="")
                
                print()
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error in analyze_stances: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints_smart(self, text: str) -> List[str]:
        """智能解析观点列表"""
        if not text:
            return []
        
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # 匹配 "1. 观点" 格式
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 5 <= len(item) <= 1000:
                    items.append(item)
                continue
            
            # 匹配 "- 观点" 格式
            match = re.match(r'^[-•*]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 5 <= len(item) <= 1000:
                    items.append(item)
                continue
        
        return items[:5]
    
    def _extract_stance_from_response(self, response: str, participant_text: str, viewpoint: str) -> str:
        """从 AI 响应中精确提取态度"""
        if not response:
            return '△'
        
        # 第一优先级：查找符号在响应开头
        if response.startswith('✅'):
            return '✅'
        elif response.startswith('❌'):
            return '❌'
        elif response.startswith('△'):
            return '△'
        
        # 第二优先级：查找 "✅/❌/△" 符号
        if '✅' in response:
            # 检查是否在前半部分
            if response.index('✅') < len(response) / 2:
                return '✅'
        
        if '❌' in response:
            if response.index('❌') < len(response) / 2:
                return '❌'
        
        if '△' in response:
            if response.index('△') < len(response) / 2:
                return '△'
        
        # 第三优先级：查找关键词（中英文）
        support_keywords = ['support', 'agree', 'favor', 'positive', 'good', '支持', '赞同', '同意', '赞成', '好的', '同意这', '很好', '应该', '肯定']
        oppose_keywords = ['oppose', 'disagree', 'against', 'negative', 'bad', '反对', '不同意', '否定', '反对这', '不好', '不应该', '不赞成', '错误']
        
        response_lower = response.lower()
        
        support_count = sum(1 for kw in support_keywords if kw in response_lower or kw in participant_text.lower())
        oppose_count = sum(1 for kw in oppose_keywords if kw in response_lower or kw in participant_text.lower())
        
        if support_count > oppose_count and support_count > 0:
            return '✅'
        elif oppose_count > support_count and oppose_count > 0:
            return '❌'
        else:
            return '△'