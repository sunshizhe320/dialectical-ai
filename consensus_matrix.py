"""
智能共识矩阵计算模块
支持多轮验证、引用证据、动态置信度评估
大幅减少 LLM 幻觉
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ConsensusMatrix:
    """智能共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
        self.verified_viewpoints = {}  # 已验证的观点缓存
    
    def extract_viewpoints_step1(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[str]]:
        """智能提取观点 - 带验证和证据"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            message_count = len(user_messages)
            
            # 第一阶段：提取初始观点
            print(f"\n📊 [第 1 阶段] 初始观点提取 (来自 {message_count} 条消息)")
            initial_viewpoints = self._extract_initial_viewpoints(
                user_messages, 
                message_count, 
                llm_mode
            )
            
            if not initial_viewpoints:
                return None
            
            print(f"  初始提取: {len(initial_viewpoints)} 个观点")
            
            # 第二阶段：验证和去重
            print(f"\n✅ [第 2 阶段] 验证观点真实性")
            verified_viewpoints = self._verify_viewpoints(
                initial_viewpoints,
                user_messages,
                llm_mode
            )
            
            print(f"  验证后: {len(verified_viewpoints)} 个观点")
            
            # 第三阶段：添加置信度评分
            print(f"\n🎯 [第 3 阶段] 计算置信度")
            scored_viewpoints = self._score_viewpoints(
                verified_viewpoints,
                user_messages,
                llm_mode
            )
            
            # 过滤低置信度观点 (< 0.5)
            final_viewpoints = [
                vp for vp, score in scored_viewpoints 
                if score >= 0.5
            ]
            
            print(f"  最终结果: {len(final_viewpoints)} 个高置信度观点\n")
            
            return final_viewpoints if final_viewpoints else None
        
        except Exception as e:
            print(f"❌ extract_viewpoints_step1 错误: {e}")
            return None
    
    def _extract_initial_viewpoints(
        self,
        messages: List[Dict],
        message_count: int,
        llm_mode: str
    ) -> List[str]:
        """第一阶段：初始提取"""
        from ai_agent import generate_response
        
        discussion_text = "\n".join([
            f"{m.get('user')}: {m.get('message', '')}"
            for m in messages[-20:]
        ])
        
        if len(discussion_text) > 2500:
            discussion_text = discussion_text[:2500]
        
        # 根据消息数量调整期望
        if message_count == 1:
            range_text = "EXACTLY 1"
        elif message_count <= 2:
            range_text = "1-2"
        elif message_count <= 4:
            range_text = "1-2 (最多)"
        else:
            range_text = "2-3"
        
        prompt = f"""Extract CORE viewpoints from this discussion.
STRICT RULE: Only extract if explicitly stated in the discussion. Do NOT invent.

Messages: {message_count}

DISCUSSION:
{discussion_text}

Extract {range_text} viewpoints. For each, include evidence quote.

FORMAT:
VIEWPOINT: [concise statement]
EVIDENCE: "[quote from discussion]"

---
VIEWPOINT: [another viewpoint]
EVIDENCE: "[quote from discussion]"
"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return []
        
        viewpoints = self._parse_viewpoint_evidence(response)
        return viewpoints
    
    def _parse_viewpoint_evidence(self, text: str) -> List[str]:
        """解析包含证据的观点"""
        viewpoints = []
        
        # 按 VIEWPOINT: 分割
        blocks = text.split('VIEWPOINT:')
        
        for block in blocks[1:]:  # 跳过第一个空块
            # 提取观点和证据
            lines = block.strip().split('\n')
            
            if not lines:
                continue
            
            viewpoint = lines[0].strip()
            
            # 查找 EVIDENCE 行
            has_evidence = any('EVIDENCE:' in line or 'Evidence:' in line.lower() for line in lines)
            
            if viewpoint and len(viewpoint) > 5 and has_evidence:
                viewpoints.append(viewpoint)
        
        return viewpoints
    
    def _verify_viewpoints(
        self,
        viewpoints: List[str],
        messages: List[Dict],
        llm_mode: str
    ) -> List[str]:
        """第二阶段：验证观点"""
        from ai_agent import generate_response
        
        if len(viewpoints) <= 1:
            return viewpoints
        
        discussion_text = "\n".join([
            f"{m.get('user')}: {m.get('message', '')}"
            for m in messages[-15:]
        ])
        
        if len(discussion_text) > 2000:
            discussion_text = discussion_text[:2000]
        
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        prompt = f"""Verify which viewpoints are ACTUALLY discussed:

PROPOSED VIEWPOINTS:
{viewpoints_str}

DISCUSSION:
{discussion_text}

For each viewpoint:
- KEEP if: someone explicitly states it or clearly supports/opposes it
- REMOVE if: not mentioned or only my interpretation

Format:
KEEP: 1, 2
REMOVE: 3"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return viewpoints
        
        # 解析 KEEP 列表
        keep_match = re.search(r'KEEP:\s*([0-9,\s]+)', response, re.IGNORECASE)
        if keep_match:
            keep_str = keep_match.group(1)
            keep_indices = [int(x.strip()) - 1 for x in keep_str.split(',') if x.strip().isdigit()]
            verified = [viewpoints[i] for i in keep_indices if i < len(viewpoints)]
            return verified
        
        return viewpoints
    
    def _score_viewpoints(
        self,
        viewpoints: List[str],
        messages: List[Dict],
        llm_mode: str
    ) -> List[Tuple[str, float]]:
        """第三阶段：计算置信度"""
        from ai_agent import generate_response
        
        if len(viewpoints) <= 1:
            return [(vp, 1.0) for vp in viewpoints]
        
        discussion_text = "\n".join([
            f"{m.get('user')}: {m.get('message', '')}"
            for m in messages[-15:]
        ])
        
        if len(discussion_text) > 2000:
            discussion_text = discussion_text[:2000]
        
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        prompt = f"""Rate confidence (0-100) for each viewpoint:

