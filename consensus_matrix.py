"""
共识矩阵 - 可靠版本
包含备用方案和多种格式支持
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
        提取观点 - 带备用方案
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
            
            # 尝试 AI 提取
            try:
                prompt = f"""Extract the main viewpoints/arguments in this discussion.

DISCUSSION:
{discussion_text}

Extract 2-5 viewpoints. Format:
1. Viewpoint 1
2. Viewpoint 2
etc.

Be clear and complete."""
                
                response = generate_response(
                    llm_mode, 
                    prompt, 
                    group_id="system", 
                    user="System",
                    timeout=10
                )
                
                print(f"AI Response:\n{response[:200]}...")
                
                if response and len(response) > 20:
                    viewpoints = self._parse_viewpoints_smart(response)
                    if viewpoints and len(viewpoints) >= 2:
                        print(f"✓ AI extracted {len(viewpoints)} viewpoints")
                        result = [(vp, vp) for vp in viewpoints]
                        return result
                
            except Exception as e:
                print(f"⚠️ AI extraction failed: {e}")
            
            # 备用方案：启发式提取
            print("📌 Using fallback heuristic extraction...")
            viewpoints = self._heuristic_extract_viewpoints(user_messages)
            
            if viewpoints and len(viewpoints) >= 1:
                print(f"✓ Fallback extracted {len(viewpoints)} viewpoints")
                result = [(vp, vp) for vp in viewpoints]
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ Error: {e}")
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
        分析态度 - 带备用方案
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
                    print("△ (not spoken)")
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                    continue
                
                participant_msgs = speaker_messages[participant]
                participant_text = "\n".join(participant_msgs)
                
                # 对每个观点分别分析
                for idx, viewpoint in enumerate(viewpoints):
                    try:
                        prompt = f"""Analyze {participant}'s stance on this viewpoint.

VIEWPOINT: "{viewpoint}"

{participant}'s STATEMENTS: {participant_text}

Does {participant} SUPPORT (✅), OPPOSE (❌), or is NEUTRAL (△)?
Answer with ONLY: ✅ or ❌ or △"""
                        
                        response = generate_response(
                            llm_mode, 
                            prompt, 
                            group_id="system", 
                            user="System",
                            timeout=5
                        )
                        
                        stance = self._extract_stance_from_response(
                            response, 
                            participant_text, 
                            viewpoint
                        )
                    except:
                        # 备用：启发式判断
                        stance = self._heuristic_analyze_stance(
                            participant_text, 
                            viewpoint
                        )
                    
                    stances_dict[participant][viewpoint] = stance
                    print(stance, end="")
                
                print()
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints_smart(self, text: str) -> List[str]:
        """智能解析观点"""
        if not text:
            return []
        
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # 格式1: "1. 观点"
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 5 <= len(item) <= 1000:
                    items.append(item)
                continue
            
            # 格式2: "- 观点"
            match = re.match(r'^[-•*]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 5 <= len(item) <= 1000:
                    items.append(item)
                continue
        
        return items[:5]
    
    def _heuristic_extract_viewpoints(self, messages: List[Dict]) -> List[str]:
        """启发式提取观点（备用方案）"""
        viewpoints = []
        
        # 直接使用消息作为观点
        for msg in messages:
            text = msg.get('message', '').strip()
            if len(text) > 20 and len(text) < 500:
                viewpoints.append(text)
        
        # 去重并限制
        viewpoints = list(dict.fromkeys(viewpoints))[:5]
        
        return viewpoints
    
    def _extract_stance_from_response(
        self, 
        response: str, 
        participant_text: str, 
        viewpoint: str
    ) -> str:
        """精确提取态度"""
        if not response:
            return '△'
        
        # 优先查找符号
        if response.startswith('✅') or response.startswith('Support'):
            return '✅'
        elif response.startswith('❌') or response.startswith('Oppose'):
            return '❌'
        elif response.startswith('△') or response.startswith('Neutral'):
            return '△'
        
        # 查找符号在响应中
        if '✅' in response and response.index('✅') < len(response) / 2:
            return '✅'
        if '❌' in response and response.index('❌') < len(response) / 2:
            return '❌'
        if '△' in response:
            return '△'
        
        # 关键词匹配
        response_lower = response.lower() + participant_text.lower()
        
        support_words = ['support', 'agree', 'yes', 'good', 'favor', '支持', '同意', '赞成', '好', '是的']
        oppose_words = ['oppose', 'disagree', 'no', 'bad', 'against', '反对', '不同意', '不赞成', '不', '错']
        
        support_count = sum(response_lower.count(w) for w in support_words)
        oppose_count = sum(response_lower.count(w) for w in oppose_words)
        
        if support_count > oppose_count > 0:
            return '✅'
        elif oppose_count > support_count > 0:
            return '❌'
        else:
            return '△'
    
    def _heuristic_analyze_stance(self, participant_text: str, viewpoint: str) -> str:
        """启发式分析态度（备用方案）"""
        text = (participant_text + " " + viewpoint).lower()
        
        support_words = ['support', 'agree', 'yes', 'good', '支持', '同意', '赞成', '好']
        oppose_words = ['oppose', 'disagree', 'no', 'bad', '反对', '不同意', '不赞成']
        
        support_count = sum(text.count(w) for w in support_words)
        oppose_count = sum(text.count(w) for w in oppose_words)
        
        if support_count > oppose_count > 0:
            return '✅'
        elif oppose_count > support_count > 0:
            return '❌'
        else:
            return '△'