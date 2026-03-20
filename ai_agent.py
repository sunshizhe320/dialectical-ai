"""
ai_agent.py
AI 回复生成模块 - 支持 Kimi (Moonshot) / Qwen / fallback
优先级：Kimi → Qwen → fallback
"""
import os
import re
import random
from dotenv import load_dotenv

load_dotenv()

# 获取 API Keys
MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")  # Kimi API Key
QWEN_KEY = os.getenv("QWEN_API_KEY")

DEBUG_MODE = True


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """
    根据 mode 与 user_message 生成 AI 回复
    
    Args:
        mode: "AI-Scaffolded" / "AI-Free-Debater" / "Control"
        user_message: 用户输入的消息
        group_id: 所属 session
        user: 使用者名称
        conversation_history: 对话历史列表
        custom_prompt: 自定 system prompt
    
    Returns:
        AI 回复字符串
    """
    if DEBUG_MODE:
        print(f"\n{'='*60}")
        print(f"[🤖 AI 回复生成启动]")
        print(f"  📌 模式: {mode}")
        print(f"  💬 用户消息: {user_message[:60]}...")
        print(f"  🔑 Kimi Key: {bool(MOONSHOT_KEY)}")
        print(f"  🔑 Qwen Key: {bool(QWEN_KEY)}")
        print(f"{'='*60}")
    
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
    
    key_points = re.findall(r'[:：]\s*([^。，？！\n]{4,20})', conversation_context)
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


def _generate_with_prompt(system_prompt, user_message, conversation_context, mode):
    """生成回复 - 优先级：Kimi → Qwen → fallback"""
    enhanced_prompt = system_prompt
    if conversation_context:
        enhanced_prompt += "\n\n【讨论背景】\n" + conversation_context
    
    # 1️⃣ 尝试 Kimi API（首选！）
    if MOONSHOT_KEY:
        if DEBUG_MODE:
            print("[🔄 正在调用 Kimi API...]")
        try:
            response = _generate_with_kimi(enhanced_prompt, user_message)
            if response:
                if DEBUG_MODE:
                    print(f"[✅ Kimi API 调用成功！]")
                return response
        except Exception as e:
            if DEBUG_MODE:
                print(f"[❌ Kimi API 失败: {str(e)}]")
    else:
        if DEBUG_MODE:
            print("[⚠️ 未设置 MOONSHOT_API_KEY]")
    
    # 2️⃣ 尝试 Qwen API
    if QWEN_KEY:
        if DEBUG_MODE:
            print("[🔄 正在调用 Qwen API...]")
        try:
            response = _generate_with_qwen(enhanced_prompt, user_message)
            if response:
                if DEBUG_MODE:
                    print(f"[✅ Qwen API 调用成功！]")
                return response
        except Exception as e:
            if DEBUG_MODE:
                print(f"[❌ Qwen API 失败: {str(e)}]")
    else:
        if DEBUG_MODE:
            print("[⚠️ 未设置 QWEN_API_KEY]")
    
    # 3️⃣ 使用 Fallback
    if DEBUG_MODE:
        print("[🔄 使用 Fallback 模式]")
    response = _generate_fallback_smart(system_prompt, user_message, conversation_context, mode)
    if DEBUG_MODE:
        print(f"[✅ Fallback 返回]")
    return response


