"""
consensus_matrix.py - 改进版
集成 API 包装器，自动记录性能数据
"""

import json
import re
import os
import time
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import streamlit as st

from api_wrapper import KimiAPIWrapper
import db

load_dotenv()

MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY") or st.secrets.get("MOONSHOT_API_KEY", "")
db = DatabaseManager()


class ConsensusMatrix:
    """共识矩阵 - 使用改进的 API 包装器"""
    
    def __init__(self):
        self.api_key = MOONSHOT_KEY
        self.api_wrapper = KimiAPIWrapper(self.api_key)
    
    def _call_moonshot(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> Tuple[Optional[str], Dict]:
        """
        调用 Moonshot API（改进版）
        
        Returns:
            (response_text, metadata)
        """
        return self.api_wrapper.call_api(prompt, system_prompt)
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[List[Tuple[str, str]]]:
        """AI 提取观点"""
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 AI extracting viewpoints...")
            
            discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages
            ])
            
            if len(discussion) > 3500:
                discussion = discussion[:3500]
            
            prompt = f"""Analyze this discussion and extract ALL distinct viewpoints.

DISCUSSION:
{discussion}

For each viewpoint:
1. Provide the COMPLETE viewpoint (1-2 sentences)
2. Provide a SIMPLIFIED version (8-15 characters)

Output format EXACTLY:
Viewpoint 1: [complete viewpoint]
Simplified: [8-15 chars]

Viewpoint 2: [complete viewpoint]
Simplified: [8-15 chars]

Rules:
- Extract EVERY distinct viewpoint, not just the main ones
- No duplicates
- Be complete and clear"""
            
            # ✅ 调用 API 并获取元数据
            response, metadata = self._call_moonshot(
                prompt,
                "You are an expert discussion analyst. Extract viewpoints accurately."
            )
            
            # ✅ 保存 API 调用记录
            if session_id:
                db.save_message(
                    session_id=session_id,
                    user="AI",
                    role="system",
                    content=f"[Viewpoint Extraction]\nPrompt length: {len(discussion)}",
                    latency=metadata.get('latency', 0),
                    tokens_used=metadata.get('tokens_used', 0),
                    tokens_input=metadata.get('tokens_input', 0),
                    tokens_output=metadata.get('tokens_output', 0),
                    error_log=metadata.get('error_log'),
                    error_code=metadata.get('error_code'),
                    error_message=metadata.get('error_message'),
                    retry_count=metadata.get('retry_count', 0),
                    is_success=1 if metadata['success'] else 0,
                    quality_score=0.9 if metadata['success'] else 0
                )
            
            if not response:
                print(f"❌ API failed: {metadata['error_code']}")
                return None
            
            result = self._parse_viewpoints(response)
            
            if result:
                print(f"✓ Extracted {len(result)} viewpoints")
                return result
            
            return None
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def analyze_stances(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints_pairs: List[Tuple[str, str]],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """AI 分析态度"""
        try:
            print(f"\n📈 AI analyzing stances...")
            
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
            
            discussion = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in messages
                if m.get('user') != 'AI'
            ])
            
            if len(discussion) > 3500:
                discussion = discussion[:3500]
            
            viewpoints_text = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(full_viewpoints)])
            
            # 批量分析所有参与者
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_text = "\n".join(speaker_messages[participant])
                
                prompt = f"""Analyze {participant}'s stance on each viewpoint based on their actual statements.

DISCUSSION CONTEXT:
{discussion}

VIEWPOINTS TO ANALYZE:
{viewpoints_text}

{participant}'s ACTUAL STATEMENTS:
{participant_text}

For EACH viewpoint (1, 2, 3, etc.):
- Does {participant} SUPPORT/AGREE with it? (✅)
- Does {participant} OPPOSE/DISAGREE with it? (❌)
- Or is {participant} NEUTRAL or hasn't MENTIONED it? (△)

Output ONLY the symbols, nothing else, one per line."""
                
                # ✅ 调用 API 并获取元数据
                response, metadata = self._call_moonshot(prompt, "Analyze stances accurately.")
                
                # ✅ 保存 API 调用记录
                if session_id:
                    db.save_message(
                        session_id=session_id,
                        user="AI",
                        role="system",
                        content=f"[Stance Analysis for {participant}]",
                        latency=metadata.get('latency', 0),
                        tokens_used=metadata.get('tokens_used', 0),
                        tokens_input=metadata.get('tokens_input', 0),
                        tokens_output=metadata.get('tokens_output', 0),
                        error_log=metadata.get('error_log'),
                        error_code=metadata.get('error_code'),
                        error_message=metadata.get('error_message'),
                        retry_count=metadata.get('retry_count', 0),
                        is_success=1 if metadata['success'] else 0
                    )
                
                if response:
                    stances = self._parse_stances(response, len(full_viewpoints))
                    
                    for idx, stance in enumerate(stances):
                        if idx < len(simplified_viewpoints):
                            stances_dict[participant][simplified_viewpoints[idx]] = stance
                    
                    print(" ".join(stances))
                else:
                    print(f"⚠️ Error: {metadata['error_code']}")
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
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line and re.match(r'^[Vv]iewpoint\s+\d+\s*[:：]', line):
                full = re.sub(r'^[Vv]iewpoint\s+\d+\s*[:：]\s*', '', line).strip()
                
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^[Ss]implified\s*[:：]', next_line):
                        simp = re.sub(r'^[Ss]implified\s*[:：]\s*', '', next_line).strip()
                        
                        if 5 <= len(full) <= 500 and 5 <= len(simp) <= 30:
                            result.append((full, simp))
                        
                        i += 2
                        continue
            
            i += 1
        
        return result
    
    def _parse_stances(self, response: str, num: int) -> List[str]:
        """解析态度符号"""
        stances = ['△'] * num
        symbols = re.findall(r'[✅❌△]', response)
        
        for i, symbol in enumerate(symbols[:num]):
            stances[i] = symbol
        
        return stances