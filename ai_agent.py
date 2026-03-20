"""
ai_agent.py
AI 回复生成模块 - 支持 Moonshot (Kimi) + transformers + 对话历史上下文感知 + 多变回复
优先级：Moonshot → transformers → 改进的 fallback
"""
import os
import re
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")

# 调试模式 - 可改为 True 查看内部逻辑
DEBUG_MODE = False


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """
    根据 mode 与 user_message 生成 AI 回复
    
    Args:
        mode: "AI-Scaffolded" / "AI-Free-Debater" / "Control"
        user_message: 用户输入的消息
        group_id: 所属 group（用于记录）
        user: 使用者名称（用于记录）
        conversation_history: 对话历史列表
        custom_prompt: 自定 system prompt
    
    Returns:
        AI 回复字符串
    """
    if mode == "Control":
        return "（此为控制组，不提供 AI 干预）"
    
    system_prompt = custom_prompt or _get_default_prompt(mode)
    conversation_context = _build_conversation_context(conversation_history)
    
    if DEBUG_MODE:
        print(f"\n[DEBUG] Mode: {mode}")
        print(f"[DEBUG] User Message: {user_message}")
        print(f"[DEBUG] Context: {conversation_context[:100]}...")
    
    return _generate_with_prompt(system_prompt, user_message, conversation_context, mode)


def _build_conversation_context(history, max_messages=10):
    """
    从对话历史中提取上下文
    """
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
    """
    更聪明的关键词提取
    """
    if not conversation_context:
        return []
    
    # 策略1：提取引号内容
    key_points = re.findall(r'[「『""]([^」』""]{2,20})[」』""]', conversation_context)
    if key_points:
        return list(set(key_points))[:3]
    
    # 策略2：提取冒号后的短语
    key_points = re.findall(r'[:：]\s*([^。，？！\n]{4,20})', conversation_context)
    if key_points:
        return list(set(key_points))[:3]
    
    # 策略3：提取最后一条消息中的名词
    lines = conversation_context.split('\n')
    if lines:
        last_line = lines[-1]
        nouns = re.findall(r'[\u4e00-\u9fff]{2,10}(?:[学习|作业|思考|观点|理由|例子|情况]{0,2})', last_line)
        if nouns:
            return list(set(nouns))[:3]
    
    return []


def _get_response_history_key(user_message):
    """获取用户消息的哈希值，用于检测重复"""
    clean = re.sub(r'@ai|@AI|＠AI|\s+', '', user_message, flags=re.IGNORECASE)
    return clean[:20]


def _get_default_prompt(mode):
    """获取默认 system prompt"""
    prompts = {
        "AI-Scaffolded": (
            "你是一位杰出的苏格拉底式教师。你的角色是：\n"
            "1. 通过精妙的提问激发学生的批判性思维\n"
            "2. 从不直接给出答案，而是引导学生自己发现\n"
            "3. 基于学生的观点，提出有针对性的后续问题\n"
            "4. 每次给出不同角度的问题，避免重复\n"
            "5. 承认学生的努力，然后进一步深化讨论\n"
            "你的提问应该简洁、有启发性，让学生思考得更深。"
        ),
        "AI-Free-Debater": (
            "你是一位经验丰富的辩手和批判性思维导师。你的角色是：\n"
            "1. 基于学生的论点，提出有力的反对观点\n"
            "2. 用「但是」「相反」「我不同意」等词开头表达相反意见\n"
            "3. 给出具体的反例或替代解释\n"
            "4. 要求学生提供更有力的证据\n"
            "5. 每次从不同角度进行辩论，避免重复相同论点\n"
            "6. 保持尊重和建设性的态度\n"
            "你的目标是帮助学生加强论证、发现漏洞、完善观点。"
        ),
        "Control": "（此为控制组，不提供 AI 干预）"
    }
    return prompts.get(mode, "")


