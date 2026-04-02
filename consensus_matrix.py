"""
智能共识矩阵计算模块 - 增强版
支持隐含观点挖掘、态度继承、上下文理解
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ConsensusMatrix:
    """智能共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_viewpoints_step1(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[str]]:
        """多轮智能提取观点 - 显式 + 隐含"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            message_count = len(user_messages)
            
            discussion_text = "\n".join([
                f"{m.get('user')}: {m.get('message', '')}"
                for m in user_messages[-20:]
            ])
            
            if len(discussion_text) > 3500:
                discussion_text = discussion_text[:3500]
            
            print(f"\n📊 [第 1 阶段] 提取显式观点")
            
            # 第一轮：提取显式观点
            explicit_viewpoints = self._extract_explicit_viewpoints(
                discussion_text,
                message_count,
                llm_mode
            )
            
            print(f"  显式观点: {len(explicit_viewpoints)} 个")
            
            # 第二轮：挖掘隐含观点
            print(f"\n📊 [第 2 阶段] 挖掘隐含观点")
            
            implicit_viewpoints = self._extract_implicit_viewpoints(
                discussion_text,
                explicit_viewpoints,
                llm_mode
            )
            
            print(f"  隐含观点: {len(implicit_viewpoints)} 个")
            
            # 合并并去重
            all_viewpoints = explicit_viewpoints + implicit_viewpoints
            final_viewpoints = self._deduplicate_viewpoints(all_viewpoints, llm_mode)
            
            # 限制数量
            if message_count == 1:
                final_viewpoints = final_viewpoints[:1]
            elif message_count <= 2:
                final_viewpoints = final_viewpoints[:2]
            elif message_count <= 4:
                final_viewpoints = final_viewpoints[:3]
            else:
                final_viewpoints = final_viewpoints[:5]
            
            print(f"\n✅ 最终观点: {len(final_viewpoints)} 个\n")
            
            return final_viewpoints if final_viewpoints else None
        
        except Exception as e:
            print(f"❌ extract_viewpoints_step1 错误: {e}")
            return None
    
    def _extract_explicit_viewpoints(
        self,
        discussion_text: str,
        message_count: int,
        llm_mode: str
    ) -> List[str]:
        """第一轮：提取显式表述的观点"""
        from ai_agent import generate_response
        
        if message_count == 1:
            range_text = "exactly 1"
        elif message_count <= 2:
            range_text = "1-2"
        else:
            range_text = "1-2"
        
        prompt = f"""提取讨论中 EXPLICITLY 表述的观点。

消息数量: {message_count}

讨论内容:
{discussion_text}

任务: 提取 {range_text} 个在讨论中 CLEARLY 表述的、参与者DIRECTLY 提出的主要观点。

规则:
- 只提取参与者明确说出的观点
- 不推理、不想象
- 可以稍加改写以便理解

格式 - 编号列表:
1. [观点 1 - 直接引用或改写]
2. [观点 2 - 直接引用或改写]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return []
        
        viewpoints = self._parse_numbered_list(response)
        return viewpoints
    
    def _extract_implicit_viewpoints(
        self,
        discussion_text: str,
        explicit_viewpoints: List[str],
        llm_mode: str
    ) -> List[str]:
        """第二轮：挖掘隐含观点"""
        from ai_agent import generate_response
        
        explicit_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(explicit_viewpoints)])
        
        prompt = f"""分析讨论中的隐含观点和深层含义。

已识别的显式观点:
{explicit_str}

讨论内容:
{discussion_text}

任务: 找出未直接表述但可以推理得出的观点。例如:
- 参与者举的例子所隐含的观点
- 参与者的担忧或期望
- 参与者通过反问或讽刺表达的观点
- 参与者提出的解决方案所隐含的问题认识

只提取1-2个最重要的隐含观点。

格式:
1. [隐含观点 1]
2. [隐含观点 2]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return []
        
        viewpoints = self._parse_numbered_list(response)
        return viewpoints
    
    def _deduplicate_viewpoints(
        self,
        viewpoints: List[str],
        llm_mode: str
    ) -> List[str]:
        """去重和合并相似观点"""
        from ai_agent import generate_response
        
        if len(viewpoints) <= 1:
            return viewpoints
        
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        prompt = f"""分析这些观点，去除重复和相似的。

