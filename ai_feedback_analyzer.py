"""
AI维度分析模块
自动为用户消息添加：Related/Additional/Challenge + ✓/×/△ 标签
"""

import json
from ai_agent import _call_kimi_api

def analyze_message_dimension(message, conversation_history=None, topic=""):
    """
    调用AI分析消息的维度
    
    返回: {
        'type': 'Related' | 'Additional' | 'Challenge',
        'verdict': '✓' | '×' | '△',
        'confidence': 0.85,
        'reasoning': '简短说明'
    }
    """
    
    # 构建上下文
    context = ""
    if conversation_history:
        context = "\n前置讨论:\n"
        for msg in conversation_history[-3:]:  # 只取最近3条
            context += f"- {msg['user']}: {msg['message'][:100]}\n"
    
    prompt = f"""你是一个讨论质量分析器。分析以下用户发言在讨论中的维度：

【讨论主题】
{topic}

【前置讨论】
{context}

【当前发言】
"{message}"

请判断这条发言属于哪个维度，并评估其观点的严密性。

维度说明：
- Related: 与已有论点相关，补充或深化现有观点
- Additional: 引入全新视角、证据或论证角度
- Challenge: 直接质疑或反对已有观点

返回JSON（只返回JSON，无其他文字）:
{{
    "type": "Related|Additional|Challenge",
    "verdict": "✓|×|△",
    "confidence": 0.95,
    "reasoning": "这条发言XX，属于XX维度，观点XX"
}}

说明：
- verdict: ✓=观点严密有据, ×=观点有逻辑漏洞, △=观点可接受但不够深入
- confidence: 分析的置信度(0-1)
"""
    
    try:
        response = _call_kimi_api(
            system_prompt="你是讨论质量分析专家。准确分析用户观点的维度和质量。",
            user_message=prompt,
            max_tokens=300
        )
        
        # 解析JSON
        result = json.loads(response)
        return result
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return {
            'type': 'Related',
            'verdict': '△',
            'confidence': 0.5,
            'reasoning': '分析服务暂时不可用'
        }
    except Exception as e:
        print(f"❌ AI分析失败: {e}")
        return None


def batch_analyze_messages(messages, session_id, topic=""):
    """
    批量分析已有消息（用于更新现存讨论）
    
    性能优化：
    - 只分析用户消息（跳过AI消息）
    - 缓存结果到本地
    """
    
    from pathlib import Path
    import json
    
    cache_file = f"ai_feedback_cache_{session_id}.json"
    
    # 尝试加载缓存
    if Path(cache_file).exists():
        with open(cache_file, 'r') as f:
            cache = json.load(f)
    else:
        cache = {}
    
    results = {}
    new_analyses = 0
    
    for msg in messages:
        if msg['user'] == 'AI':
            continue
        
        msg_id = f"{msg['timestamp']}_{msg['user']}"
        
        # 检查缓存
        if msg_id in cache:
            results[msg_id] = cache[msg_id]
            continue
        
        # 调用AI分析
        analysis = analyze_message_dimension(
            msg['message'],
            conversation_history=messages,
            topic=topic
        )
        
        if analysis:
            results[msg_id] = analysis
            cache[msg_id] = analysis
            new_analyses += 1
    
    # 保存缓存
    with open(cache_file, 'w') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 分析完成：{new_analyses}条新分析，{len(cache)-new_analyses}条缓存命中")
    
    return results, cache