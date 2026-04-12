"""
ai_agent.py - Full Version with Logging + Latency + Token Usage
"""

import os
import sys
import random
import json
import time
from dotenv import load_dotenv
import streamlit as st
import requests

load_dotenv()

# 强制刷新输出缓冲
sys.stdout = sys.stderr

MOONSHOT_KEY = None

try:
    if hasattr(st, 'secrets') and st.secrets:
        MOONSHOT_KEY = st.secrets.get("MOONSHOT_API_KEY")
        if MOONSHOT_KEY:
            print(f"✅ MOONSHOT_API_KEY loaded from Streamlit Secrets", flush=True)
except Exception as e:
    print(f"⚠️ Unable to read from Secrets: {e}", flush=True)

if not MOONSHOT_KEY:
    MOONSHOT_KEY = os.getenv("MOONSHOT_API_KEY")
    if MOONSHOT_KEY:
        print(f"✅ MOONSHOT_API_KEY loaded from Environment Variables", flush=True)

print(f"\n{'='*80}", flush=True)
print(f"[🔧 AI Agent Initialization]", flush=True)
if MOONSHOT_KEY:
    print(f"✅ MOONSHOT_API_KEY is SET (Length: {len(MOONSHOT_KEY)})", flush=True)
else:
    print(f"❌ MOONSHOT_API_KEY is NOT SET!", flush=True)
print(f"{'='*80}\n", flush=True)

DEBUG_MODE = True


def _log(message):
    """统一日志函数，确保输出到控制台"""
    print(message, flush=True)


