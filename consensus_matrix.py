"""
智能共识矩阵计算模块 - 最终版本
观点自动总结简化 + 上下文联系分析 + 准确态度识别
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ConsensusMatrix:
    """智能共识矩阵计算器 - 最终版本"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_viewpoints_step1(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[str]]:
        """提取并简化观点"""
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
            
            print(f"\n📊 [观点提取并简化] 消息: {message_count}")
            
            # 第一步：提取完整观点
            prompt_extract = f"""Extract all MAIN viewpoints from this discussion.

Discussion:
{discussion_text}

List all distinct viewpoints. For each, include the original quote or paraphrase.

FORMAT:
1. viewpoint 1
2. viewpoint 2"""
            
            response = generate_response(llm_mode, prompt_extract, group_id="system", user="System")
            
            if not response:
                return None
            
            raw_viewpoints = self._parse_numbered_list(response)
            
            # 第二步：AI 总结简化观点
            print(f"   提取 {len(raw_viewpoints)} 个原始观点")
            print(f"   总结简化中...")
            
            simplified_viewpoints = self._summarize_viewpoints(raw_viewpoints, llm_mode)
            
            # 限制数量
            if message_count == 1:
                simplified_viewpoints = simplified_viewpoints[:1]
            elif message_count <= 2:
                simplified_viewpoints = simplified_viewpoints[:2]
            elif message_count <= 4:
                simplified_viewpoints = simplified_viewpoints[:3]
            else:
                simplified_viewpoints = simplified_viewpoints[:5]
            
            print(f"   ✓ 最终 {len(simplified_viewpoints)} 个简化观点\n")
            
            return simplified_viewpoints if simplified_viewpoints else None
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _summarize_viewpoints(self, raw_viewpoints: List[str], llm_mode: str) -> List[str]:
        """AI 总结简化观点 - 5-15 字"""
        from ai_agent import generate_response
        
        if not raw_viewpoints:
            return []
        
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(raw_viewpoints)])
        
        prompt = f"""Summarize each viewpoint concisely for a table display.

Original viewpoints:
{viewpoints_str}

RULES:
- Each summary: 5-15 characters maximum (very concise)
- Keep the core meaning
- Use simple words
- Make it readable in a table cell

FORMAT - numbered list:
1. [concise summary]
2. [concise summary]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return self._auto_summarize_simple(raw_viewpoints)
        
        summarized = self._parse_numbered_list(response)
        
        # 如果AI总结失败，使用简单切割
        if not summarized:
            return self._auto_summarize_simple(raw_viewpoints)
        
        # 确保总结足够短
        result = []
        for summary in summarized:
            # 如果太长，自动切割
            if len(summary) > 20:
                summary = summary[:17] + "..."
            result.append(summary)
        
        return result
    
    def _auto_summarize_simple(self, viewpoints: List[str]) -> List[str]:
        """自动简单总结 - 备用方案"""
        result = []
        for vp in viewpoints:
            # 取第一句或前20个字
            sentences = vp.split('。')
            first_sentence = sentences[0].strip()
            
            if len(first_sentence) > 20:
                summary = first_sentence[:17] + "..."
            else:
                summary = first_sentence
            
            result.append(summary)
        
        return result
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
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
        """分析态度 - 上下文联系版本"""
        try:
            print(f"\n📊 [态度分析] {len(participants)} 人 × {len(viewpoints)} 观点\n")
            
            stances_dict = {p: {} for p in participants}
            
            # 构建完整讨论上下文（保留所有消息）
            full_discussion = "\n".join([
                f"[{m.get('user')}]: {m.get('message', '')}"
                for m in messages
            ])
            
            if len(full_discussion) > 4000:
                full_discussion = full_discussion[:4000]
            
            # 为每个参与者分析
            for participant in participants:
                print(f"👤 {participant}")
                
                stances_dict[participant] = self._analyze_participant_with_context(
                    participant,
                    messages,
                    viewpoints,
                    full_discussion,
                    llm_mode
                )
                
                print()
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_participant_with_context(
        self,
        participant: str,
        messages: List[Dict],
        viewpoints: List[str],
        full_discussion: str,
        llm_mode: str
    ) -> Dict[str, str]:
        """分析参与者 - 使用完整上下文"""
        from ai_agent import generate_response
        
        # 获取该参与者的所有消息
        participant_msgs = [
            m.get('message', '')
            for m in messages
            if m.get('user') == participant
        ]
        
        if not participant_msgs:
            print(f"   (未发言) → 所有观点 △\n")
            return {vp: '△' for vp in viewpoints}
        
        # 构建参与者的发言记录（包含顺序）
        participant_history = []
        for msg in messages:
            if msg.get('user') == participant:
                participant_history.append(msg.get('message', ''))
        
        participant_text = "\n".join(participant_history)
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        # 高级提示词：联系上下文
        prompt = f"""Analyze {participant}'s stance on each viewpoint using full discussion context.

COMPLETE DISCUSSION CONTEXT:
{full_discussion}

VIEWPOINTS TO EVALUATE:
{viewpoints_str}

{participant}'s STATEMENTS (in order):
{participant_text}

ANALYSIS RULES:
1. Consider the FULL conversation flow, not just {participant}'s direct statements
2. Look for implicit support/opposition through:
   - Examples or counterexamples given
   - Questions or challenges raised
   - Agreements or disagreements with others
   - Conditional statements ("if...then...")
3. Special cases:
   - If {participant} says "I agree" → ✅
   - If {participant} says "I disagree" → ❌  
   - If {participant} adds to/expands idea → ✅
   - If {participant} raises concerns → △ (conditional)

OUTPUT: For EACH viewpoint, output the number and ONLY ONE symbol:

1:✅
2:△
3:❌
...

RULES FOR OUTPUT:
- One entry per line
- Format: number:symbol
- ONLY symbols: ✅ ❌ △
- NO other text"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return {vp: '△' for vp in viewpoints}
        
        # 解析响应
        stances = self._parse_stance_response_robust(response, len(viewpoints))
        
        result = {}
        for idx, stance in enumerate(stances):
            if idx < len(viewpoints):
                result[viewpoints[idx]] = stance
                emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                print(f"   {viewpoints[idx][:20]}... → {emoji}")
        
        return result
    
    def _parse_stance_response_robust(self, response: str, num_viewpoints: int) -> List[str]:
        """稳健的态度解析"""
        stances = ['△'] * num_viewpoints
        
        # 方法 1: 查找 "N:符号" 模式
        matches = re.finditer(r'(\d+)\s*:\s*([✅❌△])', response)
        for match in matches:
            try:
                idx = int(match.group(1)) - 1
                stance = match.group(2)
                if 0 <= idx < num_viewpoints:
                    stances[idx] = stance
            except:
                pass
        
        # 方法 2: 如果仍未解析，查找行中的符号
        if all(s == '△' for s in stances):
            for line in response.split('\n'):
                line = line.strip()
                # 检查是否有 "N" 开头的行
                num_match = re.match(r'^(\d+)', line)
                if num_match:
                    idx = int(num_match.group(1)) - 1
                    if 0 <= idx < num_viewpoints:
                        if '✅' in line:
                            stances[idx] = '✅'
                        elif '❌' in line:
                            stances[idx] = '❌'
                        elif '△' in line:
                            stances[idx] = '△'
        
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