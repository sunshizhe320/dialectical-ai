"""
共识矩阵 - AI 智能版本
根据实际讨论内容动态提取观点数量
"""

import json
import re
import requests
import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

MOONSHOT_KEY = None
try:
    if hasattr(st, 'secrets') and 'MOONSHOT_API_KEY' in st.secrets:
        MOONSHOT_KEY = st.secrets['MOONSHOT_API_KEY']
except:
    pass

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")


class ConsensusMatrix:
    """共识矩阵 - AI 智能版本"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
    
    def _call_moonshot(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """调用 Moonshot API"""
        if not self.api_key:
            print("❌ API Key not found")
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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 3000
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
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
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[List[Tuple[str, str]]]:
        """
        AI 提取观点 - 根据实际讨论内容动态决定数量
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 AI extracting viewpoints from {len(user_messages)} messages...")
            
            discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion) > 3000:
                discussion = discussion[:3000]
            
            # AI 动态提取观点 - 不限制数量
            prompt = f"""Analyze this discussion and extract ALL distinct viewpoints/arguments mentioned.

DISCUSSION:
{discussion}

Extract every unique viewpoint, perspective, or argument that participants mentioned.
Do NOT limit to any specific number - extract as many as exist in the discussion.

For EACH viewpoint:
1. Provide the COMPLETE viewpoint (1-2 sentences)
2. Provide a SIMPLIFIED version (8-15 characters)

Output format EXACTLY:
Viewpoint 1: [complete viewpoint]
Simplified: [8-15 chars]

Viewpoint 2: [complete viewpoint]
Simplified: [8-15 chars]

Viewpoint 3: ...
(continue for ALL viewpoints found)

Rules:
- Extract EVERY distinct viewpoint, not just the main ones
- Be thorough and comprehensive
- No duplicates
- Different perspectives only
- Maintain the original meaning"""
            
            response = self._call_moonshot(
                prompt,
                "You are an expert at comprehensive discussion analysis. Extract ALL viewpoints exhaustively."
            )
            
            if not response or len(response) < 30:
                print("❌ API response too short")
                return None
            
            result = self._parse_viewpoints(response)
            
            if result:
                print(f"✓ Extracted {len(result)} viewpoints:")
                for i, (full, simp) in enumerate(result, 1):
                    print(f"  {i}. [{simp}]")
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
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """
        AI 智能分析每个参与者对每个观点的态度
        """
        try:
            print(f"\n📈 AI analyzing stances for {len(participants)} participants and {len(viewpoints_pairs)} viewpoints...")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取发言者
            speaker_messages = {}
            for m in messages:
                user = m.get('user')
                if user and user != 'AI':
                    if user not in speaker_messages:
                        speaker_messages[user] = []
                    speaker_messages[user].append(m.get('message', ''))
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            # 构建完整讨论
            discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in messages
                if m.get('user') != 'AI'
            ])
            
            if len(discussion) > 4000:
                discussion = discussion[:4000]
            
            viewpoints_text = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
            
            # 批量分析所有参与者
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_text = "\n".join(speaker_messages[participant])
                
                # AI 分析该参与者的立场
                prompt = f"""You are an expert at understanding people's viewpoints and stances in discussions.

Analyze {participant}'s stance on EACH viewpoint based ONLY on what they actually said.

FULL DISCUSSION:
{discussion}

VIEWPOINTS TO ANALYZE (numbered 1 to {len(full_viewpoints)}):
{viewpoints_text}

{participant}'s ACTUAL STATEMENTS:
{participant_text}

---

For EACH viewpoint number (1, 2, 3, 4... up to {len(full_viewpoints)}):
Determine if {participant}:
- ✅ SUPPORTS / AGREES / ENDORSES / ADVOCATES for this viewpoint
- ❌ OPPOSES / DISAGREES / CRITICIZES / ARGUES AGAINST this viewpoint
- △ NEUTRAL / BALANCED / NOT MENTIONED (either hasn't mentioned it, or gives both pros and cons)

INSTRUCTIONS:
1. Go through each numbered viewpoint
2. Check if {participant} mentioned or addressed it
3. If YES → decide: support (✅) or oppose (❌)
4. If NO or BALANCED → neutral (△)
5. Base ONLY on actual statements, not assumptions

Output ONLY symbols, one per line, in order:
1. ✅
2. ❌
3. △
4. ✅
...
(one line per viewpoint, ONLY the symbol)"""
                
                response = self._call_moonshot(
                    prompt,
                    "Analyze participant stances based on actual statements only."
                )
                
                if response:
                    stances = self._parse_stances(response, len(full_viewpoints))
                    
                    for idx, stance in enumerate(stances):
                        if idx < len(simplified_viewpoints):
                            stances_dict[participant][simplified_viewpoints[idx]] = stance
                    
                    print(" ".join(stances))
                else:
                    print("⚠️ AI failed")
                    for sv in simplified_viewpoints:
                        stances_dict[participant][sv] = '△'
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints(self, text: str) -> List[Tuple[str, str]]:
        """解析 AI 返回的观点 - 支持任意数量"""
        result = []
        lines = text.split('\n')
        i = 0
        
        viewpoint_num = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line and re.match(r'^[Vv]iewpoint\s+\d+\s*[:：]', line):
                viewpoint_num += 1
                full = re.sub(r'^[Vv]iewpoint\s+\d+\s*[:：]\s*', '', line).strip()
                
                # 查找下一行的 Simplified
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^[Ss]implified\s*[:：]', next_line):
                        simp = re.sub(r'^[Ss]implified\s*[:：]\s*', '', next_line).strip()
                        
                        if 5 <= len(full) <= 500 and 5 <= len(simp) <= 30:
                            result.append((full, simp))
                            print(f"    ✓ Parsed viewpoint {viewpoint_num}")
                        
                        i += 2
                        continue
            
            i += 1
        
        print(f"  Total viewpoints parsed: {len(result)}")
        return result
    
    def _parse_stances(self, response: str, num: int) -> List[str]:
        """解析 AI 返回的态度符号 - 支持任意数量"""
        stances = ['△'] * num
        
        # 找所有符号
        symbols = re.findall(r'[✅❌△]', response)
        
        # 配对到对应的观点
        for i, symbol in enumerate(symbols[:num]):
            stances[i] = symbol
        
        return stances