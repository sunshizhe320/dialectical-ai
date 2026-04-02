"""
超强智能共识矩阵计算模块 - Pro 版本
多维度分析、深度推理、高精准度
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ConsensusMatrix:
    """超强智能共识矩阵计算器"""
    
    def __init__(self):
        self.cache = {}
    
    def extract_viewpoints_step1(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "AI-Scaffolded"
    ) -> Optional[List[str]]:
        """多维度深度提取观点 - 超强版"""
        try:
            from ai_agent import generate_response
            
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            message_count = len(user_messages)
            
            discussion_text = "\n".join([
                f"[{i+1}] {m.get('user')}: {m.get('message', '')}"
                for i, m in enumerate(user_messages[-30:])
            ])
            
            if len(discussion_text) > 4000:
                discussion_text = discussion_text[:4000]
            
            print(f"\n{'='*60}")
            print(f"🔥 [超强观点提取] 消息数: {message_count}")
            print(f"{'='*60}")
            
            # 第一轮：显式观点提取（Chain of Thought）
            print(f"\n📌 [第 1 轮] 显式观点 (CoT 逐步推理)")
            explicit = self._extract_explicit_cot(discussion_text, message_count, llm_mode)
            print(f"   ✓ 提取 {len(explicit)} 个显式观点")
            
            # 第二轮：隐含观点深度挖掘
            print(f"\n📌 [第 2 轮] 隐含观点 (Socratic 深度挖掘)")
            implicit = self._extract_implicit_socratic(discussion_text, explicit, llm_mode)
            print(f"   ✓ 挖掘 {len(implicit)} 个隐含观点")
            
            # 第三轮：对立观点识别
            print(f"\n📌 [第 3 轮] 对立观点 (冲突识别)")
            opposing = self._extract_opposing_views(discussion_text, explicit + implicit, llm_mode)
            print(f"   ✓ 识别 {len(opposing)} 个对立观点")
            
            # 第四轮：细节观点补充
            print(f"\n📌 [第 4 轮] 细节观点 (关键补充)")
            details = self._extract_detail_viewpoints(discussion_text, explicit + implicit + opposing, llm_mode)
            print(f"   ✓ 补充 {len(details)} 个细节观点")
            
            # 合并所有观点
            all_viewpoints = explicit + implicit + opposing + details
            
            # 第五轮：去重、排序、过滤
            print(f"\n📌 [第 5 轮] 智能去重和排序")
            final_viewpoints = self._deduplicate_and_rank(all_viewpoints, discussion_text, llm_mode)
            print(f"   ✓ 最终 {len(final_viewpoints)} 个观点")
            
            # 限制数量
            max_viewpoints = min(message_count + 2, 7)  # 最多 7 个
            final_viewpoints = final_viewpoints[:max_viewpoints]
            
            print(f"\n{'='*60}")
            print(f"✅ 观点提取完成: {len(final_viewpoints)} 个观点")
            print(f"{'='*60}\n")
            
            return final_viewpoints if final_viewpoints else None
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def _extract_explicit_cot(self, discussion_text: str, message_count: int, llm_mode: str) -> List[str]:
        """使用 Chain of Thought 逐步推理"""
        from ai_agent import generate_response
        
        prompt = f"""你是一个论文分析专家。使用 Chain of Thought 方法逐步分析讨论内容。

讨论内容:
{discussion_text}

任务: 使用以下步骤逐步识别显式观点：

步骤 1: 列出每个参与者明确表述的主张
步骤 2: 识别关键词和信号词（主要、认为、应该、需要等）
步骤 3: 提取核心观点，去除修饰词
步骤 4: 列出最终观点列表

格式:
步骤 1:
- 参与者A说: ...
- 参与者B说: ...

步骤 2:
关键词: ...

步骤 3:
核心观点: ...

