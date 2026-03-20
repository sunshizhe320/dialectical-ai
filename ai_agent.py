"""
ai_agent.py
AI 回复生成模块 - 仅支持 Kimi (Moonshot)
"""
import os
import re
import random
from dotenv import load_dotenv
import streamlit as st

# 加载 .env 文件（本地开发）
load_dotenv()

# 获取 API Key - 优先从 Streamlit Secrets，其次从环境变量
MOONSHOT_KEY = None

# 方法1: 从 Streamlit Secrets 获取（Streamlit Cloud）
try:
    if hasattr(st, 'secrets') and st.secrets:
        MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY")
        print(f"✅ 从 Streamlit Secrets 加载 Key")
except Exception as e:
    print(f"⚠️ 无法从 Secrets 读取: {e}")

# 方法2: 从环境变量获取（本地或其他）
if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    print(f"✅ 从环境变量加载 Key")

# 调试输出
print(f"\n{'='*70}")
print(f"[🔑 API Key 检查]")
if MOONSHOT_KEY:
    print(f"  ✅ MOONSHOT_KEY 已加载")
    print(f"     前缀: {MOONSHOT_KEY[:10]}...")
    print(f"     长度: {len(MOONSHOT_KEY)} 字符")
else:
    print(f"  ❌ MOONSHOT_KEY 未设置！")
    print(f"     请在 Streamlit Cloud Secrets 或 .env 文件中设置")
print(f"{'='*70}\n")

DEBUG_MODE = True


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """根据 mode 与 user_message 生成 AI 回复"""
    if DEBUG_MODE:
        print(f"\n{'='*70}")
        print(f"[🤖 生成 AI 回复]")
        print(f"  模式: {mode}")
        print(f"  用户: {user}")
        print(f"  消息: {user_message[:50]}...")
        print(f"  API Key 可用: {bool(MOONSHOT_KEY)}")
        print(f"{'='*70}")
    
    if mode == "Control":
        return "（此为控制组，不提供 AI 干预）"
    
    if not MOONSHOT_KEY:
        print("❌ 错误：MOONSHOT_API_KEY 未设置！")
        return "❌ AI 服务暂不可用，请检查 API Key 配置"
    
    system_prompt = custom_prompt or _get_default_prompt(mode)
    conversation_context = _build_conversation_context(conversation_history)
    
    return _generate_with_kimi(system_prompt, user_message, conversation_context)


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
            "你是一位经验丰富的辩手和批判性思维导师。你的角色是：\n"
            "1. 基于学生的论点，提出有力的反对观点\n"
            "2. 用「但是」「相反」「我不同意」等词开头表达相反意见\n"
            "3. 给出具体的反例或替代解释\n"
            "4. 要求学生提供更有力的证据\n"
            "5. 保持尊重和建设性的态度"
        ),
        "Control": "（此为控制组，不提供 AI 干预）"
    }
    return prompts.get(mode, "")


def _generate_with_kimi(system_prompt, user_message, conversation_context):
    """直接调用 Kimi API - 包含详细的调试信息"""
    
    print(f"\n{'─'*70}")
    print(f"[📤 调用 Kimi API]")
    
    try:
        import requests
        
        # API 配置
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_KEY}"
        }
        
        # 构建消息
        enhanced_prompt = system_prompt
        if conversation_context:
            enhanced_prompt += "\n\n【讨论背景】\n" + conversation_context
        
        messages = [
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": user_message}
        ]
        
        payload = {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        print(f"  URL: {url}")
        print(f"  模型: moonshot-v1-8k")
        print(f"  消息数: {len(messages)}")
        print(f"  请求大小: {len(str(payload))} 字符")
        print(f"  发送请求...")
        
        # 发送请求
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"  ✓ 收到响应")
        print(f"  状态码: {response.status_code}")
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            
            # 验证响应结构
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "").strip()
                
                if content:
                    print(f"  ✅ 成功获得回复")
                    print(f"  内容长度: {len(content)} 字符")
                    print(f"  内容预览: {content[:50]}...")
                    print(f"{'─'*70}\n")
                    return content
                else:
                    print(f"  ❌ 响应内容为空")
                    print(f"  完整响应: {result}")
            else:
                print(f"  ❌ 响应结构不正确")
                print(f"  响应: {result}")
        else:
            print(f"  ❌ HTTP 错误")
            print(f"  状态码: {response.status_code}")
            print(f"  响应头: {dict(response.headers)}")
            print(f"  响应体: {response.text[:500]}")
        
        print(f"{'─'*70}\n")
        return None
    
    except ImportError:
        print(f"  ❌ requests 库未安装")
        print(f"     请运行: pip install requests")
        return None
    
    except Exception as e:
        print(f"  ❌ 异常错误")
        print(f"  类型: {type(e).__name__}")
        print(f"  信息: {str(e)}")
        print(f"{'─'*70}\n")
        return None


# Fallback 回复
def _get_fallback_response(mode):
    """获取 Fallback 回复"""
    is_socratic = "苏格拉底" in _get_default_prompt(mode)
    
    if is_socratic:
        responses = [
            "你的观点很有趣。能进一步解释一下吗？",
            "这是个好问题。你认为最根本的原因是什么？",
            "有什么证据或例子能支持你的观点吗？",
            "从反面想，如果不是这样会怎样？",
        ]
    else:
        responses = [
            "我理解你的立场，但我想从另���个角度看。",
            "这个观点有道理，但你有没有考虑过相反的情况？",
            "你的论证需要更强有力的证据。能提供吗？",
        ]
    
    return random.choice(responses)