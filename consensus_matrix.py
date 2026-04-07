"""
共识矩阵 - 简化版本
让 AI 一次性完成所有分析
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
    """共识矩阵 - AI 完全处理"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
    
    def _call_moonshot(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """直接调用 Moonshot API"""
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
                "max_tokens": 2000
            }
            
            print(f"[📤 Calling Moonshot API...]")
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    print(f"[✅ Success]")
                    return content
            else:
                print(f"[❌ Error {response.status_code}]")
        except Exception as e:
            print(f"[❌ Exception: {e}]")
        
        return None
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[List[Tuple[str, str]]]:
        """
        提取观点 - AI 完全处理
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 Extracting viewpoints...")
            
            # 构建讨论文本
            discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion) > 2000:
                discussion = discussion[:2000]
            
            # 一次性完成：提取 + 简化
            prompt = f"""Analyze this discussion and extract 2-4 core viewpoints.

DISCUSSION:
{discussion}

For each viewpoint:
1. Provide the COMPLETE viewpoint (1-2 sentences)
2. Provide a SIMPLIFIED version (8-15 characters)

Output format EXACTLY as follows:
Viewpoint 1: [complete viewpoint]
Simplified: [simplified 8-15 chars]

Viewpoint 2: [complete viewpoint]
Simplified: [simplified 8-15 chars]

(continue for 2-4 viewpoints)

IMPORTANT:
- Extract REAL, DISTINCT viewpoints only
- No duplicates
- Simplified version must be 8-15 characters ONLY"""
            
            response = self._call_moonshot(
                prompt,
                "You are an expert discussion analyst. Extract and simplify viewpoints accurately."
            )
            
            if not response or len(response) < 30:
                print("❌ API response too short")
                return None
            
            print(f"[Response preview] {response[:150]}...")
            
            # 解析响应
            result = self._parse_viewpoints_with_simplified(response)
            
            if result and len(result) > 0:
                print(f"✓ Extracted {len(result)} viewpoints")
                for full, simp in result:
                    print(f"  [{simp}] → {full[:50]}...")
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
        分析态度 - AI 完全处理
        """
        try:
            print(f"\n📈 Analyzing stances...")
            
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
            
            if len(discussion) > 2500:
                discussion = discussion[:2500]
            
            viewpoints_text = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
            
            # 为所有参与者一次性分析
            participants_analysis = {}
            for participant in participants:
                if participant not in speaker_messages:
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_text = "\n".join(speaker_messages[participant])
                
                prompt = f"""Based on {participant}'s actual statements, analyze their stance on each viewpoint.

DISCUSSION CONTEXT:
{discussion}

VIEWPOINTS:
{viewpoints_text}

{participant}'s STATEMENTS:
{participant_text}

For EACH viewpoint, determine if {participant}:
✅ SUPPORTS/AGREES (based on their statements)
❌ OPPOSES/DISAGREES (based on their statements)
△ is NEUTRAL or hasn't MENTIONED it

Output ONLY this format:
1. ✅
2. ❌
3. △
(one symbol per line for each viewpoint)

IMPORTANT: Base analysis ONLY on {participant}'s actual statements."""
                
                response = self._call_moonshot(
                    prompt,
                    "Analyze participant stances based on their actual statements. Output ONLY symbols."
                )
                
                if response:
                    stances = self._parse_stance_symbols(response, len(full_viewpoints))
                    for idx, stance in enumerate(stances):
                        if idx < len(simplified_viewpoints):
                            stances_dict[participant][simplified_viewpoints[idx]] = stance
                    print(f"  ✓ {participant}: {' '.join(stances)}")
                else:
                    # 备用：全部中立
                    for sv in simplified_viewpoints:
                        stances_dict[participant][sv] = '△'
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_viewpoints_with_simplified(self, text: str) -> List[Tuple[str, str]]:
        """解析包含完整和简化版本的响应"""
        result = []
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 查找 "Viewpoint N:" 开头的行
            if line.startswith('Viewpoint ') and ':' in line:
                full = line.split(':', 1)[1].strip()
                
                # 查找下一行的 "Simplified:"
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('Simplified:'):
                        simp = next_line.split(':', 1)[1].strip()
                        
                        # 验证长度
                        if 5 <= len(full) <= 500 and 5 <= len(simp) <= 30:
                            result.append((full, simp))
                            print(f"  Parsed: [{simp}] = {full[:40]}...")
                        
                        i += 2
                        continue
            
            i += 1
        
        return result
    
    def _parse_stance_symbols(self, text: str, num: int) -> List[str]:
        """解析态度符号"""
        stances = ['△'] * num
        
        # 找所有符号
        symbols = re.findall(r'[✅❌△]', text)
        
        for i, symbol in enumerate(symbols[:num]):
            stances[i] = symbol
        
        print(f"    Parsed stances: {stances}")
        return stances