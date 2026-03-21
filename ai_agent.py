"""
ai_agent.py
AI Response Generation Module - Kimi (Moonshot) API
Full English Version - Section 1
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

def generate_response(mode, user_message):
    """Generate AI response based on the selected mode"""
    if not MOONSHOT_KEY:
        print("❌ Error: API Key is missing. Using Fallback mode.")
        return _get_fallback(mode)

    if mode == "Control":
        system_prompt = "You are a helpful assistant. Please answer directly and clearly."
    elif mode == "Scaffolded":
        system_prompt = (
            "You are a dialectical learning partner. Use Socratic questioning to guide thinking. "
            "Do not give answers directly. Ask about assumptions and evidence."
        )
    else: # Debater
        system_prompt = (
            "You are a critical debater. Identify logical flaws and present counter-arguments."
        )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=MOONSHOT_KEY, base_url="https://api.moonshot.cn/v1")
        
        completion = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ API Call Failed: {str(e)}")
        return _get_fallback(mode)
    
    def _get_fallback(mode):
    """Fallback responses in English"""
    if "Scaffolded" in mode:
        options = [
            "That's interesting. Could you elaborate on why you think so?",
            "What do you believe is the underlying cause of this?",
            "Is there any specific evidence that supports your view?",
            "What would happen if the opposite were true?",
        ]
    elif "Debater" in mode:
        options = [
            "I understand, but let's look at it from a critical angle.",
            "Have you considered the potential downsides?",
            "Can you provide more concrete evidence for this argument?",
            "Does this logic apply to all possible scenarios?",
        ]
    else:
        options = ["Please go on.", "That's a point worth considering.", "Could you give an example?"]
    return random.choice(options)

def generate_argument_map(messages, topic):
    """
    Analyze conversation history and extract a structured argumentation map.
    FORCED ENGLISH OUTPUT.
    """
    # 1. Clean and Organize history text
    history_text = ""
    for m in messages:
        user_name = m.get('user', 'Unknown')
        content = m.get('message', '')
        if content:
            history_text += f"{user_name}: {content}\n"
    
    # 2. Build Strict English Prompt
    prompt = f"""
    You are an educational expert in argumentation analysis. 
    Task: Analyze the discussion regarding the topic: "{topic}".
    
    STRICT REQUIREMENTS: 
    1. ALL output MUST be in English. Translate Chinese content to English.
    2. Format: A Markdown table with [Participant | Stance | Core Argument | Supporting Evidence].
    3. Include a "Current Consensus" summary.
    4. Provide 2 "Suggestions for Further Discussion".

    Discussion History:
    {history_text}
    """
    
    # Using the existing response engine
    return generate_response("Scaffolded", prompt)

# End of file