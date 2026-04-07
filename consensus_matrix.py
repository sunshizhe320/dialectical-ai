"""
共识矩阵 - 独立 Moonshot API 版本
完全独立调用，不依赖 generate_response()
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
        """直接调用 Moonshot API - 不依赖 generate_response()"""
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
                    print(f"[✅ API Response: {len(content)} chars]")
                    return content
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:200]}")
        
        except Exception as e:
            print(f"❌ API Call Error: {e}")
        
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
            
            # 提取观点
            prompt = f"""Analyze this discussion and extract 2-5 main viewpoints.

DISCUSSION:
{discussion_text}

Extract distinct viewpoints that people mentioned.

OUTPUT (numbered list only):
1. [Complete first viewpoint]
2. [Complete second viewpoint]
3. [etc]

Rules:
- Extract REAL viewpoints from discussion
- Be COMPLETE and CLEAR
- Each viewpoint 1-3 sentences
- Different perspectives only"""
            
            response = self._call_moonshot(
                prompt,
                "You are an expert discussion analyst. Extract viewpoints clearly."
            )
            
            if response and len(response) > 20:
                print(f"Response preview: {response[:100]}...")
                viewpoints = self._parse_viewpoints_smart(response)
                
                if viewpoints and len(viewpoints) >= 1:
                    print(f"✓ Extracted {len(viewpoints)} viewpoints")
                    result = [(vp, vp) for vp in viewpoints]
                    return result
            
            # 备用方案
            print("📌 Using fallback heuristic extraction...")
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
        分析态度 - 使用 Moonshot API
        """
        try:
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
                
                # 批量分析所有观点
                viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
                
                prompt = f"""Analyze {participant}'s stance on each viewpoint.

DISCUSSION:
{full_discussion}

VIEWPOINTS:
{viewpoints_str}

{participant}'s STATEMENTS:
{participant_text}

For each viewpoint, determine stance:
✅ = SUPPORTS/AGREES
❌ = OPPOSES/DISAGREES
△ = NEUTRAL/NOT MENTIONED

OUTPUT (one symbol per line, ONLY symbols):
✅
❌
△
etc."""
                
                response = self._call_moonshot(
                    prompt,
                    "Analyze discussion stances based on actual statements."
                )
                
                if response:
                    print(f"Response: {response[:50]}...")
                    stances = self._parse_stances_from_response(response, len(viewpoints))
                    
                    for idx, stance in enumerate(stances):
                        if idx < len(viewpoints):
                            stances_dict[participant][viewpoints[idx]] = stance
                    
                    results = [s for s in stances]
                    print(" ".join(results))
                else:
                    print("△" * len(viewpoints))
                    for vp in viewpoints:
                        stances_dict[participant][vp] = '△'
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Analyze Error: {e}")
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
            
            # 格式: "1. 观点"
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 5 <= len(item) <= 1000:
                    items.append(item)
        
        return items[:5]
    
    def _parse_stances_from_response(self, response: str, num_viewpoints: int) -> List[str]:
        """从响应中解析态度"""
        stances = ['△'] * num_viewpoints
        symbols_found = re.findall(r'[✅❌△]', response)
        
        for i, symbol in enumerate(symbols_found[:num_viewpoints]):
            stances[i] = symbol
        
        return stances
    
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
        
        return unique[:5]