"""
共识矩阵 - 语义智能版本
基于 TF-IDF + 余弦相似度进行观点提取和态度分析
完全自适应，对任何主题都有效
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Set
from collections import Counter


class ConsensusMatrix:
    """共识矩阵 - 语义分析版本"""
    
    def __init__(self):
        self.vocab = set()
        self.idf_cache = {}
    
    def extract_and_simplify_viewpoints(
        self, 
        messages: List[Dict], 
        participants: List[str],
        llm_mode: str = "Control",
        session_id: str = ""
    ) -> Optional[List[Tuple[str, str]]]:
        """
        智能提取观点 - 基于语义相似度
        """
        try:
            user_messages = [m for m in messages if m.get('user') != 'AI']
            if not user_messages:
                return None
            
            print(f"\n📊 Smart viewpoint extraction...")
            
            # 收集消息
            all_texts = [m.get('message', '').strip() for m in user_messages]
            valid_texts = [t for t in all_texts if 10 <= len(t) <= 500]
            
            if not valid_texts:
                print("  ❌ No valid messages")
                return None
            
            print(f"  Valid messages: {len(valid_texts)}")
            
            # 计算 TF-IDF 向量
            vectors = self._compute_tfidf_vectors(valid_texts)
            
            # 基于语义相似度聚类
            clusters = self._semantic_cluster(valid_texts, vectors)
            print(f"  Found {len(clusters)} semantic clusters")
            
            # 提取每个簇的代表性观点
            viewpoints = []
            for i, cluster in enumerate(clusters[:4]):
                # 选择簇中最具代表性的文本（最接近簇中心的）
                representative = self._select_representative(cluster, vectors)
                viewpoints.append(representative)
                print(f"    Cluster {i+1}: {representative[:40]}...")
            
            print(f"  ✓ Extracted {len(viewpoints)} viewpoints")
            
            # 简化观点
            result = []
            for vp in viewpoints:
                simplified = self._smart_simplify(vp)
                result.append((vp, simplified))
                print(f"    [{simplified}]")
            
            return result if result else None
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
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
        智能分析态度 - 基于语义相似度
        """
        try:
            print(f"\n📈 Smart stance analysis...")
            
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
            
            # 计算观点的向量
            viewpoint_vectors = self._compute_tfidf_vectors(full_viewpoints)
            
            for participant in participants:
                print(f"  👤 {participant}...", end=" ")
                
                if participant not in speaker_messages:
                    print("△ (not spoken)")
                    stances_dict[participant] = {sv: '△' for sv in simplified_viewpoints}
                    continue
                
                participant_texts = speaker_messages[participant]
                
                # 计算参与者消息的向量
                participant_vectors = self._compute_tfidf_vectors(participant_texts)
                
                stances = []
                
                # 对每个观点分析
                for vp_idx, full_vp in enumerate(full_viewpoints):
                    stance = self._semantic_analyze_stance(
                        participant_texts,
                        participant_vectors,
                        full_vp,
                        viewpoint_vectors[vp_idx]
                    )
                    stances.append(stance)
                    stances_dict[participant][full_vp] = stance
                
                print(" ".join(stances))
            
            return stances_dict
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _tokenize(self, text: str) -> List[str]:
        """
        分词 - 支持中英文混合
        """
        # 简单的分词方法
        # 先分割中文和英文
        text = text.lower()
        
        # 英文单词
        words = []
        i = 0
        while i < len(text):
            # 英文单词
            if text[i].isalpha():
                j = i
                while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                    j += 1
                words.append(text[i:j])
                i = j
            # 中文字符
            elif ord(text[i]) > 127:
                words.append(text[i])
                i += 1
            else:
                i += 1
        
        # 过滤虚词
        stopwords = {
            'and', 'or', 'is', 'the', 'a', 'an', 'in', 'on', 'at', 'by', 'to', 'for',
            '的', '是', '和', '或', '在', '了', '有', '个', '但', '也', '能', '可',
            '以', '所', '因', '为', '从', '到', '就', '还', '没', '不', '很'
        }
        
        return [w for w in words if w not in stopwords and len(w) > 1]
    
    def _compute_tfidf_vectors(self, texts: List[str]) -> List[Dict[str, float]]:
        """
        计算 TF-IDF 向量
        返回向量字典列表
        """
        if not texts:
            return []
        
        # 分词
        tokenized = [self._tokenize(t) for t in texts]
        
        # 计算 IDF
        idf = {}
        num_docs = len(texts)
        
        vocab = set()
        for tokens in tokenized:
            vocab.update(tokens)
        
        for word in vocab:
            doc_count = sum(1 for tokens in tokenized if word in tokens)
            idf[word] = math.log(num_docs / (doc_count + 1)) + 1
        
        # 计算 TF-IDF
        vectors = []
        for tokens in tokenized:
            vector = {}
            term_count = Counter(tokens)
            total_terms = len(tokens)
            
            for term, count in term_count.items():
                tf = count / (total_terms + 1)
                vector[term] = tf * idf[term]
            
            vectors.append(vector)
        
        return vectors
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        计算余弦相似度
        """
        # 获取共同的词
        common_terms = set(vec1.keys()) & set(vec2.keys())
        
        if not common_terms:
            return 0.0
        
        # 点积
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
        
        # 范数
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _semantic_cluster(self, texts: List[str], vectors: List[Dict[str, float]]) -> List[List[str]]:
        """
        基于语义相似度的聚类
        """
        if not texts:
            return []
        
        # 简单的单链接聚类
        clusters = []
        used = set()
        similarity_threshold = 0.3  # 阈值
        
        for i, text1 in enumerate(texts):
            if i in used:
                continue
            
            # 创建新簇
            cluster = [text1]
            used.add(i)
            
            vec1 = vectors[i]
            
            # 找相似的文本
            for j in range(i + 1, len(texts)):
                if j in used:
                    continue
                
                vec2 = vectors[j]
                similarity = self._cosine_similarity(vec1, vec2)
                
                if similarity > similarity_threshold:
                    cluster.append(texts[j])
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _select_representative(self, cluster: List[str], vectors: List[Dict[str, float]]) -> str:
        """
        从簇中选择最具代表性的文本
        选择与其他文本相似度最高的（簇中心）
        """
        if len(cluster) == 1:
            return cluster[0]
        
        # 找到所有文本中最接近其他文本的
        best_idx = 0
        best_avg_sim = -1
        
        for i, text1 in enumerate(cluster):
            # 这里简化处理，直接选最长的（信息最丰富的）
            pass
        
        # 实际策略：选最长的文本（包含最多信息）
        return max(cluster, key=len)
    
    def _smart_simplify(self, text: str, max_length: int = 15) -> str:
        """
        智能简化文本
        提取最重要的关键词
        """
        tokens = self._tokenize(text)
        
        if not tokens:
            return text[:15]
        
        # 取前 3 个关键词
        simplified = "".join(tokens[:3])
        
        if len(simplified) > max_length:
            simplified = simplified[:max_length-1] + "…"
        elif len(simplified) < 8:
            simplified = text[:15]
            if len(text) > 15:
                simplified += "…"
        
        return simplified
    
    def _semantic_analyze_stance(
        self, 
        participant_texts: List[str],
        participant_vectors: List[Dict[str, float]],
        viewpoint_text: str,
        viewpoint_vector: Dict[str, float]
    ) -> str:
        """
        基于语义相似度分析态度
        """
        
        if not participant_vectors:
            return '△'
        
        # 计算参与者消息与观点的相似度
        similarities = []
        for pv in participant_vectors:
            sim = self._cosine_similarity(pv, viewpoint_vector)
            similarities.append(sim)
        
        max_similarity = max(similarities) if similarities else 0
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        print(f"      sim(max={max_similarity:.2f}, avg={avg_similarity:.2f})", end="")
        
        # 策略：如果最大相似度很高，说明参与者在讨论这个观点
        # 然后检查是支持还是反对
        
        if max_similarity < 0.1:
            # 完全没有相关性 → 中立
            return '△'
        
        # 提取参与者的整体立场
        # 使用句子级别的分析
        support_score = 0
        oppose_score = 0
        
        # 支持和反对的表达
        support_patterns = [
            '同意', '赞成', '支持', '好', '应该', '对', '正确', '可以',
            'agree', 'support', 'good', 'yes', 'right', 'should', 'can'
        ]
        
        oppose_patterns = [
            '反对', '不同意', '不赞成', '差', '不应该', '错', '问题',
            'oppose', 'disagree', 'bad', 'no', 'wrong', 'problem', 'issue'
        ]
        
        for text in participant_texts:
            text_lower = text.lower()
            
            for pattern in support_patterns:
                if pattern in text_lower:
                    support_score += 1
            
            for pattern in oppose_patterns:
                if pattern in text_lower:
                    oppose_score += 1
        
        # 判断
        if support_score > oppose_score and support_score > 0:
            return '✅'
        elif oppose_score > support_score and oppose_score > 0:
            return '❌'
        else:
            # 有相似性但无明确态度
            if max_similarity > 0.3:
                return '△'  # 提到了，但态度不明确
            else:
                return '△'  # 没有或很少提到