"""
共识矩阵 - 修复版本
正确解析观点和显示表格
"""

import json
import re
import requests
import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# 获取 API KEY
MOONSHOT_KEY = None
try:
    if hasattr(st, 'secrets') and st.secrets:
        MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY")
except:
    pass

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")

print(f"✅ MOONSHOT_API_KEY ready: {bool(MOONSHOT_KEY)}")


class ConsensusMatrix:
    """共识矩阵计算器"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
    
    def _call_moonshot(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """直接调用 Moonshot API"""
        if not self.api_key:
            print("❌ MOONSHOT_API_KEY not found")
            return None
        
        try:
            url = "https://api.moonshot.cn/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "moonshot-v1-8k",
                "messages": [
                    {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            print(f"[📤 Calling Moonshot API...]")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"[📥 Status: {response.status_code}]")
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    print(f"[✅ Got {len(content)} chars]")
                    return content
            else:
                print(f"❌ API Error {response.status_code}")
        
        except Exception as e:
            print(f"❌ API Error: {e}")
        
        return None
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control"
    ) -> Optional[List[Tuple[str, str]]]:
        """
        提取观点 - 使用 Moonshot API
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 Extracting viewpoints from {len(user_messages)} messages...")
            
            # 构建讨论文本
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 2500:
                discussion_text = discussion_text[:2500]
            
            print(f"Discussion length: {len(discussion_text)} chars")
            
            # 提取观点 - 更精确的提示
            prompt = f"""Extract 2-5 main viewpoints from this discussion.

DISCUSSION:
{discussion_text}

Output ONLY a numbered list, one viewpoint per line:
1. Viewpoint about topic A
2. Viewpoint about topic B
3. Viewpoint about topic C

IMPORTANT: Start each line with number and period, then the viewpoint.
No other text before or after the list.
"""
            
            response = self._call_moonshot(
                prompt,
                "Extract viewpoints as a numbered list. Only output the list."
            )
            
            print(f"\n=== RAW RESPONSE ===")
            print(response)
            print(f"=== END RESPONSE ===\n")
            
            if response and len(response) > 10:
                viewpoints = self._parse_viewpoints_smart(response)
                print(f"Parsed viewpoints: {viewpoints}")
                
                if viewpoints and len(viewpoints) >= 1:
                    print(f"✓ Extracted {len(viewpoints)} viewpoints:")
                    for i, vp in enumerate(viewpoints, 1):
                        print(f"  {i}. {vp}")
                    
                    result = [(vp, vp) for vp in viewpoints]
                    return result
            
            # 备用方案
            print("📌 API response too short, using fallback...")
            viewpoints = self._heuristic_extract_viewpoints(user_messages)
            if viewpoints:
                print(f"✓ Fallback extracted {len(viewpoints)} viewpoints")
                result = [(vp, vp) for vp in viewpoints]
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ Extract Error: {e}")
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
        分析态度
        """
        try:
            print(f"\n📈 Analyzing stances for {len(participants)} participants...")
            print(f"Viewpoints to analyze: {len(viewpoints_pairs)}")
            
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
            
            # 完整讨论文本
            full_discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in messages
                if m.get('user') != 'AI'
            ])
            
            if len(full_discussion) > 3000:
                full_discussion = full_discussion[:3000]
            
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                # 未发言 → 全部中立
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {vp: '△' for vp in viewpoints}
                    continue
                
                participant_msgs = speaker_messages[participant]
                participant_text = "\n".join(participant_msgs)
                
                print(f"\n    Analyzing {len(viewpoints)} viewpoints...")
                
                # 对每个观点分别分析
                for idx, viewpoint in enumerate(viewpoints):
                    prompt = f"""Determine {participant}'s stance on this viewpoint based on their actual statements.

VIEWPOINT: {viewpoint}

{participant}'s STATEMENTS:
{participant_text}

Does {participant} SUPPORT (✅), OPPOSE (❌), or is NEUTRAL (△) about this viewpoint?

Respond with ONLY ONE symbol: ✅ or ❌ or △
No other text."""
                    
                    response = self._call_moonshot(
                        prompt,
                        "Analyze stance. Respond with ONLY one symbol: ✅ or ❌ or △"
                    )
                    
                    stance = self._extract_stance_symbol(response)
                    stances_dict[participant][viewpoint] = stance
                    print(f"    [{idx+1}/{len(viewpoints)}] {viewpoint[:30]}... → {stance}")
                
                print(f"  ✓ {participant}: {' '.join([stances_dict[participant][vp] for vp in viewpoints])}")
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Analyze Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints_smart(self, text: str) -> List[str]:
        """智能解析观点 - 改进版"""
        if not text:
            return []
        
        items = []
        lines = text.split('\n')
        
        print(f"[DEBUG] Parsing {len(lines)} lines")
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # 跳过空行
            if not line or len(line) < 5:
                continue
            
            print(f"  Line {line_num}: '{line[:60]}...'")
            
            # 匹配 "1. 观点" 或 "1) 观点" 格式
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                print(f"    ✓ Matched: '{item[:60]}...'")
                if 5 <= len(item) <= 1000:
                    items.append(item)
                continue
            
            # 如果以其他格式开头但看起来像观点
            if len(line) > 20 and not line.startswith('IMPORTANT'):
                # 可能是没有编号的观点
                if '.' not in line[:3]:  # 不是句子的一部分
                    print(f"    ~ Possible viewpoint (no number): '{line[:60]}...'")
        
        print(f"[DEBUG] Final items: {len(items)}")
        return items[:5]
    
    def _extract_stance_symbol(self, response: str) -> str:
        """从响应中提取态度符号"""
        if not response:
            return '△'
        
        # 查找第一个符号
        if '✅' in response:
            return '✅'
        if '❌' in response:
            return '❌'
        if '△' in response:
            return '△'
        
        # 根据关键词判断
        response_lower = response.lower()
        if 'support' in response_lower or 'agree' in response_lower or 'yes' in response_lower:
            return '✅'
        if 'oppose' in response_lower or 'disagree' in response_lower or 'no' in response_lower:
            return '❌'
        
        return '△'
    
    def _heuristic_extract_viewpoints(self, messages: List[Dict]) -> List[str]:
        """启发式提取观点（备用方案）"""
        viewpoints = []
        
        for msg in messages:
            text = msg.get('message', '').strip()
            if 15 < len(text) < 500:
                viewpoints.append(text)
        
        seen = set()
        unique = []
        for vp in viewpoints:
            if vp.lower() not in seen:
                seen.add(vp.lower())
                unique.append(vp)
        
        print(f"[Heuristic] Extracted {len(unique)} unique viewpoints")
        return unique[:5]