def _generate_with_kimi(system_prompt, user_message):
    """调用 Kimi (Moonshot) API"""
    try:
        import requests
        
        if DEBUG_MODE:
            print("  ✓ requests 库导入成功")
        
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_KEY}"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        payload = {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        if DEBUG_MODE:
            print(f"  ✓ 发送请求到 Kimi API...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if DEBUG_MODE:
            print(f"  ✓ 返回状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            if DEBUG_MODE:
                print(f"  ✓ 内容长度: {len(content)} 字符")
            return content
        else:
            if DEBUG_MODE:
                print(f"  ✗ API 错误: {response.status_code}")
                print(f"  ✗ 响应: {response.text[:200]}")
            return None
    
    except ImportError:
        if DEBUG_MODE:
            print("  ✗ requests 库未安装")
        print("[⚠️ 请安装 requests: pip install requests]")
        return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ✗ 异常: {type(e).__name__}: {str(e)}")
        return None


def _generate_with_qwen(system_prompt, user_message):
    """调用通义千问 API"""
    try:
        from dashscope import Generation
        
        if DEBUG_MODE:
            print("  ✓ dashscope 库导入成功")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if DEBUG_MODE:
            print(f"  ✓ 发送请求到 Qwen API...")
        
        response = Generation.call(
            model="qwen-turbo",
            messages=messages,
            api_key=QWEN_KEY,
            temperature=0.7,
            max_tokens=300,
            timeout=15
        )
        
        if DEBUG_MODE:
            print(f"  ✓ 返回状态码: {response.status_code}")
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content.strip()
            if DEBUG_MODE:
                print(f"  ✓ 内容长度: {len(content)} 字符")
            return content
        else:
            if DEBUG_MODE:
                print(f"  ✗ API 错误: {response.code}")
            return None
    
    except ImportError:
        if DEBUG_MODE:
            print("  ✗ dashscope 库未安装")
        print("[⚠️ 请安装 dashscope: pip install dashscope]")
        return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ✗ 异常: {type(e).__name__}: {str(e)}")
        return None


def _generate_fallback_smart(system_prompt, user_message, conversation_context, mode):
    """改进的 fallback"""
    is_socratic = "苏格拉底" in system_prompt
    is_debater = "辩手" in system_prompt
    
    clean_message = re.sub(r'@ai|@AI|＠AI', '', user_message, flags=re.IGNORECASE).strip()
    key_points = _extract_key_points(conversation_context)
    
    if is_socratic:
        templates = _get_socratic_templates(clean_message, key_points)
        return random.choice(templates) if templates else "你的思考很深入。能继续挖掘一下这个观点吗？"
    
    elif is_debater:
        templates = _get_debater_templates(clean_message, key_points)
        return random.choice(templates) if templates else "我理解你的立场，但我想从另一个角度挑战它。"
    
    return "你的想法很有意思。能进一步解释一下背后的逻辑吗？"


def _get_socratic_templates(message, key_points):
    """获取 Socratic 提问模板"""
    templates = []
    
    if any(w in message for w in ["为什么", "为何", "why"]):
        if key_points:
            templates.extend([
                f"你提到「{key_points[0]}」，能解释为什么吗？",
                f"除了「{key_points[0]}」，还有其他原因吗？",
            ])
    
    elif any(w in message for w in ["怎样", "如何", "how"]):
        if key_points:
            templates.extend([
                f"具体到「{key_points[0]}」，你会如何处理？",
                f"「{key_points[0]}」有其他做法吗？",
            ])
    
    else:
        if key_points:
            templates.extend([
                f"「{key_points[0]}」总是成立吗？",
                f"有其他角度来看「{key_points[0]}」吗？",
            ])
    
    return templates if templates else [
        "你的观点很有趣。你的论据是什么？",
        "有没有其他方式来看这个问题？",
    ]


def _get_debater_templates(message, key_points):
    """获取 Debater 反驳模板"""
    templates = []
    
    if any(w in message for w in ["总是", "永远", "从不"]):
        templates.extend([
            "说「总是」有点绝对。能举个例外吗？",
            "真的「永远」都这样吗？",
        ])
    
    else:
        if key_points:
            templates.extend([
                f"关于「{key_points[0]}」，我有不同看法。",
                f"「{key_points[0]}」的反面是什么？",
            ])
        else:
            templates.extend([
                "这个观点有一定道理，但我想挑战一下。",
                "我同意你的一部分，但另一部分我有异议。",
            ])
    
    return templates if templates else [
        "我理解你，但我想从另一个角度看。",
        "有没有其他可能性？",
    ]