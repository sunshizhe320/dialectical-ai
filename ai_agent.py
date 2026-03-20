"""
ai_agent.py
AI 回复生成模块 - Kimi (Moonshot) API
"""
import os
import re
import random
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取 API Key
MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")

# 如果本地没有，尝试从 Streamlit Secrets 获取
if not MOONSHOT_KEY:
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY")
    except:
        pass

DEBUG_MODE = True

# 启动时打印 API Key 状态
if DEBUG_MODE:
    print(f"\n{'='*80}")
    print(f"[🔑 API 初始化]")
    if MOONSHOT_KEY:
        print(f"✅ MOONSHOT_API_KEY 已加载 ({len(MOONSHOT_KEY)} 字符)")
        print(f"   前缀: {MOONSHOT_KEY[:15]}...")
    else:
        print(f"❌ MOONSHOT_API_KEY 未找到！")
    print(f"{'='*80}\n")


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """生成 AI 回复"""
    
    if mode == "Control":
        return "（此为控制组，不提供 AI 干预）"
    
    # 检查 API Key
    if not MOONSHOT_KEY:
        error_msg = "❌ API Key 未配置。请在 Streamlit Cloud Secrets 中设置 MOONSHOT_API_KEY"
        if DEBUG_MODE:
            print(f"[❌ 错误] {error_msg}")
        return error_msg
    
    system_prompt = custom_prompt or _get_default_prompt(mode)
    conversation_context = _build_conversation_context(conversation_history)
    
    # 调用 Kimi API
    response = _call_kimi_api(system_prompt, user_message, conversation_context)
    
    # 如果 API 失败，使用 Fallback
    if not response:
        if DEBUG_MODE:
            print(f"[⚠️ API 失败，使用 Fallback]")
        response = _get_fallback(mode)
    
    return response


def _build_conversation_context(history, max_messages=10):
    """构建对话背景"""
    if not history:
        return ""
    
    messages = []
    for h in history[-max_messages:]:
        user = h.get("user", "")
        msg = h.get("message", "")
        role = h.get("role", "")
        
        if role == "assistant" or user == "AI":
            messages.append(f"AI: {msg}")
        else:
            clean = msg.replace("@AI", "").replace("@ai", "").replace("＠AI", "").strip()
            messages.append(f"{user}: {clean}")
    
    return "\n".join(messages)


def _get_default_prompt(mode):
    """获取系统 Prompt"""
    if "Scaffolded" in mode:
        return (
            "你是一位杰出的苏格拉底式教师。\n"
            "你的角色是：\n"
            "1. 通过精妙的提问激发学生的批判性思维\n"
            "2. 从不直接给出答案，而是引导学生自己发现\n"
            "3. 基于学生的观点，提出有针对性的后续问题\n"
            "4. 每次给出不同角度的问题，避免重复\n"
            "你的提问应该简洁、有启发性。"
        )
    elif "Debater" in mode:
        return (
            "你是一位经验丰富的辩手和批判性思维导师。\n"
            "你的角色是：\n"
            "1. 基于学生的论点，提出有力的反对观点\n"
            "2. 用「但是」「相反」「我不同意」等词开头表达相反意见\n"
            "3. 给出具体的反例或替代解释\n"
            "4. 要求学生提供更有力的证据\n"
            "5. 保持尊重和建设性的态度"
        )
    return "你是一个有帮助的 AI 助手。"


def _call_kimi_api(system_prompt, user_message, context):
    """调用 Kimi (Moonshot) API"""
    
    try:
        if DEBUG_MODE:
            print(f"\n{'─'*80}")
            print(f"[📤 调用 Kimi API]")
            print(f"  API Key: {MOONSHOT_KEY[:20]}..." if MOONSHOT_KEY else "  API Key: 未设置")
            print(f"  用户消息: {user_message[:50]}...")
        
        # 构建请求
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_KEY}"
        }
        
        # 构建 Prompt
        full_prompt = system_prompt
        if context:
            full_prompt += f"\n\n【讨论背景】\n{context}"
        
        payload = {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        if DEBUG_MODE:
            print(f"  📝 请求数据: {len(str(payload))} 字节")
            print(f"  🔄 发送中...")
        
        # 发送请求
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if DEBUG_MODE:
            print(f"  ✓ 收到响应")
            print(f"  状态码: {response.status_code}")
        
        # 检查状态
        if response.status_code != 200:
            if DEBUG_MODE:
                print(f"  ❌ HTTP 错误 {response.status_code}")
                print(f"  响应: {response.text[:200]}")
            return None
        
        # 解析响应
        result = response.json()
        
        if DEBUG_MODE:
            print(f"  响应结构: {list(result.keys())}")
        
        # 提取内容
        if "choices" not in result:
            if DEBUG_MODE:
                print(f"  ❌ 响应中没有 'choices' 字段")
            return None
        
        if len(result["choices"]) == 0:
            if DEBUG_MODE:
                print(f"  ❌ choices 为空")
            return None
        
        choice = result["choices"][0]
        if "message" not in choice:
            if DEBUG_MODE:
                print(f"  ❌ choice 中没有 'message' 字段")
            return None
        
        message = choice["message"]
        if "content" not in message:
            if DEBUG_MODE:
                print(f"  ❌ message 中没有 'content' 字段")
            return None
        
        content = message["content"].strip()
        
        if not content:
            if DEBUG_MODE:
                print(f"  ❌ content 为空")
            return None
        
        if DEBUG_MODE:
            print(f"  ✅ 成功!")
            print(f"  内容长度: {len(content)} 字符")
            print(f"  内容: {content[:60]}...")
            print(f"{'─'*80}\n")
        
        return content
    
    except requests.exceptions.Timeout:
        if DEBUG_MODE:
            print(f"  ❌ 请求超时 (30秒)")
        return None
    except requests.exceptions.ConnectionError:
        if DEBUG_MODE:
            print(f"  ❌ 连接错误")
        return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ❌ 异常: {type(e).__name__}")
            print(f"  信息: {str(e)[:100]}")
        return None


def _get_fallback(mode):
    """Fallback 回复"""
    if "Scaffolded" in mode:
        options = [
            "你的思考很有趣。能进一步解释一下吗？",
            "这是个好问题。你认为最根本的原因是什么？",
            "有什么证据或例子能支持你的观点吗？",
            "从反面想，如果不是这样会怎样？",
            "你的观点基于什么假设？",
        ]
    elif "Debater" in mode:
        options = [
            "我理解你的立场，但我想从另一个角度看。",
            "这个观点有道理，但你有没有考虑过相反的情况？",
            "你的论证需要更强有力的证据。能提供吗？",
            "我不太同意这个判断。真的所有情况都这样吗？",
            "这个观点似乎过于绝对了。有没有例外？",
        ]
    else:
        options = [
            "你的想法很有意思。能继续说说吗？",
            "这是个值得思考的观点。",
            "你能举个例子来说明吗？",
        ]
    
    return random.choice(options)