步骤 4:
最终观点:
1. [观点 1]
2. [观点 2]
3. [观点 3]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        if not response:
            return []
        
        # 提取"最终观点:"之后的内容
        if "最终观点:" in response:
            viewpoints_section = response.split("最终观点:")[-1]
            viewpoints = self._parse_numbered_list(viewpoints_section)
        else:
            viewpoints = self._parse_numbered_list(response)
        
        return viewpoints
    
    def _extract_implicit_socratic(self, discussion_text: str, explicit_vps: List[str], llm_mode: str) -> List[str]:
        """使用 Socratic 方法进行深度挖掘"""
        from ai_agent import generate_response
        
        explicit_str = "\n".join([f"- {vp}" for vp in explicit_vps])
        
        prompt = f"""你是一个 Socratic 方法的大师，通过提问来挖掘隐含观点。

已识别的显式观点:
{explicit_str}

讨论内容:
{discussion_text}

使用 Socratic 方法深度分析，找出隐含观点：

思考以下问题并给出答案：
1. 参与者为什么提出这些观点？他们的根本关切是什么？
2. 观点背后的价值观或假设是什么？
3. 参与者举的例子隐含了什么观点？
4. 他们的提议（如果有）背后的问题诊断是什么？
5. 未被明确提及但被隐含假设的观点？

隐含观点列表:
1. [隐含观点 1 - 带着原因]
2. [隐含观点 2]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        if not response:
            return []
        
        # 提取编号列表
        viewpoints = self._parse_numbered_list(response)
        
        return viewpoints
    
    def _extract_opposing_views(self, discussion_text: str, existing_vps: List[str], llm_mode: str) -> List[str]:
        """识别对立观点"""
        from ai_agent import generate_response
        
        existing_str = "\n".join([f"- {vp}" for vp in existing_vps[:5]])
        
        prompt = f"""分析讨论中的观点对立关系。

已有观点:
{existing_str}

讨论内容:
{discussion_text}

任务: 找出对现有观点形成对立/反驳的观点：

1. 检查是否有参与者明确表示反对某个观点
2. 检查是否有隐含的对立立场
3. 识别替代方案或不同的解决思路

对立观点列表 (最多2个):
1. [对立观点 1]
2. [对立观点 2]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        if not response:
            return []
        
        viewpoints = self._parse_numbered_list(response)
        return viewpoints[:2]
    
    def _extract_detail_viewpoints(self, discussion_text: str, existing_vps: List[str], llm_mode: str) -> List[str]:
        """提取关键细节观点"""
        from ai_agent import generate_response
        
        existing_str = "\n".join([f"- {vp}" for vp in existing_vps[:6]])
        
        prompt = f"""提取讨论中的关键细节观点。

已有观点:
{existing_str}

讨论内容:
{discussion_text}

任务: 找出补充现有观点的关键细节：

1. 参与者提出的具体影响或后果
2. 参与者建议的具体措施或条件
3. 参与者强调的限制条件或边界
4. 参与者引入的新维度或角度

细节观点 (最多1-2个):
1. [细节观点 1]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        if not response:
            return []
        
        viewpoints = self._parse_numbered_list(response)
        return viewpoints[:2]
    
    def _deduplicate_and_rank(self, viewpoints: List[str], discussion_text: str, llm_mode: str) -> List[str]:
        """智能去重、排序和评分"""
        from ai_agent import generate_response
        
        if len(viewpoints) <= 3:
            return viewpoints
        
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        prompt = f"""分析和排序这些观点。

观点列表:
{viewpoints_str}

讨论内容:
{discussion_text}

任务:
1. 合并完全相同或高度相似的观点
2. 按重要性排序（根据被提及次数、强调程度、影响范围）
3. 为每个观点打分 (1-10)
4. 只保留最重要的观点

输出格式:
MERGE: 2 and 5 as "[合并后的观点]" (Score: 9)
KEEP: 1 (Score: 9), 3 (Score: 8), 4 (Score: 7)
REMOVE: 6, 7

