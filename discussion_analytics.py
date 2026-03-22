import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def extract_claims_with_llm(messages, api_key=None):
    """
    使用 LLM 从讨论消息中动态提取核心论点/观点
    
    Args:
        messages: 讨论消息列表，每条消息格式为 {"user": "name", "message": "content", ...}
        api_key: OpenAI API key (可选，默认从环境变量读取)
    
    Returns:
        list: 4-5个核心观点列表，每个观点 10-20 字符
    """
    
    # 如果没有足够的消息，返回默认值
    if not messages or len(messages) < 3:
        return ["Claim A", "Claim B", "Claim C"]
    
    try:
        import openai
    except ImportError:
        print("⚠️ OpenAI library not installed, using fallback extraction")
        return extract_claims_fallback(messages)
    
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ No OpenAI API key found, using fallback extraction")
        return extract_claims_fallback(messages)
    
    # 准备讨论文本
    discussion_text = "\n".join([
        f"{msg.get('user', 'Unknown')}: {msg.get('message', '')}"
        for msg in messages
    ])
    
    # 限制长度以节省token
    if len(discussion_text) > 3000:
        discussion_text = discussion_text[:3000]
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in analyzing group discussions. Extract 3-4 core claims or viewpoints from the discussion. Each claim should be concise (10-20 characters max), clear, and capture the main perspectives shared."
                },
                {
                    "role": "user",
                    "content": f"""Analyze this discussion and extract the core claims/viewpoints:

{discussion_text}

Return ONLY a JSON array of 3-4 claims in this format:
["Claim 1", "Claim 2", "Claim 3"]

Each claim should be concise (10-20 characters) and in the same language as the discussion."""
                }
            ],
            temperature=0.5,
            max_tokens=150
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 解析 JSON 响应
        import json
        claims = json.loads(response_text)
        
        # 验证和清理
        claims = [str(c)[:25] for c in claims if c]  # 确保每个字符串不超过25字符
        
        return claims if len(claims) >= 3 else extract_claims_fallback(messages)
    
    except Exception as e:
        print(f"⚠️ LLM extraction failed: {e}, using fallback")
        return extract_claims_fallback(messages)


def extract_claims_fallback(messages):
    """
    备用方案：基于关键词的简单观点提取
    """
    claims = set()
    
    for msg in messages:
        text = msg.get("message", "").lower()
        
        # 检查包含"观点"、"认为"等关键词的句子
        if any(kw in text for kw in ['观点', '认为', '支持', '反对', '应该', 'should', 'believe', 'think']):
            # 简单分句
            sentences = msg.get("message", "").split("。")
            for sent in sentences:
                if len(sent) > 5 and len(sent) < 50:
                    if any(kw in sent.lower() for kw in ['观点', '认为', '支持', '反对', '应该']):
                        claims.add(sent.strip())
    
    # 转换为列表，并缩短
    claims_list = list(claims)[:4]
    
    # 如果提取不到足够的，使用默认值
    if len(claims_list) < 3:
        claims_list = ["观点A", "观点B", "观点C"]
    
    # 截断长文本
    claims_list = [c[:25] + "..." if len(c) > 25 else c for c in claims_list]
    
    return claims_list


def analyze_stance_on_claim(messages, participant, claim):
    """
    分析特定参与者对某个论点的立场
    
    Args:
        messages: 讨论消息列表
        participant: 参与者名字
        claim: 论点文本
    
    Returns:
        str: "agree" / "disagree" / "neutral"
    """
    
    # 获取该参与者的所有消息
    participant_msgs = [m.get("message", "").lower() for m in messages if m.get("user") == participant]
    combined_text = " ".join(participant_msgs)
    
    if not combined_text:
        return "neutral"
    
    # 赞成的关键词
    agree_keywords = ['赞成', '同意', '支持', '对', 'agree', 'yes', '+1', 'absolutely', 'definitely', '确实', '有道理']
    # 反对的关键词
    disagree_keywords = ['反对', '不同意', '反驳', 'disagree', 'no', '-1', 'no way', '不对', '错误', '不然']
    
    # 简单匹配
    agree_count = sum(1 for kw in agree_keywords if kw in combined_text)
    disagree_count = sum(1 for kw in disagree_keywords if kw in combined_text)
    
    if agree_count > disagree_count:
        return "agree"
    elif disagree_count > agree_count:
        return "disagree"
    else:
        return "neutral"