观点列表:
{viewpoints_str}

任务: 
1. 找出重复或高度相似的观点
2. 将相似观点合并为一个更全面的观点
3. 保留不同的观点

输出格式:
KEEP: 1, 3, 5
MERGE: 2 and 4 as "[merged viewpoint]"

例如:
KEEP: 1, 3
MERGE: 2 and 4 as "远程工作带来的时间和精力节省"
REMOVE: 5"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return viewpoints
        
        result = []
        
        # 解析 KEEP 列表
        keep_match = re.search(r'KEEP:\s*([0-9,\s]+)', response, re.IGNORECASE)
        if keep_match:
            keep_str = keep_match.group(1)
            keep_indices = [int(x.strip()) - 1 for x in keep_str.split(',') if x.strip().isdigit()]
            result.extend([viewpoints[i] for i in keep_indices if i < len(viewpoints)])
        
        # 解析 MERGE 列表
        merge_matches = re.finditer(r'as\s+"([^"]+)"', response, re.IGNORECASE)
        for match in merge_matches:
            result.append(match.group(1))
        
        return result if result else viewpoints
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # 匹配 "1. text" 或 "1) text" 格式
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                if len(item) > 3 and len(item) < 300:
                    items.append(item)
        
        return items
    
    def analyze_stances_step2(
        self,
        messages: List[Dict],
        participants: List[str],
        viewpoints: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[Dict]:
        """智能分析态度 - 支持继承"""
        try:
            stances_dict = {p: {} for p in participants}
            
            # 为每个参与者分析
            for idx, participant in enumerate(participants):
                print(f"\n👤 分析参与者: {participant}")
                
                # 获取参与者的所有消息和上文
                participant_stances = self._analyze_participant_stances(
                    participant,
                    messages,
                    viewpoints,
                    idx,  # 传入参与者的索引
                    llm_mode
                )
                
                stances_dict[participant] = participant_stances
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ analyze_stances_step2 错误: {e}")
            return None
    
    def _analyze_participant_stances(
        self,
        participant: str,
        messages: List[Dict],
        viewpoints: List[str],
        participant_idx: int,
        llm_mode: str
    ) -> Dict[str, str]:
        """分析单个参与者对所有观点的态度"""
        from ai_agent import generate_response
        
        # 获取所有消息上下文
        full_discussion = "\n".join([
            f"{m.get('user')}: {m.get('message', '')}"
            for m in messages
        ])
        
        # 获取该参与者的消息
        participant_msgs = [
            m.get('message', '')
            for m in messages
            if m.get('user') == participant and m.get('message', '')
        ]
        
        if not participant_msgs:
            # 未发言 -> 所有观点都是△
            return {vp: '△' for vp in viewpoints}
        
        participant_text = "\n".join(participant_msgs)
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        prompt = f"""分析 {participant} 对各个观点的态度。

所有观点:
{viewpoints_str}

完整讨论过程:
{full_discussion}

{participant} 的发言:
{participant_text}

任务: 对每个观点判断 {participant} 的态度。

特殊规则:
- 如果 {participant} 说"赞同上面的观点"或"同意"，则继承前一个发言人对该观点的态度
- 如果 {participant} 是补充或扩展前面的观点，则对该观点标记为同意✅
- 需要理解上下文和隐含意思

格式 - CSV:
1,✅
2,△
3,❌

说明:
✅ = {participant} 支持/同意该观点
❌ = {participant} 反对/不同意该观点
△ = {participant} 未提及或态度不清楚"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return {vp: '△' for vp in viewpoints}
        
        # 解析 CSV 格式
        stances = {}
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or ',' not in line:
                continue
            
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    idx = int(parts[0].strip()) - 1
                    stance = parts[1].strip()
                    
                    if stance in ['✅', '❌', '△'] and idx < len(viewpoints):
                        vp = viewpoints[idx]
                        stances[vp] = stance
                        print(f"  {vp[:30]}... → {stance}")
                except:
                    continue
        
        # 填充缺失的观点
        for vp in viewpoints:
            if vp not in stances:
                stances[vp] = '△'
        
        return stances
    
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