"""
共识矩阵 - 优化版本
智能缓存 + 限流 + 备用方案
"""

import json
import re
import requests
import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime, timedelta

load_dotenv()

# 获取 API KEY
MOONSHOT_KEY = None
try:
    if hasattr(st, 'secrets') and 'MOONSHOT_API_KEY' in st.secrets:
        MOONSHOT_KEY = st.secrets['MOONSHOT_API_KEY']
except:
    pass

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")


class ConsensusMatrix:
    """共识矩阵计算器 - 带缓存和限流"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
        self.cache = {}  # {session_id: {messages_hash: (viewpoints, stances)}}
        self.last_api_call = None
        self.min_interval = 5  # 最少 5 秒调用一次 API
    
    def _should_call_api(self) -> bool:
        """判断是否应该调用 API"""
        now = datetime.now()
        if self.last_api_call is None:
            return True
        
        elapsed = (now - self.last_api_call).total_seconds()
        return elapsed >= self.min_interval
    
    def _messages_hash(self, messages: List[Dict]) -> str:
        """生成消息哈希用于缓存"""
        user_messages = [m for m in messages if m.get('user') != 'AI']
        text = "".join([m.get('message', '') for m in user_messages])
        return str(hash(text))
    
    def _call_moonshot(self, prompt: str, system_prompt: str = "", max_tokens: int = 1000) -> Optional[str]:
        """
        调用 Moonshot API - 带速率限制
        """
        if not self.api_key:
            print("❌ API Key not configured")
            return None
        
        # 速率限制
        if not self._should_call_api():
            print("⏳ Rate limit: waiting before next API call")
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
                "max_tokens": max_tokens
            }
            
            print(f"[📤 API Call] Calling Moonshot API...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            self.last_api_call = datetime.now()
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    print(f"[✅ API Success] {len(content)} chars")
                    return content
            elif response.status_code == 429:
                print(f"❌ Rate Limited (429): API quota exceeded")
                return None
            else:
                print(f"❌ API Error {response.status_code}")
                return None
        
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
        提取观点 - 带缓存
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 Extracting viewpoints from {len(user_messages)} messages...")
            
            # 检查缓存
            msg_hash = self._messages_hash(messages)
            if session_id in self.cache and msg_hash in self.cache[session_id]:
                print(f"[💾 Cache Hit] Using cached viewpoints")
                viewpoints_pairs, _ = self.cache[session_id][msg_hash]
                return viewpoints_pairs
            
            # 构建讨论文本
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 2000:
                discussion_text = discussion_text[:2000]
            
            # 尝试 API 调用
            if self._should_call_api():
                prompt_extract = f"""Extract 2-4 distinct viewpoints from this discussion.

DISCUSSION:
{discussion_text}

Output format - numbered list only:
1. [Viewpoint 1]
2. [Viewpoint 2]
3. [Viewpoint 3]

Rules: Extract REAL viewpoints, be complete and clear."""
                
                response = self._call_moonshot(
                    prompt_extract,
                    "Extract viewpoints as a numbered list only.",
                    max_tokens=600
                )
                
                if response and len(response) > 20:
                    full_viewpoints = self._parse_numbered_list(response)
                    
                    if full_viewpoints and len(full_viewpoints) >= 1:
                        # 简化观点
                        simplified = self._simplify_viewpoints(full_viewpoints)
                        result = list(zip(full_viewpoints, simplified))
                        
                        # 缓存
                        if session_id:
                            if session_id not in self.cache:
                                self.cache[session_id] = {}
                            self.cache[session_id][msg_hash] = (result, None)
                        
                        print(f"✓ Extracted {len(result)} viewpoints")
                        return result
            
            # 备用方案：启发式提取
            print("📌 Using fallback heuristic extraction...")
            viewpoints = self._heuristic_extract(user_messages)
            if viewpoints:
                result = [(vp, vp[:15]) for vp in viewpoints]
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def _simplify_viewpoints(self, viewpoints: List[str]) -> List[str]:
        """简化观点到 8-15 字"""
        simplified = []
        
        for vp in viewpoints:
            # 提取关键词
            words = vp.split()
            
            # 简单简化：取前 2-3 个关键词
            key_words = [w for w in words if len(w) > 2][:3]
            simp = " ".join(key_words)
            
            # 截断到 15 字
            if len(simp) > 15:
                simp = simp[:12] + "…"
            
            simplified.append(simp)
        
        return simplified
    
    def analyze_stances(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints_pairs: List[Tuple[str, str]],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """
        分析态度 - 带缓存和备用方案
        """
        try:
            print(f"\n📈 Analyzing stances for {len(participants)} participants...")
            
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
            
            # 尝试 API 分析
            if self._should_call_api():
                for participant in participants:
                    if participant not in speaker_messages:
                        stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                        continue
                    
                    participant_text = "\n".join(speaker_messages[participant])
                    viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
                    
                    prompt = f"""Analyze {participant}'s stance on each viewpoint.

VIEWPOINTS:
{viewpoints_str}

{participant}'s STATEMENTS:
{participant_text}

Output ONLY numbered symbols:
1. ✅
2. ❌
3. △"""
                    
                    response = self._call_moonshot(
                        prompt,
                        "Analyze stances. Output ONLY numbered symbols.",
                        max_tokens=300
                    )
                    
                    if response:
                        stances = self._parse_stances(response, len(full_viewpoints))
                        for idx, s in enumerate(stances):
                            if idx < len(simplified_viewpoints):
                                stances_dict[participant][simplified_viewpoints[idx]] = s
                        print(f"  ✓ {participant}: {' '.join(stances)}")
                    else:
                        # 备用：启发式分析
                        for sv in simplified_viewpoints:
                            stances_dict[participant][sv] = '△'
            else:
                # 速率限制：使用启发式方案
                print("⏳ Rate limited, using heuristic analysis...")
                for participant in participants:
                    if participant not in speaker_messages:
                        stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    else:
                        participant_text = "\n".join(speaker_messages[participant]).lower()
                        for sv in simplified_viewpoints:
                            stance = self._heuristic_stance(participant_text, sv)
                            stances_dict[participant][sv] = stance
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 3 <= len(item) <= 1000:
                    items.append(item)
        return items
    
    def _parse_stances(self, response: str, num: int) -> List[str]:
        """解析态度"""
        stances = ['△'] * num
        symbols = re.findall(r'[✅❌△]', response)
        for i, s in enumerate(symbols[:num]):
            stances[i] = s
        return stances
    
    def _heuristic_extract(self, messages: List[Dict]) -> List[str]:
        """启发式提取"""
        viewpoints = []
        for msg in messages:
            text = msg.get('message', '').strip()
            if 10 < len(text) < 500:
                viewpoints.append(text)
        
        seen = set()
        unique = []
        for vp in viewpoints:
            if vp[:30].lower() not in seen:
                seen.add(vp[:30].lower())
                unique.append(vp)
        
        return unique[:4]
    
    def _heuristic_stance(self, text: str, viewpoint: str) -> str:
        """启发式态度分析"""
        support = ['support', 'agree', 'good', '支持', '同意', '赞成', '好']
        oppose = ['oppose', 'disagree', 'bad', '反对', '不同意', '不赞成']
        
        sup_count = sum(text.count(w) for w in support)
        opp_count = sum(text.count(w) for w in oppose)
        
        if sup_count > opp_count > 0:
            return '✅'
        elif opp_count > sup_count > 0:
            return '❌'
        else:
            return '△'