最终排序后的观点列表:
1. [最重要的观点]
2. [次重要的观点]"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        if not response:
            return viewpoints
        
        result = []
        
        # 提取合并的观点
        merge_matches = re.finditer(r'as\s+"([^"]+)"', response, re.IGNORECASE)
        for match in merge_matches:
            result.append(match.group(1))
        
        # 提取保留的观点
        keep_match = re.search(r'KEEP:\s*([^R]+?)(?:REMOVE|$)', response, re.IGNORECASE | re.DOTALL)
        if keep_match:
            keep_str = keep_match.group(1)
            keep_items = re.findall(r'(\d+)\s*\(', keep_str)
            for idx_str in keep_items:
                try:
                    idx = int(idx_str) - 1
                    if idx < len(viewpoints):
                        result.append(viewpoints[idx])
                except:
                    pass
        
        # 如果没有解析出来，返回原列表
        if not result:
            return viewpoints
        
        return result
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            match = re.match(r'^[\d]+[\.\)]\s+(.+)$', line)
            if match:
                item = match.group(1).strip()
                # 移除评分注释
                item = re.sub(r'\s*\(Score:\s*\d+\).*$', '', item)
                item = re.sub(r'\s*-\s*带着.*$', '', item)
                
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
        """多层级超强态度分析"""
        try:
            stances_dict = {p: {} for p in participants}
            
            print(f"\n{'='*60}")
            print(f"🔥 [超强态度分析] {len(participants)} 个参与者 × {len(viewpoints)} 个观点")
            print(f"{'='*60}")
            
            # 构建完整讨论上下文
            full_discussion = "\n".join([
                f"[{i+1}] {m.get('user')}: {m.get('message', '')}"
                for i, m in enumerate(messages)
            ])
            
            # 为每个参与者分析
            for participant in participants:
                print(f"\n👤 {participant}:")
                stances_dict[participant] = self._analyze_participant_stances_advanced(
                    participant,
                    messages,
                    viewpoints,
                    full_discussion,
                    llm_mode
                )
            
            print(f"\n{'='*60}")
            print(f"✅ 态度分析完成")
            print(f"{'='*60}\n")
            
            return stances_dict
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def _analyze_participant_stances_advanced(
        self,
        participant: str,
        messages: List[Dict],
        viewpoints: List[str],
        full_discussion: str,
        llm_mode: str
    ) -> Dict[str, str]:
        """多层级分析单个参与者"""
        from ai_agent import generate_response
        
        # 获取参与者的所有消息
        participant_msgs = [
            m.get('message', '')
            for m in messages
            if m.get('user') == participant and m.get('message', '')
        ]
        
        if not participant_msgs:
            # 未发言 -> 所有观点都是中立
            print(f"   (未发言) → 所有观点 △")
            return {vp: '△' for vp in viewpoints}
        
        participant_text = "\n".join(participant_msgs)
        viewpoints_str = "\n".join([f"{i+1}. {vp}" for i, vp in enumerate(viewpoints)])
        
        prompt = f"""你是一个高级文本分析师。使用多层级分析方法判断 {participant} 对每个观点的态度。

完整讨论过程:
{full_discussion}

所有观点:
{viewpoints_str}

{participant} 的发言:
{participant_text}

任务: 对每个观点进行多层级分析

【第 1 层】直接表述分析:
- 寻找显式的赞成/反对信号词（同意、反对、认为、应该等）

【第 2 层】隐含态度分析:
- 分析举例、比喻、反问是否隐含态度
- 检查修饰词（"虽然...但是..."结构表达真实态度）
- 识别反讽、讽刺等修辞手法

【第 3 层】上下文推理:
- 参与者的建议或方案隐含了什么态度？
- 参与者的担忧或疑虑隐含了什么态度？
- 结合 {participant} 之前的发言，态度是否一致？

【特殊规则】:
- 如果 {participant} 说"赞同上面的观点"→继承前发言人的态度
- 如果 {participant} 补充或扩展观点→对该观点 ✅
- 如果 {participant} 提出条件或限制→对该观点 △ (有保留)
- 如果 {participant} 强烈反对→❌

输出格式 (CSV):
viewpoint_number,stance,confidence,reasoning

例如:
1,✅,95,直接说同意
2,△,70,有条件同意
3,❌,85,明确反对

分析结果:"""
        
        response = generate_response(llm_mode, prompt, group_id="system", user="System")
        
        if not response:
            return {vp: '△' for vp in viewpoints}
        
        # 解析结果
        stances = {}
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or ',' not in line:
                continue
            
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                try:
                    vp_num = int(parts[0]) - 1
                    stance_char = parts[1]
                    
                    # 提取第一个有效的态度符号
                    stance = '△'
                    for char in stance_char:
                        if char in ['✅', '❌', '△']:
                            stance = char
                            break
                    
                    if vp_num < len(viewpoints):
                        vp = viewpoints[vp_num]
                        stances[vp] = stance
                        
                        # 显示分析结果
                        emoji = "✅" if stance == "✅" else ("❌" if stance == "❌" else "△")
                        print(f"   {vp[:25]}... → {emoji}")
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