"""
ai_agent.py (Improved Version)
AI Response Generation with Fixed API Calls for All Modes
"""
import os
import re
import random
from dotenv import load_dotenv
import streamlit as st
import requests

load_dotenv()

MOONSHOT_KEY = None

try:
    if hasattr(st, 'secrets') and st.secrets:
        MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY")
        if MOONSHOT_KEY:
            print(f"✅ MOONSHOT_API_KEY loaded from Streamlit Secrets")
except Exception as e:
    print(f"⚠️ Unable to read from Secrets: {e}")

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    if MOONSHOT_KEY:
        print(f"✅ MOONSHOT_API_KEY loaded from Environment Variables")

print(f"\n{'='*80}")
print(f"[🔧 AI Agent Initialization]")
if MOONSHOT_KEY:
    print(f"✅ MOONSHOT_API_KEY is SET (Length: {len(MOONSHOT_KEY)})")
else:
    print(f"❌ MOONSHOT_API_KEY is NOT SET!")
print(f"{'='*80}\n")

DEBUG_MODE = True


def _call_kimi_api(system_prompt, user_message, max_tokens=500):
    """
    ✅ 统一的API调用函数 - 所有模式都使用这个
    """
    if not MOONSHOT_KEY:
        error_msg = "❌ API Key not configured"
        if DEBUG_MODE:
            print(f"[❌ Error] {error_msg}")
        return None
    
    try:
        if DEBUG_MODE:
            print(f"[🔄 Calling Kimi API...]")
        
        url = "https://api.moonshot.ai/v1/chat/completions"
        
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
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if DEBUG_MODE:
            print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "").strip()
                
                if content:
                    if DEBUG_MODE:
                        print(f"  ✅ Success! Response length: {len(content)} characters")
                    return content
        
        if DEBUG_MODE:
            print(f"  ❌ API Error: {response.status_code}")
        return None
    
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ❌ Exception: {type(e).__name__}: {str(e)}")
        return None


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """Generate AI response based on the selected mode"""
    
    if DEBUG_MODE:
        print(f"\n{'='*80}")
        print(f"[📝 generate_response called]")
        print(f"  mode: {mode}")
        print(f"  user: {user}")
        print(f"  message: {user_message[:50]}...")
    
    if mode == "Control":
        return "(This is the control group - no AI intervention)"
    
    system_prompt = _get_system_prompt(mode)
    
    # ✅ 统一调用API - 不再有重复代码
    response = _call_kimi_api(system_prompt, user_message, max_tokens=300)
    
    if response:
        return response
    else:
        return _get_fallback(mode)


def _get_system_prompt(mode):
    """Get system prompt based on mode"""
    
    if "Scaffolded" in mode:
        return (
            "You are a Socratic tutor with expertise in critical thinking. "
            "Your role is to: "
            "1. Ask insightful questions that help students think deeper "
            "2. Never give direct answers, but guide students to discover themselves "
            "3. Challenge assumptions and request evidence "
            "4. Encourage students to think from multiple perspectives. "
            "Keep your responses concise and thought-provoking."
        )
    
    elif "Debater" in mode:
        return (
            "You are an expert critical debater and logical analyst. "
            "Your role is to: "
            "1. Identify logical flaws and weaknesses in arguments "
            "2. Present strong counter-arguments using words like 'However', 'On the contrary', 'I disagree' "
            "3. Provide concrete examples or alternative explanations "
            "4. Demand stronger evidence and support "
            "5. Maintain a respectful and constructive tone. "
            "Focus on the logic and evidence, not the person."
        )
    
    else:
        return "You are a helpful AI assistant. Answer clearly and directly."


def _get_fallback(mode):
    """Fallback responses in English"""
    
    if "Scaffolded" in mode:
        options = [
            "That's interesting. Could you elaborate on why you think so?",
            "What do you believe is the underlying cause of this?",
            "Is there any specific evidence that supports your view?",
            "What would happen if the opposite were true?",
            "What assumptions are you making here?",
        ]
    elif "Debater" in mode:
        options = [
            "I understand your point, but let me challenge it from a different angle.",
            "Have you considered the potential downsides or counterexamples?",
            "Can you provide more concrete evidence for this argument?",
            "Does this logic really apply to all possible scenarios?",
            "I see your reasoning, but I respectfully disagree. Here's why:",
        ]
    else:
        options = [
            "Please continue.",
            "That's a point worth considering.",
            "Could you give a specific example?",
            "I see. Tell me more about this.",
        ]
    
    return random.choice(options)


def generate_argument_map(messages, topic):
    """
    ✅ 改进版本：使用结构化提示生成规范的论证分析表格
    - 清晰的表格格式
    - 论证共识部分
    - 核心分歧部分
    - 后续讨论建议
    """
    # 整理对话历史
    history_text = ""
    for m in messages:
        user_name = m.get('user', 'Unknown')
        content = m.get('message', '')
        if content:
            history_text += f"{user_name}: {content}\n"
    
    # ✅ 改进的英文提示 - 结构更清晰
    prompt = f"""
You are an expert in argumentation analysis and critical thinking.

TASK: Analyze the following discussion about: "{topic}"

OUTPUT FORMAT (MUST follow exactly):

## 🎯 Core Conclusion
[One sentence summary of the main discussion outcome]

## 📊 Structured Argument Table
| Participant | Stance | Core Argument | Supporting Evidence |
|---|---|---|---|
| [Name] | [Support/Oppose/Neutral] | [Main claim in 1 sentence] | [Key reasons/examples] |

(Create one row for each distinct participant position)

## 🤝 Discussion Consensus
List 2-3 points that both sides agree on or acknowledge.

## ⚔️ Core Disagreement
List 2-3 main points where the participants fundamentally disagree.

## 💭 Suggestions for Deeper Discussion
1. [Specific question exploring tension between positions]
2. [Specific question about evidence or assumptions]
3. [Specific question about long-term implications]

---
Discussion History:
{history_text}

Please provide your analysis in clear, structured English with markdown formatting.
"""
    
    # ✅ 用改进的API调用 - 允许更长的响应
    response = _call_kimi_api(
        system_prompt="You are an expert argumentation analyst. Provide structured, markdown-formatted analysis.",
        user_message=prompt,
        max_tokens=800  # 允许更长的分析
    )
    
    if response:
        return response
    else:
        return "⚠️ Unable to generate argument map. Please try again."


# End of file