VIEWPOINTS:
{viewpoints_str}

DISCUSSION:
{discussion_text}

Scoring:
- 90-100: Explicitly mentioned, clear support/opposition
- 70-89: Clearly implied, good evidence
- 50-69: Somewhat supported, but not explicit
- Below 50: Vague or weak evidence

Format:
1: 95
2: 72
3: 45"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return [(vp, 0.7) for vp in viewpoints]
        
        # 解析分数
        scores = []
        for line in response.split('\n'):
            match = re.match(r'^(\d+):\s*(\d+)', line.strip())
            if match:
                idx = int(match.group(1)) - 1
                score = int(match.group(2)) / 100.0
                
                if idx < len(viewpoints):
                    scores.append((viewpoints[idx], score))
        
        if not scores:
            return [(vp, 0.7) for vp in viewpoints]
        
        return scores
    
    def analyze_stances_step2(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """智能分析态度 - 带论文和验证"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages[-20:]
            ])
            
            if len(discussion_text) > 2500:
                discussion_text = discussion_text[:2500]
            
            print(f"\n📊 [态度分析] 为 {len(participants)} 个参与者分析态度")
            
            # 为每个参与者和观点分析
            stances_dict = {p: {} for p in participants}
            
            for viewpoint in viewpoints:
                print(f"\n  分析观点: {viewpoint[:40]}...")
                
                for participant in participants:
                    stance = self._analyze_single_stance(
                        participant,
                        viewpoint,
                        discussion_text,
                        messages,
                        llm_mode
                    )
                    stances_dict[participant][viewpoint] = stance
            
            print(f"\n✅ 态度分析完成\n")
            return stances_dict
        
        except Exception as e:
            print(f"❌ analyze_stances_step2 错误: {e}")
            return None
    
    def _analyze_single_stance(
        self,
        participant: str,
        viewpoint: str,
        discussion_text: str,
        messages: List[Dict],
        llm_mode: str
    ) -> str:
        """分析单个参与者对单个观点的态度"""
        from ai_agent import generate_response
        
        # 提取该参与者的消息
        participant_msgs = [
            m.get('message', '') 
            for m in messages 
            if m.get('user') == participant
        ]
        
        if not participant_msgs:
            return '△'
        
        participant_text = "\n".join(participant_msgs)
        
        prompt = f"""Analyze {participant}'s stance on this viewpoint.

VIEWPOINT: {viewpoint}

{participant}'s statements:
{participant_text}

STRICT RULES:
- ✅ only if {participant} explicitly agrees/supports
- ❌ only if {participant} explicitly disagrees/opposes
- △ if {participant} doesn't mention it or is unclear

Provide evidence quote.

FORMAT:
STANCE: [✅ or ❌ or △]
EVIDENCE: "[quote]"
REASONING: [brief explanation]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return '△'
        
        # 解析态度
        stance_match = re.search(r'STANCE:\s*([✅❌△])', response)
        if stance_match:
            return stance_match.group(1)
        
        return '△'
    
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