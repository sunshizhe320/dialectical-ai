"""
discourse_analysis.py (增強版)
自動偵測對話中的批判性思維指標（Discourse Moves）
包括：Questions, Counterarguments, Evidence, Clarifications, Agreements
"""
import re

class DiscourseAnalyzer:
    def __init__(self):
        """
        定義各類指標的關鍵詞與 patterns
        """
        
        # ===== 提問（Questions） =====
        # 包括：直接問號、疑問詞、委婉提問
        self.question_patterns = [
            r'[？?]',  # 問號
            r'\?$',  # 英文問號
            r'為什麼|為何|如何|怎樣|怎麼|能否|是否|有沒有|會不會',
            r'你覺得|你認為|你想|你覺',
            r'什麼時候|什麼地方|什麼原因|什麼情況',
            r'可以|可否|得不得|行不行',
            # 英文
            r'what|why|how|when|where|which|who|whom',
            r'can you|could you|would you|should you|do you|does|will you',
            r'is|are|am|have|has|did|do',
            r'\?'
        ]
        
        # ===== 反駁 / 挑戰（Counterarguments） =====
        # 包括：轉折詞、否定、挑戰、替代觀點
        self.counterargument_patterns = [
            # 轉折與否定
            r'但是|但|然而|不過|相反|反之|反而|恰恰相反|卻|可是',
            r'我不同意|我反對|我持反對意見|這不對|這不正確',
            r'不一定|不全是|並非|並不是|存疑|有異議|有問題',
            r'不能|沒有|無法|無所謂|不成立',
            # 挑戰與替代
            r'反例|反面例子|相反的例子|我想提出',
            r'另一方面|換個角度|換句話說|從另一個角度看',
            r'你有沒有想過|你有沒有考慮|你忽略了',
            r'這樣的話|這樣的邏輯|這個論點',
            # 英文
            r'but|however|on the other hand|instead|rather|contrary',
            r'disagree|oppose|challenge|object|counter|against',
            r'not|no|never|cannot|doesn\'t|isn\'t|aren\'t|didn\'t',
            r'on the contrary|conversely|nevertheless|yet'
        ]
        
        # ===== 證據 / 例子（Evidence） =====
        # 包括：例子、數據、研究、事實、引用
        self.evidence_patterns = [
            # 例子與案例
            r'例如|舉例|比如|例子|實例|案例|實際上|事實上',
            r'比方說|比方|譬如|具體來說|具體的例子',
            # 數據與研究
            r'根據|據說|數據|統計|調查|研究|結果|發現|發現',
            r'報告|報告顯示|報告指出|顯示|指出|證明|驗證',
            r'有研究|有調查|有人|有專家|根據研究',
            # 事實與權威
            r'事實|實際|真實|真的|確實|肯定|證實',
            r'權威|專家|學者|科學|科學家|醫生|教授',
            # 英文
            r'for example|for instance|such as|like|according to',
            r'research|study|data|statistics|survey|findings|show|indicate',
            r'evidence|proof|demonstrated|shows|found that',
            r'expert|professor|scientist|study shows|research indicates'
        ]
        
        # ===== 澄清 / 確認（Clarifications） =====
        # 包括：重述、確認、解釋、簡化
        self.clarification_patterns = [
            # 重述與簡化
            r'換句話說|也就是說|換言之|簡單說|簡言之|也就是',
            r'就是|即|是指|意思是|意味著|代表',
            r'總結|總之|一句話|核心是|關鍵是',
            # 確認與提問
            r'你是說|你的意思是|你指的是|對吧|是嗎|沒錯|對不對',
            r'我沒理解錯吧|我理解得沒錯吧|這樣理解對嗎',
            r'澄清|明確|確認|確定|確實',
            # 解釋
            r'因為|所以|由於|因此|既然|既然這樣',
            r'解釋|說明|闡述|詳細說|具體說',
            # 英文
            r'in other words|that is|that is to say|in short|simply put',
            r'clarify|clarification|to clarify|to be clear|correct me if',
            r'you mean|you\'re saying|right|correct|am i right',
            r'so|therefore|thus|because|since|that\'s why'
        ]
        
        # ===== 贊同 / 補充（Agreements） =====
        # 包括：同意、支持、補充、建立
        self.agreement_patterns = [
            r'我同意|我贊成|你說得對|沒錯|對|完全同意',
            r'這個想法|這個觀點|你的論點|你的看法',
            r'還有|另外|補充|進一步|進一步說|延伸',
            r'這方面|這個角度|這個面向|值得一提',
            r'同時|此外|而且|另一方面|不僅|不只',
            # 英文
            r'agree|yes|right|exactly|definitely|absolutely',
            r'support|point|idea|good idea|true',
            r'also|furthermore|moreover|additionally|in addition'
        ]

    def analyze_message(self, message, verbose=False):
        """
        分析單一訊息，回傳該訊息包��的指標
        verbose=True 時回傳匹配的具體模式（用於調試）
        回傳格式：{"questions": 0/1, "counterarguments": 0/1, "evidence": 0/1, "clarifications": 0/1, "agreements": 0/1}
        """
        result = {
            "questions": 0,
            "counterarguments": 0,
            "evidence": 0,
            "clarifications": 0,
            "agreements": 0
        }
        
        # 用於 debug 的匹配詳情
        matches = {
            "questions": [],
            "counterarguments": [],
            "evidence": [],
            "clarifications": [],
            "agreements": []
        }
        
        msg_lower = message.lower()
        
        # 檢查各類指標
        if self._contains_pattern(msg_lower, self.question_patterns):
            result["questions"] = 1
            if verbose:
                matches["questions"] = self._get_matching_patterns(msg_lower, self.question_patterns)
        
        if self._contains_pattern(msg_lower, self.counterargument_patterns):
            result["counterarguments"] = 1
            if verbose:
                matches["counterarguments"] = self._get_matching_patterns(msg_lower, self.counterargument_patterns)
        
        if self._contains_pattern(msg_lower, self.evidence_patterns):
            result["evidence"] = 1
            if verbose:
                matches["evidence"] = self._get_matching_patterns(msg_lower, self.evidence_patterns)
        
        if self._contains_pattern(msg_lower, self.clarification_patterns):
            result["clarifications"] = 1
            if verbose:
                matches["clarifications"] = self._get_matching_patterns(msg_lower, self.clarification_patterns)
        
        if self._contains_pattern(msg_lower, self.agreement_patterns):
            result["agreements"] = 1
            if verbose:
                matches["agreements"] = self._get_matching_patterns(msg_lower, self.agreement_patterns)
        
        if verbose:
            result["matches"] = matches
        
        return result

    def _contains_pattern(self, text, patterns):
        """檢查文本是否包含任何一個 pattern"""
        for pattern in patterns:
            try:
                if re.search(pattern, text):
                    return True
            except re.error:
                continue
        return False

    def _get_matching_patterns(self, text, patterns):
        """回傳所有匹配的 pattern（用於調試）"""
        matches = []
        for pattern in patterns:
            try:
                if re.search(pattern, text):
                    match = re.search(pattern, text).group(0)
                    matches.append(match)
            except re.error:
                continue
        return matches

    def analyze_history(self, history_list, verbose=False):
        """
        分析整個對話歷史
        history_list: [{"user": "...", "role": "...", "message": "...", "timestamp": "..."}, ...]
        verbose=True 時回傳詳細的每條訊息分析
        回傳：{
            "questions": count, 
            "counterarguments": count, 
            "evidence": count, 
            "clarifications": count,
            "agreements": count,
            "user_messages": count, 
            "ai_messages": count,
            "detailed": [...]  # 若 verbose=True
        }
        """
        stats = {
            "questions": 0,
            "counterarguments": 0,
            "evidence": 0,
            "clarifications": 0,
            "agreements": 0,
            "user_messages": 0,
            "ai_messages": 0,
            "detailed": []
        }
        
        for h in history_list:
            role = h.get("role", "")
            message = h.get("message", "")
            user = h.get("user", "")
            
            # 判斷是否為 user 訊息（不計 AI 回覆）
            is_user_msg = role == "user" or (role != "assistant" and user != "AI")
            
            # 計數訊息
            if is_user_msg:
                stats["user_messages"] += 1
            else:
                stats["ai_messages"] += 1
            
            # 只分析 user 的訊息（不分析 AI 回覆）
            if is_user_msg:
                indicators = self.analyze_message(message, verbose=verbose)
                stats["questions"] += indicators["questions"]
                stats["counterarguments"] += indicators["counterarguments"]
                stats["evidence"] += indicators["evidence"]
                stats["clarifications"] += indicators["clarifications"]
                stats["agreements"] += indicators["agreements"]
                
                # 若 verbose，儲存詳細資訊
                if verbose:
                    detail_entry = {
                        "user": user,
                        "message": message,
                        "indicators": {k: v for k, v in indicators.items() if k != "matches"},
                        "matches": indicators.get("matches", {})
                    }
                    stats["detailed"].append(detail_entry)
                else:
                    # 非 verbose 模式：只儲存指標
                    detail_entry = {
                        "user": user,
                        "message": message,
                        "indicators": indicators
                    }
                    stats["detailed"].append(detail_entry)
        
        return stats

# 方便快速使用
analyzer = DiscourseAnalyzer()