def _generate_with_prompt(system_prompt, user_message, conversation_context, mode):
    """
    生成回复 - 优先级：Moonshot → transformers → 改进的 fallback
    """
    enhanced_prompt = system_prompt
    if conversation_context:
        enhanced_prompt += "\n\n【讨论背景】\n" + conversation_context

    # 1) 尝试 Moonshot (Kimi)
    if MOONSHOT_KEY:
        try:
            if DEBUG_MODE:
                print("[DEBUG] 尝试调用 Moonshot (Kimi) API...")
            response = _generate_with_moonshot(enhanced_prompt, user_message)
            if response:
                if DEBUG_MODE:
                    print(f"[DEBUG] Moonshot 返回: {response[:50]}...")
                return response
        except Exception as e:
            if DEBUG_MODE:
                print(f"[DEBUG] Moonshot 失败: {e}")

    # 2) 尝试 transformers（本地模型）
    try:
        if DEBUG_MODE:
            print("[DEBUG] 尝试调用 transformers...")
        response = _generate_with_transformers(enhanced_prompt, user_message)
        if response:
            if DEBUG_MODE:
                print(f"[DEBUG] transformers 返回: {response[:50]}...")
            return response
    except Exception as e:
        if DEBUG_MODE:
            print(f"[DEBUG] transformers 失败: {e}")

    # 3) 使用改进的 fallback
    if DEBUG_MODE:
        print("[DEBUG] 使用 fallback 模式")
    return _generate_fallback_smart(system_prompt, user_message, conversation_context, mode)


def _generate_with_moonshot(system_prompt, user_message):
    """调用 Moonshot (Kimi) API"""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=MOONSHOT_KEY,
            base_url="https://api.moonshot.cn/v1"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            timeout=15
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        print("[WARNING] openai 未安装: pip install openai")
        return None
    except Exception as e:
        print(f"[WARNING] Moonshot 错误: {e}")
        return None


def _generate_with_transformers(system_prompt, user_message):
    """使用本地 transformers 模型（英文为主，中文能力弱）"""
    try:
        from transformers import pipeline, set_seed
        
        # 使用兼容性较好的模型（如 gpt2），但注意：对中文支持差
        gen = pipeline("text-generation", model="gpt2", device=-1)
        prompt = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
        set_seed(random.randint(1, 1000))
        
        outputs = gen(prompt, max_length=150, num_return_sequences=1, do_sample=True, pad_token_id=50256)
        text = outputs[0]["generated_text"]
        reply = text.split("Assistant:")[-1].strip()
        
        # 过滤无效回复
        if len(reply) < 10 or "User:" in reply:
            return None
        return reply
    except Exception as e:
        print(f"[WARNING] transformers 错误: {e}")
        return None


def _generate_fallback_smart(system_prompt, user_message, conversation_context, mode):
    """
    改进的 fallback - 更聪明、更多变
    """
    is_socratic = "苏格拉底" in system_prompt or "引导性问题" in system_prompt
    is_debater = "辩手" in system_prompt or "反对" in system_prompt
    
    clean_message = re.sub(r'@ai|@AI|＠AI', '', user_message, flags=re.IGNORECASE).strip()
    key_points = _extract_key_points(conversation_context)
    
    if DEBUG_MODE:
        print(f"[DEBUG] 模式: {'Socratic' if is_socratic else 'Debater' if is_debater else 'Other'}")
        print(f"[DEBUG] 关键词: {key_points}")
    
    if is_socratic:
        templates = _get_socratic_templates(clean_message, key_points)
        return random.choice(templates) if templates else _get_default_socratic(key_points)
    
    elif is_debater:
        templates = _get_debater_templates(clean_message, key_points)
        return random.choice(templates) if templates else _get_default_debater(key_points)
    
    return "这个想法很有意思。能进一步解释一下背后的逻辑吗？"


