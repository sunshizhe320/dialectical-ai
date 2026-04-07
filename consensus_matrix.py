"""
共识矩阵 - Moonshot API 完整版本
智能提取简洁观点 + 准确分析态度 + 实时更新
"""

import json
import re
import requests
import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# 获取 API KEY - 优先从 Streamlit Secrets 读取
MOONSHOT_KEY = None

try:
    if hasattr(st, 'secrets') and 'MOONSHOT_API_KEY' in st.secrets:
        MOONSHOT_KEY = st.secrets['MOONSHOT_API_KEY']
        print(f"✅ MOONSHOT_API_KEY loaded from Streamlit Secrets")
except Exception as e:
    print(f"⚠️ Could not read Streamlit Secrets: {e}")

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    if MOONSHOT_KEY:
        print(f"✅ MOONSHOT_API_KEY loaded from environment")

if MOONSHOT_KEY:
    print(f"✅ API Key ready (length: {len(MOONSHOT_KEY)})")
else:
    print(f"❌ MOONSHOT_API_KEY not configured!")


class ConsensusMatrix:
    """共识矩阵计算器 - AI 版本"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
        self.max_retries = 2
    
    def _call_moonshot(self, prompt: str, system_prompt: str = "", max_tokens: int = 1000) -> Optional[str]:
        """
        调用 Moonshot API - 带重试机制
        """
        if not self.api_key:
            print("❌ MOONSHOT_API_KEY not configured")
            return None
        
        for attempt in range(self.max_retries):
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
                
                print(f"[Attempt {attempt + 1}] Calling Moonshot API...")
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"].strip()
                        print(f"✅ API Success: {len(content)} chars")
                        return content
                else:
                    print(f"❌ API Error {response.status_code}: {response.text[:100]}")
            
            except Exception as e:
                print(f"❌ API Call Error (attempt {attempt + 1}): {e}")
        
        print(f"❌ All {self.max_retries} attempts failed")
        return None
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control"
    ) -> Optional[List[Tuple[str, str]]]:
        """
        AI 提取观点 + 生成简洁版本
        返回: [(完整观点, 简洁版本), ...]
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 AI Extracting viewpoints from {len(user_messages)} messages...")
            
            # 构建讨论文本
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion_text) > 2000:
                discussion_text = discussion_text[:2000]
            
            # 第一步：AI 提取观点
            prompt_extract = f"""Analyze this discussion and extract 2-4 distinct viewpoints.

DISCUSSION:
{discussion_text}

Extract the core viewpoints that different participants mentioned. Each viewpoint should be unique and represent a different perspective.

Output format - numbered list:
1. [Complete viewpoint 1]
2. [Complete viewpoint 2]
3. [Complete viewpoint 3]

Rules:
- Extract REAL viewpoints from the discussion
- Each viewpoint should be complete and clear
- Different perspectives only
- 1-2 sentences per viewpoint"""
            
            response_extract = self._call_moonshot(
                prompt_extract,
                "You are an expert discussion analyst. Extract viewpoints clearly and comprehensively.",
                max_tokens=800
            )
            
            if not response_extract or len(response_extract) < 20:
                print("❌ Failed to extract viewpoints")
                return None
            
            print(f"[Extracted] {response_extract[:100]}...")
            
            # 解析提取的观点
            full_viewpoints = self._parse_numbered_list(response_extract)
            
            if not full_viewpoints:
                print("❌ No viewpoints parsed")
                return None
            
            print(f"✓ Extracted {len(full_viewpoints)} viewpoints")
            
            # 第二步：AI 简化观点到 8-15 字
            viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
            
            prompt_simplify = f"""Simplify each viewpoint to 8-15 Chinese characters.

VIEWPOINTS:
{viewpoints_str}

Create a simplified version for each viewpoint that captures the core idea in 8-15 characters.

Output format - numbered list:
1. 简化观点1
2. 简化观点2
3. 简化观点3

Rules:
- Keep the core meaning
- Exactly 8-15 characters
- Use simple, direct language"""
            
            response_simplify = self._call_moonshot(
                prompt_simplify,
                "Simplify viewpoints to 8-15 characters. Preserve core meaning.",
                max_tokens=400
            )
            
            simplified_viewpoints = self._parse_numbered_list(response_simplify) if response_simplify else []
            
            # 配对完整和简化版本
            result = []
            for i, full in enumerate(full_viewpoints):
                simplified = simplified_viewpoints[i] if i < len(simplified_viewpoints) else full[:15]
                
                # 确保简化版本不超过 20 字
                if len(simplified) > 20:
                    simplified = simplified[:17] + "…"
                
                result.append((full, simplified))
                print(f"  [{simplified}] → {full[:50]}...")
            
            return result if result else None
        
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
        AI 分析每个参与者对每个观点的态度
        返回: {参与者: {简化观点: '✅/❌/△'}}
        """
        try:
            print(f"\n📈 AI Analyzing stances for {len(participants)} participants...")
            
            stances_dict = {p: {} for p in participants}
            
            # 获取发言者及其消息
            speaker_messages = {}
            for m in messages:
                user = m.get('user')
                if user and user != 'AI':
                    if user not in speaker_messages:
                        speaker_messages[user] = []
                    speaker_messages[user].append(m.get('message', ''))
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            # 构建完整讨论文本
            full_discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in messages
                if m.get('user') != 'AI'
            ])
            
            if len(full_discussion) > 2500:
                full_discussion = full_discussion[:2500]
            
            # 为所有参与者批量分析
            viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
            
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                # 未发言 → 全部中立
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_msgs = speaker_messages[participant]
                participant_text = "\n".join(participant_msgs)
                
                # AI 分析该参与者的立场
                prompt_analyze = f"""Analyze {participant}'s stance on each viewpoint based on their actual statements.

