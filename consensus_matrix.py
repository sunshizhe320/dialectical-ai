"""
共识矩阵 - 改进版本
更精准的态度分析
"""

import re
import math
from typing import Dict, List, Tuple, Optional
from collections import Counter


class ConsensusMatrix:
    """共识矩阵 - 改进的语义分析版本"""
    
    def __init__(self):
        pass
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[List[Tuple[str, str]]]:
        """提取观点"""
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 Smart viewpoint extraction...")
            
            all_texts = [m.get('message', '').strip() for m in user_messages]
            valid_texts = [t for t in all_texts if 10 <= len(t) <= 500]
            
            if not valid_texts:
                print("  ❌ No valid messages")
                return None
            
            print(f"  Valid messages: {len(valid_texts)}")
            
            # 基于词汇相似度聚类
            clusters = self._simple_cluster(valid_texts)
            print(f"  Found {len(clusters)} clusters")
            
            viewpoints = []
            for cluster in clusters[:4]:
                representative = max(cluster, key=len)
                viewpoints.append(representative)
                print(f"    {representative[:40]}...")
            
            result = []
            for vp in viewpoints:
                simplified = self._smart_simplify(vp)
                result.append((vp, simplified))
            
            return result if result else None
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
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
        分析态度 - 改进版本
        """
        try:
            print(f"\n📈 Smart stance analysis...")
            
            stances_dict = {p: {} for p in participants}
            
            speaker_messages = {}
            for m in messages:
                user = m.get('user')
                if user and user != 'AI':
                    if user not in speaker_messages:
                        speaker_messages[user] = []
                    speaker_messages[user].append(m.get('message', ''))
            
            full_viewpoints = [vp[0] for vp in viewpoints_pairs]
            simplified_viewpoints = [vp[1] for vp in viewpoints_pairs]
            
            print(f"  Analyzing {len(full_viewpoints)} viewpoints for {len(participants)} participants")
            
            for participant in participants:
                print(f"  👤 {participant}:", end=" ")
                
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_texts = speaker_messages[participant]
                stances = []
                
                # 对每个观点分析
                for vp_idx, full_vp in enumerate(full_viewpoints):
                    stance = self._improved_analyze_stance(
                        participant_texts,
                        full_vp,
                        participant
                    )
                    stances.append(stance)
                    stances_dict[participant][full_vp] = stance
                    print(stance, end=" ")
                
                print()
            
            return stances_dict
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        
        words = []
        i = 0
        while i < len(text):
            if text[i].isalpha() or text[i].isdigit():
                j = i
                while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                    j += 1
                words.append(text[i:j])
                i = j
            elif ord(text[i]) > 127:
                words.append(text[i])
                i += 1
            else:
                i += 1
        
        stopwords = {
            'and', 'or', 'is', 'the', 'a', 'an', 'in', 'on', 'at', 'by', 'to', 'for',
            '的', '是', '和', '或', '在', '了', '有', '个', '但', '也', '能', '可',
            '以', '所', '因', '为', '从', '到', '就', '还', '没', '不', '很', '被'
        }
        
        return [w for w in words if w not in stopwords and len(w) > 1]
    
    def _simple_cluster(self, texts: List[str]) -> List[List[str]]:
        """简单聚类"""
        clusters = []
        used = set()
        
        for i, text1 in enumerate(texts):
            if i in used:
                continue
            
            cluster = [text1]
            used.add(i)
            
            words1 = set(self._tokenize(text1))
            
            for j in range(i + 1, len(texts)):
                if j in used:
                    continue
                
                text2 = texts[j]
                words2 = set(self._tokenize(text2))
                
                if len(words1) > 0 and len(words2) > 0:
                    intersection = len(words1 & words2)
                    union = len(words1 | words2)
                    similarity = intersection / union
                    
                    if similarity > 0.25:
                        cluster.append(text2)
                        used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _smart_simplify(self, text: str) -> str:
        """简化文本"""
        tokens = self._tokenize(text)
        
        if not tokens:
            return text[:15]
        
        simplified = "".join(tokens[:3])
        
        if len(simplified) > 15:
            simplified = simplified[:12] + "…"
        elif len(simplified) < 8:
            simplified = text[:15]
            if len(text) > 15:
                simplified += "…"
        
        return simplified
    
    def _improved_analyze_stance(
        self,
        participant_texts: List[str],
        viewpoint: str,
        participant_name: str = ""
    ) -> str:
        """
        改进的态度分析
        步骤：
        1. 检查参与者是否在讨论这个观点
        2. 分析整体表态（支持/反对）
        3. 处理否定表达
        4. 多维度评分
        """
        
        vp_tokens = set(self._tokenize(viewpoint))
        
        if not vp_tokens:
            return '△'
        
        # 步骤 1：检查相关性
        mention_count = 0
        supporting_sentences = 0
        opposing_sentences = 0
        
        for text in participant_texts:
            text_lower = text.lower()
            text_tokens = set(self._tokenize(text))
            
            # 检查是否提到观点相关内容
            overlap = len(vp_tokens & text_tokens)
            if overlap > 0:
                mention_count += overlap
                
                # 分句分析
                sentences = self._split_sentences(text)
                
                for sentence in sentences:
                    sent_lower = sentence.lower()
                    sent_tokens = set(self._tokenize(sentence))
                    
                    # 句子中的观点词汇覆盖
                    sent_overlap = len(vp_tokens & sent_tokens)
                    
                    if sent_overlap > 0:
                        # 判断这句话的态度
                        stance = self._sentence_stance(sent_lower)
                        
                        if stance == 'support':
                            supporting_sentences += 1
                        elif stance == 'oppose':
                            opposing_sentences += 1
        
        print(f"\n      [Debug] mention={mention_count}, support={supporting_sentences}, oppose={opposing_sentences}")
        
        # 步骤 2：决策
        if mention_count == 0:
            # 完全没提到
            return '△'
        
        # 有提到观点
        if supporting_sentences > opposing_sentences:
            return '✅'
        elif opposing_sentences > supporting_sentences:
            return '❌'
        else:
            # 中立或未明确表态
            return '△'
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        分句 - 支持中英文
        """
        # 中文句号、英文句号等
        sentences = re.split(r'[。！？；：,.;!?]', text)
        
        # 过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences if sentences else [text]
    
    def _sentence_stance(self, sentence: str) -> str:
        """
        ��析单个句子的态度
        """
        
        # 强支持表达
        strong_support = {
            '同意': 3, '赞成': 3, '支持': 3, '好': 2, '很好': 3, '优秀': 3,
            '有帮助': 2, '有利': 2, '改善': 2, '进步': 2, '正确': 2, '应该': 2,
            'agree': 3, 'support': 3, 'good': 2, 'yes': 2, 'right': 2,
            'beneficial': 2, 'improve': 2, 'positive': 2, 'helpful': 2
        }
        
        # 强反对表达
        strong_oppose = {
            '反对': 3, '不同意': 3, '不赞成': 3, '差': 2, '不好': 2, '问题': 2,
            '困难': 2, '不对': 2, '错误': 3, '有害': 3, '不应该': 2,
            'oppose': 3, 'disagree': 3, 'bad': 2, 'no': 2, 'wrong': 3,
            'problem': 2, 'difficult': 2, 'harmful': 3, 'negative': 2
        }
        
        # 否定词
        negation = {'不', '没', '无', '没有', '不是', '不能', 'not', 'no', 'can\'t', 'don\'t', 'no'}
        
        support_score = 0
        oppose_score = 0
        has_negation = any(neg in sentence for neg in negation)
        
        # 计分
        for word, weight in strong_support.items():
            count = sentence.count(word)
            if count > 0:
                if has_negation:
                    # "不是很好" 或 "没有好处" - 反对
                    oppose_score += count * weight
                else:
                    support_score += count * weight
        
        for word, weight in strong_oppose.items():
            count = sentence.count(word)
            if count > 0:
                if has_negation:
                    # "不反对" - 支持
                    support_score += count * weight
                else:
                    oppose_score += count * weight
        
        # 判断
        if support_score > oppose_score:
            return 'support'
        elif oppose_score > support_score:
            return 'oppose'
        else:
            return 'neutral'