# ========== 以下函数保持不变（模板逻辑）==========
def _get_socratic_templates(message, key_points):
    templates = []
    if any(w in message for w in ["为什么", "为何", "why", "原因"]):
        if key_points:
            templates.extend([
                f"有趣的问题。你提到「{key_points[0]}」，那为什么你认为这是最重要的原因？",
                f"这个「为什么」问得好。除了「{key_points[0]}」，还有其他可能的解释吗？",
                f"关于「{key_points[0]}」，你能举个具体例子来说明吗？",
                f"如果改变「{key_points[0]}」的条件，结果会不同吗？",
            ])
        else:
            templates.extend([
                "这是个深层的「为什么」。你认为最根本的原因是什么？",
                "有什么证据或例子能支持你的「为什么」吗？",
                "从反面想，如果不是这个原因，会怎样？",
            ])
    elif any(w in message for w in ["怎样", "如何", "how", "方法"]):
        if key_points:
            templates.extend([
                f"好问题。具体到「{key_points[0]}」，你会如何处理？",
                f"关于「{key_points[0]}」的方法，有不同的做法吗？",
                f"如果「{key_points[0]}」变了，你的方法还适用吗？",
            ])
        else:
            templates.extend([
                "你的做法听起来不错。具体步骤是什么？",
                "有其他的方式也能达到同样效果吗？",
                "这个方法的前提条件是什么？",
            ])
    elif any(w in message for w in ["对比", "区别", "不同", "比较"]):
        if len(key_points) >= 2:
            templates.extend([
                f"「{key_points[0]}」和「{key_points[1]}」的关键区别在哪？这个区别是否改变你的看法？",
                f"你觉得「{key_points[0]}」和「{key_points[1]}」哪个更重要？为什么？",
            ])
        else:
            templates.extend([
                "这两个观点的共同点是什么？",
                "区别重要吗？为什么？",
            ])
    else:
        if key_points:
            templates.extend([
                f"你提到「{key_points[0]}」，这个假设是从哪里来的？",
                f"我很想理解你关于「{key_points[0]}」的想法。能再详细说说吗？",
                f"「{key_points[0]}」总是成立吗？有例外情况吗？",
                f"基于「{key_points[0]}」，下一步的逻辑是什么？",
            ])
        else:
            templates.extend([
                "这个观点很有趣。你的论据是什么？",
                "有没有其他方式来看这个问题？",
                "这个结论必然成立吗？",
            ])
    return templates


def _get_debater_templates(message, key_points):
    templates = []
    if any(w in message for w in ["容易", "简单", "显然", "当然"]):
        templates.extend([
            "我不太同意这个「容易」的判断。真的所有情况都这么简单吗？",
            "这个想法似乎过于简化了。有没有复杂的情况？",
            "你这个结论太笃定了。有没有反例？",
        ])
    elif any(w in message for w in ["总是", "永远", "从不", "absolutely"]):
        templates.extend([
            "说「总是」有点太绝对了。你能举个例外吗？",
            "这个观点很强硬，但现实可能更复杂。你同意吗？",
            "真的「永远」都这样吗？让我想想反例...",
        ])
    else:
        if key_points:
            templates.extend([
                f"关于「{key_points[0]}」，我有不同看法。你考虑过反面吗？",
                f"我理解你的立场，但「{key_points[0]}」有个问题：...",
                f"有个点我想挑战：你怎么看「{key_points[0]}」的反面例子？",
            ])
        else:
            templates.extend([
                "这个观点有一定道理，但有个我想挑战的地方。",
                "我同意你的一部分，但另一部分我不太赞同。为什么？",
                "这个逻辑有个漏洞：有没有反例？",
            ])
    return templates


def _get_default_socratic(key_points):
    defaults = [
        "你的思考很深入。能继续挖掘一下这个观点吗？",
        "这是个好想法。背后的假设是什么？",
        "有证据或例子来支持你的观点吗？",
    ]
    return random.choice(defaults)


def _get_default_debater(key_points):
    defaults = [
        "我理解你的立场，但我想从另一个角度挑战它。",
        "这个观点有一定道理，但你有没有考虑过相反的情况？",
        "你的论证需要更强有力的证据。你能提供吗？",
    ]
    return random.choice(defaults)