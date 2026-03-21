"""
ai_agent.py
AI Response Generation Module - Kimi (Moonshot) API
Full English Version with Bug Fixes
"""
import os
import re
import random
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

# Get API Key - Priority from Streamlit Secrets
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

# Print Initialization Status
print(f"\n{'='*80}")
print(f"[🔧 AI Agent Initialization]")
if MOONSHOT_KEY:
    print(f"✅ MOONSHOT_API_KEY is SET (Length: {len(MOONSHOT_KEY)})")
else:
    print(f"❌ MOONSHOT_API_KEY is NOT SET!")
print(f"{'='*80}\n")

DEBUG_MODE = True

def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """Generate AI response based on the selected mode"""
    
    if DEBUG_MODE:
        print(f"\n{'='*80}")
        print(f"[📝 generate_response called]")
        print(f"  mode: {mode}")
        print(f"  user: {user}")
        print(f"  message: {user_message[:50]}...")
        print(f"  MOONSHOT_KEY available: {bool(MOONSHOT_KEY)}")
    
    if mode == "Control":
        return "(This is the control group - no AI intervention)"
    
    if not MOONSHOT_KEY:
        error_msg = "❌ API Key not configured"
        if DEBUG_MODE:
            print(f"[❌ Error] {error_msg}")
        return error_msg
    
def generate_response(mode, user_message, group_id="", user="", conversation_history=None, custom_prompt=None):
    """Generate AI response based on the selected mode"""
    
    if DEBUG_MODE:
        print(f"\n{'='*80}")
        print(f"[📝 generate_response called]")
        print(f"  mode: {mode}")
        print(f"  user: {user}")
        print(f"  message: {user_message[:50]}...")
        print(f"  MOONSHOT_KEY available: {bool(MOONSHOT_KEY)}")
    
    if mode == "Control":
        return "(This is the control group - no AI intervention)"
    
    if not MOONSHOT_KEY:
        error_msg = "❌ API Key not configured"
        if DEBUG_MODE:
            print(f"[❌ Error] {error_msg}")
        return error_msg
    
    system_prompt = _get_system_prompt(mode)
    
    try:
        import requests
        
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
            "max_tokens": 300
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if DEBUG_MODE:
            print(f"  Status Code: {response.status_code}")
            print(f"  Response Text: {response.text[:500]}")  # ← 添加这行看完整响应
        
        if response.status_code == 200:
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "").strip()
                
                if content:
                    if DEBUG_MODE:
                        print(f"  ✅ Success!")
                        print(f"  Response length: {len(content)} characters")
                        print(f"{'='*80}\n")
                    return content
                else:
                    if DEBUG_MODE:
                        print(f"  ❌ Empty content in response")
                    return _get_fallback(mode)
        else:
            if DEBUG_MODE:
                print(f"  ❌ API Error: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
            return _get_fallback(mode)
    
    except Exception as e:
        if DEBUG_MODE:
            print(f"  ❌ Exception: {type(e).__name__}")
            print(f"  Message: {str(e)}")
            import traceback
            traceback.print_exc()  # ← 添加完整堆栈跟踪
        
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
    Analyze conversation history and extract a structured argumentation map.
    Output in English.
    """
    # Clean and organize history text
    history_text = ""
    for m in messages:
        user_name = m.get('user', 'Unknown')
        content = m.get('message', '')
        if content:
            history_text += f"{user_name}: {content}\n"
    
    # Build English Prompt
    prompt = f"""
    You are an expert in argumentation analysis and critical thinking.
    
    Task: Analyze the following discussion about: "{topic}"
    
    REQUIREMENTS (MUST output in English):
    1. Create a summary table with columns: [Participant | Stance | Core Argument | Evidence]
    2. Identify the main positions and supporting evidence
    3. Provide a brief "Current Consensus" section
    4. List 2-3 suggestions for deeper analysis or continued discussion
    
    Discussion History:
    {history_text}
    
    Please provide your analysis in clear, structured English.
    """
    
    # Use the existing response engine
    response = generate_response("AI-Scaffolded", prompt)
    return response


# End of file