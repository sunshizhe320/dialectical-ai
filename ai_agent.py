"""
ai_agent.py
AI 回复生成模块 - Kimi (Moonshot) API
包含详细的调试信息
"""
import os
import re
import random
from dotenv import load_dotenv
import streamlit as st

# 加载环境变量
load_dotenv()

# 获取 API Key - 优先从 Streamlit Secrets
MOONSHOT_KEY = None

# 方法1: 从 Streamlit Secrets 获取（优先）
try:
    if hasattr(st, 'secrets') and st.secrets:
        MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY")
        if MOONSHOT_KEY:
            print(f"✅ 从 Streamlit Secrets 加载 MOONSHOT_API_KEY")
except Exception as e:
    print(f"⚠️ 无法从 Secrets 读取: {e}")

# 方法2: 从环境变量获取（备选）
if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    if MOONSHOT_KEY:
        print(f"✅ 从环境变量加载 MOONSHOT_API_KEY")

# 打印初始化状态
print(f"\n{'='*80}")
print(f"[🔧 AI Agent 初始化]")
if MOONSHOT_KEY:
    print(f"✅ MOONSHOT_API_KEY 已加载")
    print(f"   长度: {len(MOONSHOT_KEY)} 字符")
    print(f"   前缀: {MOONSHOT_KEY[:20]}...")
else:
    print(f"❌ MOONSHOT_API_KEY 未设置!")
print(f"{'='*80}\n")

DEBUG_MODE = True


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """生成 AI 回复"""
    
    if DEBUG_MODE:
        print(f"\n{'='*80}")
        print(f"[📝 generate_response 调用]")
        print(f"  mode: {mode}")
        print(f"  user: {user}")
        print(f"  message: {user_message[:50]}...")
        print(f"  MOONSHOT_KEY 可用: {bool(MOONSHOT_KEY)}")
    
    if mode == "Control":
        return "（此为控制组，不提供 AI 干预）"
    
    if not MOONSHOT_KEY:
        error_msg = "❌ API Key 未配置"
        if DEBUG_MODE:
            print(f"[❌ 错误] {error_msg}")
        return error_msg
    
    system_prompt = custom_prompt or _get_default_prompt(mode)
    conversation_context = _build_conversation_context(conversation_history)
    
    # 调用 Kimi API
    if DEBUG_MODE:
        print(f"[🔄 调用 Kimi API...]")
    
    response = _call_kimi_api(system_prompt, user_message, conversation_context)
    
    if DEBUG_MODE:
        print(f"[📤 API 返回] {response[:50] if response else 'None'}...")
    
    # 如果 API 失败，使用 Fallback
    if not response:
        if DEBUG_MODE:
            print(f"[⚠️ API 失败，使用 Fallback]")
        response = _get_fallback(mode)
    
    if DEBUG_MODE:
        print(f"[✅ 最终返回] {response[:50]}...")
        print(f"{'='*80}\n")
    
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
    """调用 Kimi (Moonshot) API - 包含详细调试"""
    
    print(f"\n{'─'*80}")
    print(f"[📤 _call_kimi_api 开始]")
    
    try:
        # 导入 requests
        print(f"  [1/6] 导入 requests...")
        import requests
        print(f"       ✅ 成功")
        
        # 构建 URL
        url = "https://api.moonshot.cn/v1/chat/completions"
        print(f"  [2/6] 设置 URL: {url}")
        
        # 构建请求头
        print(f"  [3/6] 构建请求头...")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_KEY}"
        }
        print(f"       ✅ Authorization header 已设置")
        
        # 构建完整 prompt
        print(f"  [4/6] 构建消息...")
        full_prompt = system_prompt
        if context:
            full_prompt += f"\n\n【讨论背景】\n{context}"
        
        messages = [
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": user_message}
        ]
        print(f"       ✅ messages 数量: {len(messages)}")
        
        # 构建请求体
        print(f"  [5/6] 构建请求体...")
        payload = {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300
        }
        print(f"       ✅ payload 大小: {len(str(payload))} 字节")
        
        # 发送请求
        print(f"  [6/6] 发送 POST 请求...")
        print(f"       URL: {url}")
        print(f"       Timeout: 30 秒")
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"\n{'─'*80}")
        print(f"[📥 收到响应]")
        print(f"  状态码: {response.status_code}")
        print(f"  响应大小: {len(response.text)} 字符")
        
        # 检查 HTTP 状态
        if response.status_code != 200:
            print(f"\n❌ HTTP 错误 {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print(f"响应体:\n{response.text[:500]}")
            return None
        
        # 解析 JSON
        print(f"\n  [解析 JSON...]")
        try:
            result = response.json()
            print(f"  ✅ JSON 解析成功")
        except Exception as e:
            print(f"  ❌ JSON 解析失败: {e}")
            print(f"  原文本: {response.text[:200]}")
            return None
        
        # 验证响应结构
        print(f"\n  [验证响应结构...]")
        print(f"  响应字段: {list(result.keys())}")
        
        if "choices" not in result:
            print(f"  ❌ 缺少 'choices' 字段")
            print(f"  完整响应: {result}")
            return None
        
        if len(result["choices"]) == 0:
            print(f"  ❌ choices 为空")
            return None
        
        choice = result["choices"][0]
        print(f"  ✅ 获得第一个 choice")
        
        if "message" not in choice:
            print(f"  ❌ 缺少 'message' 字段")
            print(f"  choice: {choice}")
            return None
        
        message = choice["message"]
        print(f"  ✅ 获得 message")
        
        if "content" not in message:
            print(f"  ❌ 缺少 'content' 字段")
            print(f"  message: {message}")
            return None
        
        content = message["content"].strip()
        
        if not content:
            print(f"  ❌ content 为空")
            return None
        
        print(f"\n✅ 成功获得回复!")
        print(f"  内容长度: {len(content)} 字符")
        print(f"  内容预览: {content[:100]}...")
        print(f"{'─'*80}\n")
        
        return content
    
    except requests.exceptions.Timeout as e:
        print(f"\n❌ 请求超时 (30秒)")
        print(f"  错误: {e}")
        return None
    
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ 连接错误")
        print(f"  错误: {e}")
        return None
    
    except Exception as e:
        print(f"\n❌ 异常错误")
        print(f"  类型: {type(e).__name__}")
        print(f"  信息: {str(e)}")
        import traceback
        print(f"  堆栈:\n{traceback.format_exc()}")
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

def generate_argument_map(messages, topic):
    """
    分析对话历史，提取结构化的论证图谱
    """
    history_text = "\n".join([f"{m['user']}: {m['message']}" for m in messages if m['role'] != 'system'])
    
    prompt = f"""
    你是一名教育专家。请分析关于“{topic}”的讨论记录，并提取结构化论证。
    输出要求：
    1. 为每个参与者提取：立场（支持/反对/中立）、核心观点、支撑论据、互动逻辑。
    2. 给出当前讨论的阶段性共识。
    3. 严格使用 Markdown 表格和引用块格式。

    讨论记录：
    {history_text}
    """
    
    # 调用你现有的 get_kimi_response
    return get_kimi_response([{"role": "user", "content": prompt}])