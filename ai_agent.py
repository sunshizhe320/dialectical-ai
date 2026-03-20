"""
ai_agent.py
AI 回复生成模块 - 支持 Kimi / Qwen
优先级：Kimi → Qwen → fallback
"""
import os
import re
import random
from dotenv import load_dotenv

# 首先尝试加载 .env（本地开发）
load_dotenv()

# 尝试从 Streamlit Secrets 获取（云端部署）
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        QWEN_KEY = st.secrets.get("QWEN_API_KEY") or os.getenv("QWEN_API_KEY")
    else:
        MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
        QWEN_KEY = os.getenv("QWEN_API_KEY")
except:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    QWEN_KEY = os.getenv("QWEN_API_KEY")

DEBUG_MODE = True

if DEBUG_MODE:
    print(f"\n{'='*70}")
    print(f"[🔑 API Key 检查]")
    print(f"  ✓ MOONSHOT_KEY: {MOONSHOT_KEY[:20]}..." if MOONSHOT_KEY else "  ✗ MOONSHOT_KEY: 未设置")
    print(f"  ✓ QWEN_KEY: {QWEN_KEY[:20]}..." if QWEN_KEY else "  ✗ QWEN_KEY: 未设置")
    print(f"{'='*70}\n")


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """根据 mode 与 user_message 生成 AI 回复"""
    if DEBUG_MODE:
        print(f"\n{'='*70}")
        print(f"[🤖 AI 回复生成]")
        print(f"  📌 模式: {mode}")
        print(f"  💬 消息: {user_message[:50]}...")
        print(f"{'='*70}")
    
    if mode == "Control":
        return "（此为控制组，不提供 AI 干预）"
    
    system_prompt = custom_prompt or _get_default_prompt(mode)
    conversation_context = _build_conversation_context(conversation_history)
    
    return _generate_with_prompt(system_prompt, user_message, conversation_context, mode)


def _build_conversation_context(history, max_messages=10):
    """从对话历史中提取上下文"""
    if not history:
        return ""
    
    context_messages = []
    for h in history[-max_messages:]:
        user_name = h.get("user", "")
        message = h.get("message", "")
        role = h.get("role", "user")
        
        if role == "assistant" or user_name == "AI":
            context_messages.append(f"AI: {message}")
        else:
            clean_msg = message.replace("@AI", "").replace("@ai", "").replace("＠AI", "").strip()
            context_messages.append(f"{user_name}: {clean_msg}")
    
    return "\n".join(context_messages) if context_messages else ""


def _extract_key_points(conversation_context):
    """提取关键词"""
    if not conversation_context:
        return []
    
    key_points = re.findall(r'[「『""]([^「『""]{2,20})[」』""]', conversation_context)
    if key_points:
        return list(set(key_points))[:3]
    
    return []


def _get_default_prompt(mode):
    """获取默认 system prompt"""
    prompts = {
        "AI-Scaffolded": (
            "你是一位杰出的苏格拉底式教师。你的角色是：\n"
            "1. 通过精妙的提问激发学生的批判性思维\n"
            "2. 从不直接给出答案，而是引导学生自己发现\n"
            "3. 基于学生的观点，提出有针对性的后续问题\n"
            "4. 每次给出不同角度的问题，避免重复\n"
            "你的提问应该简洁、有启发性。"
        ),
        "AI-Free-Debater": (
            "你是一位经验丰富的辩手和批判性思维导师。你的角色是��\n"
            "1. 基于学生的论点，提出有力的反对观点\n"
            "2. 用「但是」「相反」「我不同意」等词开头表达相反意见\n"
            "3. 给出具体的反例或替代解释\n"
            "4. 要求学生提供更有力的证据\n"
            "5. 保持尊重和建设性的态度"
        ),
        "Control": "（此为控制组，不提供 AI 干预）"
    }
    return prompts.get(mode, "")


def _generate_with_prompt(system_prompt, user_message, conversation_context, mode):
    """生成回复 - 优先级：Kimi → Qwen → fallback"""
    enhanced_prompt = system_prompt
    if conversation_context:
        enhanced_prompt += "\n\n【讨论背景】\n" + conversation_context
    
    # 1️⃣ 尝试 Kimi API（首选）
    if MOONSHOT_KEY:
        if DEBUG_MODE:
            print("[🔄 尝试 Kimi API...]")
        try:
            response = _generate_with_kimi(enhanced_prompt, user_message)
            if response:
                if DEBUG_MODE:
                    print("[✅ Kimi API 成功]")
                return response
        except Exception as e:
            if DEBUG_MODE:
                print(f"[❌ Kimi 失败: {str(e)[:100]}]")
    else:
        if DEBUG_MODE:
            print("[⚠️ MOONSHOT_API_KEY 未设置]")
    
    # 2️⃣ 尝试 Qwen API
    if QWEN_KEY:
        if DEBUG_MODE:
            print("[🔄 尝试 Qwen API...]")
        try:
            response = _generate_with_qwen(enhanced_prompt, user_message)
            if response:
                if DEBUG_MODE:
                    print("[✅ Qwen API 成功]")
                return response
        except Exception as e:
            if DEBUG_MODE:
                print(f"[❌ Qwen 失败: {str(e)[:100]}]")
    else:
        if DEBUG_MODE:
            print("[⚠️ QWEN_API_KEY 未设置]")
    
    # 3️⃣ 使用 Fallback
    if DEBUG_MODE:
        print("[🔄 使用 Fallback]")
    return _generate_fallback(system_prompt, user_message, mode)


def _generate_with_kimi(system_prompt, user_message):
    """调用 Kimi (Moonshot) API"""
    try:
        import requests
        
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_KEY}"
        }
        
        payload = {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        if DEBUG_MODE:
            print(f"  📤 发送到: {url}")
            print(f"  🔑 Key长度: {len(MOONSHOT_KEY)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if DEBUG_MODE:
            print(f"  📥 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if DEBUG_MODE:
                print(f"  ✓ 返回内容: {len(content)} 字符")
            return content if content else None
        else:
            if DEBUG_MODE:
                print(f"  ✗ 错误响应: {response.text[:200]}")
            return None
    
    except ImportError:
        print("[❌ requests 未安装: pip install requests]")
        return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ✗ 异常: {str(e)}")
        return None


def _generate_with_qwen(system_prompt, user_message):
    """调用 Qwen API"""
    try:
        from dashscope import Generation
        
        response = Generation.call(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            api_key=QWEN_KEY,
            temperature=0.7,
            max_tokens=300,
            timeout=20
        )
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content.strip()
            return content
        else:
            if DEBUG_MODE:
                print(f"  ✗ Qwen 错误: {response.code}")
            return None
    
    except ImportError:
        print("[❌ dashscope 未安装: pip install dashscope]")
        return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ✗ 异常: {str(e)}")
        return None


def _generate_fallback(system_prompt, user_message, mode):
    """Fallback 回复"""
    is_socratic = "苏格拉底" in system_prompt
    is_debater = "辩手" in system_prompt
    
    if is_socratic:
        responses = [
            "你的观点很有趣。能进一步解释你的想法吗？",
            "这是个好问题。你认为最根本的原因是什么？",
            "有什么证据或例子能支持你的观点吗？",
        ]
    elif is_debater:
        responses = [
            "我理解你的立场，但我想从另一个角度看。",
            "这个观点有道理，但你有没有考虑过相反的情况？",
            "你的论证需要更强有力的证据。能提供吗？",
        ]
    else:
        responses = [
            "你的想法很有意思。能继续说说吗？",
            "这是个值得思考的观点。",
        ]
    
    return random.choice(responses)