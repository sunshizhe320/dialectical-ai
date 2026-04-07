"""
共识矩阵 - Moonshot API 版本（带诊断）
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
        print(f"✅ Loaded from Streamlit Secrets")
except:
    pass

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    if MOONSHOT_KEY:
        print(f"✅ Loaded from environment")

print(f"🔑 API Key ready: {bool(MOONSHOT_KEY)}")


class ConsensusMatrix:
    """共识矩阵 - Moonshot API"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
    
    def _call_moonshot(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """调用 Moonshot API"""
        if not self.api_key:
            print("❌ API Key not found!")
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
                "max_tokens": 2000
            }
            
            print(f"[📤 POST to Moonshot API]")
            print(f"  System prompt length: {len(system_prompt)}")
            print(f"  User prompt length: {len(prompt)}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            print(f"[📥 Response received]")
            print(f"  Status code: {response.status_code}")
            print(f"  Response length: {len(response.text)} chars")
            
            if response.status_code != 200:
                print(f"[❌ HTTP {response.status_code}]")
                print(f"  Response: {response.text[:300]}")
                return None
            
            # 解析 JSON
            try:
                result = response.json()
                print(f"[✅ JSON parsed]")
            except json.JSONDecodeError as e:
                print(f"[❌ JSON parse error: {e}]")
                print(f"  Response text: {response.text[:200]}")
                return None
            
            # 检查结构
            if "choices" not in result:
                print(f"[❌ No 'choices' in response]")
                print(f"  Keys: {list(result.keys())}")
                return None
            
            if len(result["choices"]) == 0:
                print(f"[❌ Choices is empty]")
                return None
            
            choice = result["choices"][0]
            if "message" not in choice:
                print(f"[❌ No 'message' in choice]")
                print(f"  Choice keys: {list(choice.keys())}")
                return None
            
            content = choice["message"].get("content", "").strip()
            
            if not content:
                print(f"[❌ Content is empty]")
                return None
            
            print(f"[✅ Got {len(content)} chars content]")
            print(f"  Preview: {content[:100]}...")
            
            return content
        
        except requests.Timeout:
            print(f"[❌ Request timeout]")
        except requests.ConnectionError:
            print(f"[❌ Connection error]")
        except Exception as e:
            print(f"[❌ Exception: {type(e).__name__}: {e}]")
            import traceback
            traceback.print_exc()
        
        return None
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[List[Tuple[str, str]]]:
        """提取观点"""
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                print("❌ No user messages")
                return None
            
            print(f"\n📊 Extract viewpoints from {len(user_messages)} messages")
            
            discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion) > 2000:
                discussion = discussion[:2000]
            
            print(f"  Discussion length: {len(discussion)} chars")
            
            prompt = f"""Extract 2-4 core viewpoints from this discussion.

DISCUSSION:
{discussion}

For each viewpoint, provide:
1. Complete viewpoint (1-2 sentences)
2. Simplified version (8-15 characters)

Output format:
Viewpoint 1: [complete]
Simplified: [8-15 chars]

Viewpoint 2: [complete]
Simplified: [8-15 chars]

Important:
- Extract REAL viewpoints only
- Be complete and clear
- 8-15 characters for simplified version
- No duplicates"""
            
            response = self._call_moonshot(
                prompt,
                "You are an expert discussion analyst. Extract viewpoints accurately."
            )
            
            if not response:
                print("❌ API returned None")
                return None
            
            print(f"\n[Parsing response]")
            result = self._parse_viewpoints(response)
            
            print(f"  Parsed {len(result)} viewpoints")
            if not result:
                print("❌ No viewpoints parsed from response")
                print(f"  Full response:\n{response}")
                return None
            
            for i, (full, simp) in enumerate(result, 1):
                print(f"  {i}. [{simp}] = {full[:40]}...")
            
            return result
        
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
        """分析态度"""
        try:
            print(f"\n📈 Analyze stances")
            
            stances_dict = {p: {} for p in participants}
            
            speaker_messages = {}
            for m in messages:
                user = m.get('user')
                if user and user != 'AI':
                    if user not in speaker_messages:
                        speaker_messages[user] = []
                    speaker_messages[user].append(m.get('message', ''))
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            print(f"  Viewpoints: {len(full_viewpoints)}")
            print(f"  Participants: {len(participants)}")
            
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_text = "\n".join(speaker_messages[participant])
                viewpoints_text = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
                
                prompt = f"""Analyze {participant}'s stance.

VIEWPOINTS:
{viewpoints_text}

{participant}'s STATEMENTS:
{participant_text}

Output ONLY symbols:
1. ✅
2. ❌
3. △"""
                
                response = self._call_moonshot(prompt, "Output ONLY numbered symbols.")
                
                if response:
                    stances = self._parse_stances(response, len(full_viewpoints))
                    for idx, stance in enumerate(stances):
                        if idx < len(simplified_viewpoints):
                            stances_dict[participant][simplified_viewpoints[idx]] = stance
                    print(" ".join(stances))
                else:
                    print("❌")
                    for sv in simplified_viewpoints:
                        stances_dict[participant][sv] = '△'
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints(self, text: str) -> List[Tuple[str, str]]:
        """解析观点"""
        result = []
        lines = text.split('\n')
        
        print(f"  Total lines: {len(lines)}")
        
        i = 0
        viewpoint_count = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # 查找 "Viewpoint N:" 或 "Viewpoint N ："
            if re.match(r'^[Vv]iewpoint\s+\d+\s*[:：]', line):
                viewpoint_count += 1
                print(f"  Found Viewpoint {viewpoint_count} at line {i}: {line[:50]}...")
                
                full = re.sub(r'^[Vv]iewpoint\s+\d+\s*[:：]\s*', '', line).strip()
                
                # 查找下一行的 Simplified
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    if re.match(r'^[Ss]implified\s*[:：]', next_line):
                        simp = re.sub(r'^[Ss]implified\s*[:：]\s*', '', next_line).strip()
                        
                        print(f"    Full: {full[:40]}...")
                        print(f"    Simplified: {simp}")
                        
                        if 5 <= len(full) <= 500 and 5 <= len(simp) <= 30:
                            result.append((full, simp))
                            print(f"    ✓ Added")
                        else:
                            print(f"    ✗ Length check failed (full={len(full)}, simp={len(simp)})")
                        
                        i += 2
                        continue
                
                i += 1
            else:
                i += 1
        
        print(f"  Final result: {len(result)} viewpoints parsed")
        return result
    
    def _parse_stances(self, response: str, num: int) -> List[str]:
        """解析态度"""
        stances = ['△'] * num
        symbols = re.findall(r'[✅❌△]', response)
        
        print(f"    Found {len(symbols)} symbols in response")
        
        for i, symbol in enumerate(symbols[:num]):
            stances[i] = symbol
        
        return stances