VIEWPOINTS TO ANALYZE:
{viewpoints_str}

FULL DISCUSSION CONTEXT:
{full_discussion}

{participant}'s STATEMENTS:
{participant_text}

For each viewpoint, determine if {participant}:
✅ SUPPORTS or AGREES with it (based on their statements)
❌ OPPOSES or DISAGREES with it (based on their statements)
△ is NEUTRAL or hasn't MENTIONED it

Output ONLY a numbered list with symbols:
1. ✅
2. ❌
3. △
etc.

IMPORTANT: Base your analysis ONLY on {participant}'s actual statements, not on the discussion context."""
                
                response_analyze = self._call_moonshot(
                    prompt_analyze,
                    "Analyze participant stances based on their actual statements. Output ONLY numbered symbols.",
                    max_tokens=500
                )
                
                if response_analyze:
                    print(f"Response: {response_analyze[:50]}...")
                    stances = self._parse_stances(response_analyze, len(full_viewpoints))
                    
                    for idx, stance in enumerate(stances):
                        if idx < len(simplified_viewpoints):
                            stances_dict[participant][simplified_viewpoints[idx]] = stance
                    
                    results = [s for s in stances]
                    print(" ".join(results))
                else:
                    print("△" * len(full_viewpoints))
                    for sv in simplified_viewpoints:
                        stances_dict[participant][sv] = '△'
            
            print()
            return stances_dict
        
        except Exception as e:
            print(f"❌ Analyze Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        if not text:
            return []
        
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # 匹配 "1. " 或 "1) " 格式
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if 3 <= len(item) <= 1000:
                    items.append(item)
        
        return items
    
    def _parse_stances(self, response: str, num_viewpoints: int) -> List[str]:
        """解析态度响应"""
        stances = ['△'] * num_viewpoints
        
        if not response:
            return stances
        
        # 查找所有符号
        symbols_found = re.findall(r'[✅❌△]', response)
        
        # 配对到对应的观点
        for i, symbol in enumerate(symbols_found[:num_viewpoints]):
            stances[i] = symbol
        
        return stances