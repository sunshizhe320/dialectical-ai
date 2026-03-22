"""
discourse_analysis.py (Updated)
增加了共识矩阵逻辑和贡献分类，对接手稿中的 1. (Related/Additional) 和 3. (矩阵)
"""

import json
from datetime import datetime

class DiscourseAnalyzer:
    def __init__(self):
        self.analysis_cache = {}

    def analyze_messages(self, messages):
        if not messages or len(messages) < 1:
            return {"status": "insufficient_data"}
        
        # 1. 提取参与者
        participants = list(self._extract_participants(messages).keys())
        
        # 2. 提取核心议题 (这里建议未来对接 LLM，目前先基于语义关键词模拟)
        # 假设我们从讨论中提取了几个关键争议点
        claims = self._extract_claims(messages)
        
        analysis = {
            "total_messages": len(messages),
            "participants": participants,
            # 新增：贡献分类 (对应手稿 Step 1: Related/Additional)
            "contributions": self._classify_all_contributions(messages),
            # 新增：共识矩阵数据 (对应手稿 Step 3: Matrix)
            "consensus_matrix": self._generate_matrix(participants, claims, messages),
            "timestamp": datetime.now().isoformat()
        }
        return analysis

    def _extract_claims(self, messages):
        """
        从对话中提取核心观点。
        毕业设计后期建议在这里调用 LLM 总结出 3-4 个核心议题。
        """
        # 示例：根据当前话题动态生成的 Mock 议题
        return [
            "算法导致信息茧房",
            "算法加剧了情绪化表达",
            "个人用户应承担主要责任"
        ]

    def _classify_all_contributions(self, messages):
        """
        对应手稿：判断是 Related (针对他人) 还是 Additional (新观点)
        """
        results = []
        for i, msg in enumerate(messages):
            content = msg.get('message', '')
            # 简单逻辑：如果包含回复语气或提及他人，设为 Related
            is_related = any(word in content for word in ["同意", "觉得", "但是", "针对", "回复"])
            tag = "Related" if (is_related and i > 0) else "Additional"
            results.append({"user": msg.get('user'), "tag": tag})
        return results

    def _generate_matrix(self, participants, claims, messages):
        """
        生成手稿中的勾选矩阵 (Row: Participant, Col: Claim)
        返回值格式示例: {"Amber": [True, False, None], ...}
        """
        matrix = {}
        for p in participants:
            user_stances = []
            user_text = " ".join([m.get('message', '') for m in messages if m.get('user') == p])
            
            for claim in claims:
                # 这里使用简单的关键词匹配来判断勾选(True)还是叉号(False)
                # 实际项目中这里是 LLM 判断的结果
                if any(word in user_text for word in ["同意", "确实", "支持", "是的"]):
                    user_stances.append(True)  # 对应勾选 √
                elif any(word in user_text for word in ["不认为", "反对", "但是", "不同意"]):
                    user_stances.append(False) # 对应叉号 X
                else:
                    user_stances.append(None)  # 对应未表态
            matrix[p] = user_stances
        return {"claims": claims, "data": matrix}

    # ... 保留原有的 _extract_participants 等基础统计方法 ...