def _call_kimi_api(system_prompt, user_message, max_tokens=500):
    """
    Unified API Call with Complete Error Logging
    ✅ Returns (content, metadata)
    """
    _log(f"\n[🔄 _call_kimi_api START]")
    _log(f"  MOONSHOT_KEY: {bool(MOONSHOT_KEY)}")
    _log(f"  max_tokens: {max_tokens}")
    
    metadata = {
        "success": False,
        "latency": 0.0,
        "tokens_used": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "error_code": None,
        "error_message": None
    }
    
    if not MOONSHOT_KEY:
        _log(f"❌ MOONSHOT_KEY is None!")
        metadata["error_code"] = "NO_API_KEY"
        metadata["error_message"] = "API Key not set"
        return None, metadata
    
    start_time = time.time()
    
    try:
        _log(f"[📝 Preparing request]")
        _log(f"  System Prompt Length: {len(system_prompt)}")
        _log(f"  User Message Length: {len(user_message)}")
        
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_KEY}"
        }
        
        full_system_prompt = system_prompt + "\n\n[FINAL INSTRUCTION]: Always respond in English, never in other languages."
        
        payload = {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens
        }
        
        _log(f"[📤 Sending POST request to {url}]")
        _log(f"  Headers: {list(headers.keys())}")
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        latency = time.time() - start_time
        metadata["latency"] = latency
        
        _log(f"[📥 Response received]")
        _log(f"  Status Code: {response.status_code}")
        _log(f"  Response Length: {len(response.text)}")
        _log(f"  Response Text: {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                _log(f"  Response JSON parsed successfully")
                _log(f"  Response Keys: {list(result.keys())}")
                
                # ✅ 提取 tokens
                usage = result.get("usage", {})
                metadata["tokens_input"] = usage.get("prompt_tokens", 0)
                metadata["tokens_output"] = usage.get("completion_tokens", 0)
                metadata["tokens_used"] = usage.get("total_tokens", 0)
                
                if "choices" in result:
                    _log(f"  Choices count: {len(result['choices'])}")
                    
                    if len(result["choices"]) > 0:
                        choice = result["choices"][0]
                        _log(f"  Choice keys: {list(choice.keys())}")
                        
                        message = choice.get("message", {})
                        content = message.get("content", "").strip()
                        
                        _log(f"  Content length: {len(content)}")
                        _log(f"  Content preview: {content[:100]}...")
                        
                        if content:
                            _log(f"✅ API Call Success! Got {len(content)} chars")
                            _log(f"[🔄 _call_kimi_api END - SUCCESS]")
                            metadata["success"] = True
                            return content, metadata
                        else:
                            _log(f"❌ Content is empty")
                    else:
                        _log(f"❌ No choices in result")
                else:
                    _log(f"❌ No 'choices' key in response")
                    
            except json.JSONDecodeError as je:
                _log(f"❌ JSON Parse Error: {str(je)}")
                _log(f"  Response text: {response.text[:200]}")
                metadata["error_code"] = "JSON_ERROR"
                metadata["error_message"] = str(je)
        else:
            _log(f"❌ HTTP Error {response.status_code}")
            _log(f"  Response: {response.text[:300]}")
            metadata["error_code"] = str(response.status_code)
            metadata["error_message"] = response.text[:200]
        
        _log(f"[🔄 _call_kimi_api END - FAILED]")
        return None, metadata
    
    except requests.Timeout as te:
        _log(f"❌ Request Timeout: {str(te)}")
        _log(f"[🔄 _call_kimi_api END - TIMEOUT]")
        metadata["error_code"] = "TIMEOUT"
        metadata["error_message"] = str(te)
        metadata["latency"] = time.time() - start_time
        return None, metadata
    
    except requests.ConnectionError as ce:
        _log(f"❌ Connection Error: {str(ce)}")
        _log(f"[🔄 _call_kimi_api END - CONNECTION ERROR]")
        metadata["error_code"] = "CONNECTION_ERROR"
        metadata["error_message"] = str(ce)
        metadata["latency"] = time.time() - start_time
        return None, metadata
    
    except Exception as e:
        _log(f"❌ Unexpected Exception: {type(e).__name__}: {str(e)}")
        import traceback
        _log(traceback.format_exc())
        _log(f"[🔄 _call_kimi_api END - EXCEPTION]")
        metadata["error_code"] = "EXCEPTION"
        metadata["error_message"] = str(e)
        metadata["latency"] = time.time() - start_time
        return None, metadata


def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """Generate AI response based on mode"""
    
    _log(f"\n[🎯 generate_response START]")
    _log(f"  mode: {mode}")
    _log(f"  user: {user}")
    _log(f"  message: {user_message[:50]}...")
    
    if mode == "Control":
        _log(f"  Control mode detected - no AI intervention")
        _log(f"[🎯 generate_response END]")
        return "(This is the control group - no AI intervention)", {
            "success": True, "latency": 0, "tokens_used": 0, "tokens_input": 0, "tokens_output": 0
        }
    
    if not MOONSHOT_KEY:
        _log(f"❌ API Key not configured")
        _log(f"[🎯 generate_response END - Using Fallback]")
        return _get_fallback(mode), {
            "success": False, "latency": 0, "tokens_used": 0, "tokens_input": 0, "tokens_output": 0,
            "error_code": "NO_API_KEY", "error_message": "API Key not configured"
        }
    
    system_prompt = _get_system_prompt(mode)
    
    _log(f"[📞 Calling _call_kimi_api]")
    response, metadata = _call_kimi_api(system_prompt, user_message, max_tokens=300)
    
    if response:
        _log(f"✅ Got API response, returning it")
        _log(f"[🎯 generate_response END - SUCCESS]")
        return response, metadata
    else:
        _log(f"⚠️ API failed, using fallback")
        fallback = _get_fallback(mode)
        _log(f"[🎯 generate_response END - Using Fallback]")
        return fallback, metadata


def _get_system_prompt(mode):
    """
    Get system prompt based on mode
    ✅ FORCE ENGLISH OUTPUT
    """
    
    FORCE_ENGLISH = (
        "**CRITICAL INSTRUCTION**: You MUST respond ONLY in ENGLISH. "
        "No matter what language the user writes in, you must reply in English only. "
        "Do not translate, do not code-mix, do not include any non-English text. "
        "ENGLISH ONLY. ENGLISH ONLY. ENGLISH ONLY."
    )
    
    if "Scaffolded" in mode:
        return (
            f"{FORCE_ENGLISH}\n\n"
            "You are a Socratic tutor with expertise in critical thinking. "
            "Your role is to: "
            "1. Ask insightful questions that help students think deeper "
            "2. Never give direct answers, but guide students to discover themselves "
            "3. Challenge assumptions and request evidence "
            "4. Encourage students to think from multiple perspectives. "
            "Keep your responses concise and thought-provoking. "
            "Remember: RESPOND IN ENGLISH ONLY!"
        )
    
    elif "Debater" in mode:
        return (
            f"{FORCE_ENGLISH}\n\n"
            "You are an expert critical debater and logical analyst. "
            "Your role is to: "
            "1. Identify logical flaws and weaknesses in arguments "
            "2. Present strong counter-arguments using words like 'However', 'On the contrary', 'I disagree' "
            "3. Provide concrete examples or alternative explanations "
            "4. Demand stronger evidence and support "
            "5. Maintain a respectful and constructive tone. "
            "Focus on the logic and evidence, not the person. "
            "Remember: RESPOND IN ENGLISH ONLY!"
        )
    
    else:
        return (
            f"{FORCE_ENGLISH}\n\n"
            "You are a helpful AI assistant. Answer clearly and directly in English only."
        )


def _get_fallback(mode):
    """Fallback responses"""
    if "Scaffolded" in mode:
        return random.choice([
            "Could you elaborate on why you think so?",
            "What evidence supports your view?",
            "What would happen if the opposite were true?",
        ])
    elif "Debater" in mode:
        return random.choice([
            "Have you considered the downsides?",
            "Can you provide concrete evidence?",
            "Does this logic apply to all scenarios?",
        ])
    return "Please continue."


def generate_argument_map(messages, topic):
    """
    Generate structured argumentation analysis
    """
    _log(f"\n[📊 generate_argument_map START]")
    _log(f"  Messages: {len(messages)}")
    _log(f"  Topic: {topic[:50]}...")
    
    if not messages or len(messages) < 2:
        error_msg = "⚠️ Need at least 2 messages to analyze."
        _log(f"  {error_msg}")
        _log(f"[📊 generate_argument_map END - Insufficient data]")
        return error_msg
    
    history_text = ""
    for m in messages:
        user_name = m.get('user', 'Unknown')
        content = m.get('message', '')
        if content:
            history_text += f"{user_name}: {content}\n"
    
    _log(f"  History length: {len(history_text)} chars")
    
    prompt = f"""Analyze this discussion: "{topic}"

Output in this exact markdown format:

## 🎯 Core Conclusion
[1 sentence summary]

## 📊 Argument Table
| Participant | Stance | Core Argument | Evidence |
|---|---|---|---|
| Name | Support/Oppose | Claim | Reasons |

## 🤝 Consensus Points
- Point 1
- Point 2

## ⚔️ Core Disagreements
- Point 1
- Point 2

## 💭 Deeper Questions
1. Question 1
2. Question 2

---

Discussion:
{history_text}

Provide analysis in markdown format."""
    
    _log(f"[📞 Calling _call_kimi_api for argument map]")
    response, _ = _call_kimi_api(
        system_prompt="You are an expert argumentation analyst.",
        user_message=prompt,
        max_tokens=1500
    )
    
    if response and len(response) > 50:
        _log(f"✅ Got analysis response: {len(response)} chars")
        _log(f"[📊 generate_argument_map END - SUCCESS]")
        return response
    else:
        error_msg = f"⚠️ Analysis failed. Response: {response[:50] if response else 'None'}"
        _log(f"  {error_msg}")
        _log(f"[📊 generate_argument_map END - FAILED]")
        return error_msg