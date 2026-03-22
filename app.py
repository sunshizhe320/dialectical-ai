import streamlit as st
import time
import io
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from ai_agent import generate_response, generate_argument_map


# 尝试导入新模块，如果不存在则跳过
try:
    from ai_scaffolding import classify_message_type, generate_scaffolding_questions, extract_core_viewpoints
except:
    classify_message_type = None

st.set_page_config(
    page_title="Dialectical AI Partner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== File system storage for cross-device synchronization ==========

SESSIONS_FILE = "sessions_data.json"
PARTICIPANTS_FILE = "participants_data.json"

def load_all_sessions():
    """Load all sessions from file"""
    if Path(SESSIONS_FILE).exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_sessions(data):
    """Save all sessions to file"""
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Failed to save sessions: {e}")

def load_all_participants():
    """Load all participants from file"""
    if Path(PARTICIPANTS_FILE).exists():
        try:
            with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_participants(data):
    """Save all participants to file"""
    try:
        with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Failed to save participants: {e}")

def get_or_create_session(team_name, topic, mode, created_by):
    """Get or create session - include mode in session ID"""
    all_sessions = load_all_sessions()
    
    team_name = team_name.strip()
    topic = topic.strip()
    mode = mode.strip()
    
    for sid, info in all_sessions.items():
        existing_team = info.get("team_name", "").strip()
        existing_topic = info.get("topic", "").strip()
        existing_mode = info.get("mode", "").strip()
        
        if (existing_team == team_name and 
            existing_topic == topic and 
            existing_mode == mode):
            print(f"✅ Found existing session: {sid}")
            return sid
    
    topic_short = topic.replace('?', '').replace('？', '')[:20]
    session_id = f"{team_name}_{topic_short}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    all_sessions[session_id] = {
        "team_name": team_name,
        "topic": topic,
        "mode": mode,
        "created_at": datetime.now().isoformat(),
        "created_by": created_by,
        "messages": []
    }
    
    save_all_sessions(all_sessions)
    return session_id

def add_participant(session_id, user_name):
    """Add participant"""
    all_participants = load_all_participants()
    
    if session_id not in all_participants:
        all_participants[session_id] = {}
    
    all_participants[session_id][user_name] = datetime.now().isoformat()
    save_all_participants(all_participants)

def get_session_participants(session_id):
    """Get active participants"""
    all_participants = load_all_participants()
    
    if session_id not in all_participants:
        return []
    
    cutoff = datetime.now() - timedelta(minutes=5)
    active = []
    
    for user, last_active in all_participants[session_id].items():
        try:
            if datetime.fromisoformat(last_active) > cutoff:
                active.append(user)
        except:
            pass
    
    return active

def save_message(session_id, user, role, message):
    """Save message"""
    all_sessions = load_all_sessions()
    
    if session_id not in all_sessions:
        return
    
    all_sessions[session_id]["messages"].append({
        "user": user,
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    
    save_all_sessions(all_sessions)

def get_history(session_id, limit=100):
    """Get conversation history"""
    all_sessions = load_all_sessions()
    
    if session_id not in all_sessions:
        return []
    
    messages = all_sessions[session_id].get("messages", [])
    return messages[-limit:] if len(messages) > limit else messages

def get_session_info(session_id):
    """Get session info"""
    all_sessions = load_all_sessions()
    
    if session_id not in all_sessions:
        return None
    
    info = all_sessions[session_id]
    return {
        "team_name": info.get("team_name"),
        "topic": info.get("topic"),
        "mode": info.get("mode"),
        "created_at": info.get("created_at"),
        "created_by": info.get("created_by")
    }

# ========== CSS styling ==========
st.markdown("""
<style>
    @keyframes blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-10px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    .welcome-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 40px;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
    }
    
    .welcome-header {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .welcome-header h1 {
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 10px;
    }
    
    .welcome-header p {
        color: #666;
        font-size: 1.1rem;
    }
    
    .mode-card {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1976d2;
        margin-bottom: 15px;
    }
    
    .session-panel {
        background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        padding: 16px;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 16px;
    }
    
    .session-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        font-size: 0.95rem;
    }
    
    .timer {
        font-weight: 700;
        color: #ff6b6b;
        font-size: 1.2rem;
    }
    
    .ai-bubble {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 12px 14px;
        border-radius: 10px;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(76, 175, 80, 0.15);
        border-left: 3px solid #4caf50;
        word-wrap: break-word;
        animation: slideIn 0.3s ease-out;
    }
    
    .student-bubble {
        background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%);
        padding: 12px 14px;
        border-radius: 10px;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(31, 119, 180, 0.1);
        border-right: 3px solid #1f77b4;
        margin-left: auto;
        word-wrap: break-word;
        animation: slideIn 0.3s ease-out;
    }
    
    .bubble-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    
    .speaker-name {
        font-weight: 700;
        font-size: 0.85rem;
        color: #333;
    }
    
    .timestamp {
        font-size: 0.7rem;
        color: #999;
    }
    
    .message-content {
        font-size: 0.9rem;
        line-height: 1.5;
        color: #333;
    }
    
    .ai-hint {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        margin-bottom: 12px;
        color: #856404;
    }
    
    .team-info-card {
        background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #7b1fa2;
        margin-bottom: 15px;
    }
    
    .topic-card {
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    h1, h2, h3 {
        color: #1f77b4;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ========== Session State ==========
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "team_name" not in st.session_state:
    st.session_state.team_name = None
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = None

# Auto-refresh
if st.session_state.session_started:
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    if (datetime.now() - st.session_state.last_refresh).total_seconds() > 1.0:
        st.session_state.last_refresh = datetime.now()
        st.rerun()

# ========== AI Mode Configuration ==========
MODE_OPTIONS = {
    "AI-Scaffolded": {
        "name": "🎓 Socratic Tutoring",
        "description": "AI will guide you to think deeply through questions",
        "icon": "🎓"
    },
    "AI-Free-Debater": {
        "name": "⚔️ Active Debater",
        "description": "AI will present counterarguments and request evidence",
        "icon": "⚔️"
    },
    "Control": {
        "name": "👥 Human-Only Discussion",
        "description": "No AI intervention, free discussion",
        "icon": "👥"
    }
}

def stream_ai_response(ai_reply, placeholder_container):
    """Stream AI response"""
    if not ai_reply:
        placeholder_container.markdown("""
        <div class="ai-bubble">
            <div class="bubble-header">
                <span class="speaker-name">🤖 AI Assistant</span>
                <span class="timestamp">❌ Error</span>
            </div>
            <div class="message-content">AI service temporarily unavailable, please try again later</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    displayed_text = ""
    
    for char in ai_reply:
        displayed_text += char
        placeholder_container.markdown(f"""
        <div class="ai-bubble">
            <div class="bubble-header">
                <span class="speaker-name">🤖 AI Assistant</span>
                <span class="timestamp" style="color: #ff6b6b;">⏳</span>
            </div>
            <div class="message-content">{displayed_text}<span style="animation: blink 0.7s infinite;">▌</span></div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(0.02)
    
    placeholder_container.markdown(f"""
    <div class="ai-bubble">
        <div class="bubble-header">
            <span class="speaker-name">🤖 AI Assistant</span>
            <span class="timestamp">{datetime.now().strftime("%H:%M:%S")}</span>
        </div>
        <div class="message-content">{displayed_text}</div>
    </div>
    """, unsafe_allow_html=True)

# ========== Login Page ==========
if not st.session_state.session_started:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-header">
            <h1>📱 Dialectical AI Partner</h1>
            <p>Critical Thinking & Collaborative Learning Platform</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("""
    ## 🎓 Research Project Introduction
    
    This research explores how **generative AI as a dialectical partner** promotes students' critical thinking development.
    
    ### 📋 What You'll Experience:
    - **Deep Discussion**: Discuss around self-defined topics
    - **👥 Team Collaboration**: Multiple members join the same group to discuss together
    - **🤖 AI Assistance**: Receive discussion support in different ways
    - **📊 Real-time Analysis**: System automatically analyzes critical thinking indicators
    
    ### 💡 How to Join a Group
    **Important:** Join the same discussion with other group members by filling in the **same "Group Name" and "Discussion Topic"**!
    
    **Example:**
    - Group Name: `Group1`
    - Discussion Topic: `Should AI be allowed to participate in K-12 education?`
    
    If two people fill in exactly the same information, they'll automatically sync to one interface!
    """)
    
    st.divider()
    
    st.markdown("## 🎯 Discussion Setup")
    
    col1, col2 = st.columns([0.5, 0.5])
    
    with col1:
        st.markdown("### 👤 Basic Information")
        user_name = st.text_input(
            "Your Name/Nickname",
            placeholder="Enter your name",
            max_chars=20,
            key="login_username"
        )
        
        team_name = st.text_input(
            "🏢 Group Name (Must be the same as group members!)",
            placeholder="e.g.: Group1, Team A",
            max_chars=30,
            key="login_team"
        )
    
    with col2:
        st.markdown("### 🤖 AI Mode Selection")
        mode_select = st.selectbox(
            "Select AI Discussion Mode",
            list(MODE_OPTIONS.keys()),
            format_func=lambda x: MODE_OPTIONS[x]["name"],
            key="login_mode"
        )
    
    st.divider()
    
    st.markdown("### 📌 Discussion Topic")
    st.info("💡 Enter the topic you want to discuss. **Group members must enter the same topic** to join the same discussion")
    
    topic = st.text_area(
        "Discussion Topic",
        placeholder="e.g.: Should companies adopt remote work policies?",
        height=100,
        key="login_topic"
    )
    
    if mode_select:
        mode_info = MODE_OPTIONS[mode_select]
        st.markdown(f"""
        <div class="mode-card">
            <strong>{mode_info['name']}</strong><br><br>
            {mode_info['description']}
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
    
    with col2:
        consent = st.checkbox("✅ I have read and agree to participate in this research")
        
        if st.button("🚀 Enter Discussion", use_container_width=True):
            if not user_name.strip():
                st.error("❌ Please enter your name")
            elif not team_name.strip():
                st.error("❌ Please enter group name")
            elif not topic.strip():
                st.error("❌ Please enter discussion topic")
            elif not consent:
                st.error("❌ Please agree to participate in this research")
            else:
                session_id = get_or_create_session(
                    team_name=team_name.strip(),
                    topic=topic.strip(),
                    mode=mode_select,
                    created_by=user_name.strip()
                )
                
                add_participant(session_id, user_name.strip())
                
                st.session_state.session_id = session_id
                st.session_state.user_name = user_name.strip()
                st.session_state.team_name = team_name.strip()
                st.session_state.session_started = True
                st.session_state.session_start_time = datetime.now()
                
                st.success(f"✅ Successfully entered discussion!")
                time.sleep(1)
                st.rerun()

# ========== Discussion Page ==========
else:
    session_info = get_session_info(st.session_state.session_id)
    
    if not session_info:
        st.error("❌ Session information lost, please re-login")
        if st.button("Return to Login"):
            st.session_state.session_started = False
            st.rerun()
    else:
        topic = session_info.get("topic", "Discussion Topic")
        team_name = session_info.get("team_name", "Group")
        mode = session_info.get("mode", "Control")
        mode_info = MODE_OPTIONS.get(mode, {})
        
        add_participant(st.session_state.session_id, st.session_state.user_name)
        current_participants = get_session_participants(st.session_state.session_id)
        current_history = get_history(st.session_state.session_id, limit=500)
        
        # Sidebar
        with st.sidebar:
            st.title("📱 Dialectical AI")
            
            st.markdown("### 👥 Session Information")
            st.markdown(f"""
            <div class="team-info-card">
                <strong>🏢 Group Name:</strong> {team_name}<br>
                <strong>👤 Your Name:</strong> {st.session_state.user_name}<br>
                <strong>🤖 AI Mode:</strong> {mode_info.get('name', 'Unknown')}<br>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
           
            st.markdown("### 📊 Session Status")
            
            elapsed = datetime.now() - st.session_state.session_start_time
            remaining = max(0, 2400 - int(elapsed.total_seconds()))
            minutes = remaining // 60
            seconds = remaining % 60
            
            st.markdown(f"""
            <div class="session-panel">
                <div class="session-item">
                    <span>💬 Messages:</span>
                    <strong>{len(current_history)}</strong>
                </div>
                <div class="session-item">
                    <span>👥 Group Members:</span>
                    <strong>{len(current_participants)}</strong>
                </div>
                <div class="session-item">
                    <span>⏱️ Time Remaining:</span>
                    <span class="timer">{minutes:02d}:{seconds:02d}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown("**👥 Active Group Members**")
            if current_participants:
                for member in current_participants:
                    if member == st.session_state.user_name:
                        st.caption(f"✓ 🟢 {member} (you)")
                    else:
                        st.caption(f"● 🔵 {member}")
            else:
                st.caption("No active members")
            
            st.divider()
            
            st.markdown(f"""
            <div class="topic-card">
                <strong>📌 Discussion Topic:</strong><br><br>
                {topic}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown(f"""
            <div class="mode-card">
                <strong>{mode_info.get('name', 'Unknown Mode')}</strong><br><br>
                {mode_info.get('description', '')}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            if st.button("📥 Export Discussion Record", use_container_width=True):
                history = get_history(st.session_state.session_id, limit=1000)
                if history:
                    buffer = io.StringIO()
                    writer = csv.writer(buffer)
                    writer.writerow(["User", "Role", "Message", "Time"])
                    for h in history:
                        writer.writerow([h["user"], h["role"], h["message"], h["timestamp"]])
                    st.download_button(
                        "📥 Download CSV",
                        buffer.getvalue(),
                        f"discussion_record_{team_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
        
        # Main Area
        st.markdown(f"## 💬 {team_name} Discussion")
        
        members_str = ", ".join(current_participants) if current_participants else "No members"
        st.markdown(f"**👥 Participants:** {members_str}")
        st.markdown(f"**📌 Topic:** {topic}")
        
        st.divider()
        
        if mode != "Control":
            st.markdown("""
            <div class="ai-hint">
                💡 <strong>Tip:</strong> Use <code>@AI</code> in your message to mention AI for help.
            </div>
            """, unsafe_allow_html=True)
        
        progress = min(len(current_history) / 40, 1.0)
        st.progress(progress, f"📊 {len(current_history)} messages")
        
        # Discussion History
        st.markdown("### 💬 Discussion History")
        
        history = get_history(st.session_state.session_id, limit=500)
        
        if history:
            for msg in history:
                role = msg["role"]
                user = msg["user"]
                content = msg["message"]
                timestamp = msg["timestamp"]
                
                try:
                    time_obj = datetime.fromisoformat(timestamp)
                    time_str = time_obj.strftime("%H:%M:%S")
                except:
                    time_str = ""
                
                if role == "assistant" or user == "AI":
                    col1, col2 = st.columns([0.08, 0.92])
                    with col2:
                        st.markdown(f"""
                        <div class="ai-bubble">
                            <div class="bubble-header">
                                <span class="speaker-name">🤖 AI Assistant</span>
                                <span class="timestamp">{time_str}</span>
                            </div>
                            <div class="message-content">{content}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    col1, col2 = st.columns([0.92, 0.08])
                    with col1:
                        is_self = user == st.session_state.user_name
                        has_ai_mention = "@AI" in content or "@ai" in content or "＠AI" in content
                        
                        bubble_html = f"""
                        <div class="student-bubble" style="{'border: 2px solid #ff9800;' if has_ai_mention else ''}">
                            <div class="bubble-header">
                                <span class="speaker-name">👤 {user} {'(you)' if is_self else ''} {('🔔' if has_ai_mention else '')}</span>
                                <span class="timestamp">{time_str}</span>
                            </div>
                            <div class="message-content">{content}</div>
                        </div>
                        """
                        
                        st.markdown(bubble_html, unsafe_allow_html=True)
        else:
            st.info("💭 Start discussing!")
        
        # Message Input
        st.markdown("### ✏️ Your Message")
        
        col1, col2, col3 = st.columns([0.72, 0.14, 0.14])
        
        with col1:
            user_input = st.text_area(
                "",
                placeholder="Share your thoughts... (use @AI to mention AI)",
                height=80,
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("")
            send_btn = st.button("📤 Send", use_container_width=True)
        
        with col3:
            st.write("")
            clear_btn = st.button("🗑️ Clear", use_container_width=True)
        
        # Handle Send
        if send_btn:
            if user_input.strip():
                save_message(
                    st.session_state.session_id, 
                    st.session_state.user_name, 
                    "user", 
                    user_input
                )
                add_participant(st.session_state.session_id, st.session_state.user_name)
                
                ai_triggered = "@AI" in user_input or "@ai" in user_input or "＠AI" in user_input
                
                if ai_triggered and mode != "Control":
                    conversation_history = get_history(st.session_state.session_id, limit=20)
                    
                    with st.spinner("🤖 AI is thinking..."):
                        try:
                            print(f"\n[APP] Calling generate_response with mode={mode}", flush=True)
                            ai_reply = generate_response(
                                mode,
                                user_input,
                                group_id=st.session_state.session_id,
                                user=st.session_state.user_name,
                                conversation_history=conversation_history
                            )
                            
                            if ai_reply:
                                save_message(
                                    st.session_state.session_id, 
                                    "AI", 
                                    "assistant", 
                                    ai_reply
                                )
                                
                                ai_placeholder = st.empty()
                                stream_ai_response(ai_reply, ai_placeholder)
                            else:
                                st.error("❌ AI returned empty result")
                        
                        except Exception as e:
                            st.error(f"❌ Error calling AI: {str(e)}")
                            print(f"Error: {e}")
                
                time.sleep(0.3)
                st.rerun()
        
        if clear_btn:
            st.rerun()
        
            if clear_btn:
              st.rerun()
        
        # ========== Analysis Sections ==========
        st.divider()
        st.markdown("## 📊 Analysis & Consensus Matrix")
        
        if "session_id" in st.session_state and st.session_state.session_id:
            all_data = load_all_sessions()
            current_sess = all_data.get(st.session_state.session_id, {})
            messages = current_sess.get("messages", [])
            participants = get_session_participants(st.session_state.session_id)
            
            # 只有在有足够数据时才显示
            if len(messages) >= 3 and len(participants) >= 2:
                
                                # ========== 提取核心观点 ==========
                def extract_core_arguments(messages):
                    """从讨论中动态提取核心论点（使用LLM）"""
                    try:
                        # 尝试使用 LLM 提取
                        from discussion_analytics import extract_claims_with_llm
                        claims = extract_claims_with_llm(messages)
                        return claims
                    except Exception as e:
                        print(f"LLM extraction error: {e}")
                        # 备用方案：简单关键词提取
                        arguments = []
                        
                        for msg in messages:
                            text = msg.get("message", "")
                            
                            # 检测论点关键词
                            if any(kw in text.lower() for kw in ['观点', '论点', '应该', '认为', 'claim', 'should']):
                                # 取第一句，最多25字符
                                sentences = text.split("。")
                                if sentences[0]:
                                    arg = sentences[0][:25]
                                    if arg not in arguments and len(arg) > 3:
                                        arguments.append(arg)
                        
                        # 如果还是没提取到，用通用值
                        if not arguments:
                            arguments = ["观点A", "观点B", "观点C"]
                        
                        return arguments[:4]
                
                core_arguments = extract_core_arguments(messages)
                
                # ========== 构建共识矩阵 ==========
                def build_consensus_matrix(participants, messages, arguments):
                    """构建共识矩阵"""
                    import pandas as pd
                    
                    matrix_data = []
                    
                    for participant in participants:
                        row = {}
                        for arg in arguments:
                            # 获取该参与者对该论点的立场
                            stance = "△"  # 默认中立
                            
                            # 查找该参与者的所有消息
                            participant_msgs = [m.get("message", "").lower() for m in messages if m.get("user") == participant]
                            combined_text = " ".join(participant_msgs)
                            
                            # 检查是否提到该论点
                            if arg.lower() in combined_text:
                                # 检查赞成/反对的关键词
                                if any(w in combined_text for w in ['赞成', '同意', '支持', '对', 'agree', 'yes', '+1']):
                                    stance = "✅"
                                elif any(w in combined_text for w in ['反对', '不同意', '反驳', 'disagree', 'no', '-1']):
                                    stance = "❌"
                            
                            row[arg] = stance
                        
                        matrix_data.append(row)
                    
                    return pd.DataFrame(matrix_data, index=participants)
                
                # ========== 显示标签页 ==========
                tab1, tab2, tab3 = st.tabs(["📊 Consensus Matrix", "📈 Convergence Analysis", "💬 Mutual Feedback"])
                
                with tab1:
                    st.subheader("📊 Consensus Matrix")
                    
                    import pandas as pd
                    from ai_agent import generate_response
                    
                    # ========== 提取观点函数 ==========
                    def extract_viewpoints_local(messages):
                        """从讨论中提取核心观点"""
                        if not messages or len(messages) < 2:
                            return ["观点A", "观点B", "观点C"]
                        
                        try:
                            # 准备讨论文本
                            discussion = "\n".join([
                                f"{m.get('user', 'Unknown')}: {m.get('message', '')}"
                                for m in messages[-10:]
                            ])
                            
                            if len(discussion) > 1500:
                                discussion = discussion[:1500]
                            
                            # 调用 API（用 Scaffolded 模式）
                            prompt = f"""Extract 3-4 key viewpoints from this discussion. Each viewpoint should be ONE SHORT sentence (max 15 words).

Discussion:
{discussion}

List each viewpoint on a new line, no numbers or bullets:"""
                            
                            response = generate_response(
                                mode="Scaffolded",
                                user_message=prompt,
                                group_id=st.session_state.session_id,
                                user="System"
                            )
                            
                            if response:
                                viewpoints = []
                                for line in response.split('\n'):
                                    line = line.strip()
                                    
                                    # 跳过空行和太短的内容
                                    if not line or len(line) < 5 or len(line) > 80:
                                        continue
                                    
                                    # 移除开头数字
                                    cleaned = line
                                    for prefix in ['1.', '2.', '3.', '4.', '-', '•']:
                                        if cleaned.startswith(prefix):
                                            cleaned = cleaned[len(prefix):].strip()
                                            break
                                    
                                    if cleaned and len(cleaned) >= 5:
                                        viewpoints.append(cleaned[:70])  # 限制长度
                                
                                if len(viewpoints) >= 3:
                                    return viewpoints[:4]
                        
                        except Exception as e:
                            print(f"⚠️ 提取观点错误: {e}")
                        
                        return ["观点A", "观点B", "观点C"]
                    
                    # ========== 获取观点 ==========
                    with st.spinner("🤖 AI 正在分析讨论内容..."):
                        core_viewpoints = extract_viewpoints_local(messages)
                    
                    # ========== 构建矩阵 ==========
                    matrix_data = []
                    
                    for participant in participants:
                        row = {}
                        participant_messages = [
                            m.get("message", "")
                            for m in messages
                            if m.get("user") == participant
                        ]
                        participant_text = " ".join(participant_messages).lower()
                        
                        for viewpoint in core_viewpoints:
                            stance = "△"
                            
                            agree_keywords = ['赞成', '同意', '支持', 'agree', 'yes', 'beneficial', 'support']
                            disagree_keywords = ['反对', '不同意', 'disagree', 'no', 'concerns', 'problem']
                            
                            has_agree = any(kw in participant_text for kw in agree_keywords)
                            has_disagree = any(kw in participant_text for kw in disagree_keywords)
                            
                            if has_agree and not has_disagree:
                                stance = "✅"
                            elif has_disagree and not has_agree:
                                stance = "❌"
                            
                            row[viewpoint] = stance
                        
                        matrix_data.append(row)
                    
                    # 创建 DataFrame
                    df = pd.DataFrame(matrix_data, index=participants)
                    
                    # 定义样式
                    def style_cells(val):
                        if val == "✅":
                            return 'background-color: #90EE90; color: #000; font-weight: bold; font-size: 18px; text-align: center;'
                        elif val == "❌":
                            return 'background-color: #FFB6C6; color: #000; font-weight: bold; font-size: 18px; text-align: center;'
                        else:
                            return 'background-color: #FFE4B5; color: #000; font-weight: bold; font-size: 14px; text-align: center;'
                    
                    # 显示表格
                    styled_df = df.style.applymap(style_cells)
                    st.dataframe(styled_df, use_container_width=True)
                    
                    st.divider()
                    
                    # 图例
                    st.markdown("**Legend:** ✅ Agree (赞成)  |  ❌ Disagree (反对)  |  △ Neutral (中立)")
                with tab2:
                    st.subheader("📈 Convergence Analysis")
                    
                    # 计算收敛度
                    convergence_data = {}
                    for arg in core_arguments:
                        stances = [df.loc[p, arg] for p in participants if p in df.index]
                        agree_count = sum(1 for s in stances if s == "✅")
                        convergence_data[arg] = {
                            "agree": agree_count,
                            "total": len(stances),
                            "rate": agree_count / len(stances) if stances else 0
                        }
                    
                    # 总体收敛度
                    total_agree = sum(d["agree"] for d in convergence_data.values())
                    total_votes = sum(d["total"] for d in convergence_data.values())
                    overall_rate = total_agree / total_votes if total_votes > 0 else 0
                    
                    st.markdown(f"### 🎯 Overall Consensus: {overall_rate*100:.1f}%")
                    st.progress(overall_rate)
                    
                    st.divider()
                    
                    st.markdown("**Breakdown by Viewpoint:**")
                    for arg, data in convergence_data.items():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(arg)
                        with col2:
                            rate = data["rate"]
                            st.progress(rate, f"{data['agree']}/{data['total']}")
                    
                    st.divider()
                    
                    # 根据收敛度给出建议
                    st.markdown("### 💡 Guidance")
                    if overall_rate >= 0.9:
                        st.success("🎉 Excellent! Your group has achieved strong consensus. Well done!")
                    elif overall_rate >= 0.6:
                        st.info("🔄 Good progress! Consider one more round to address remaining disagreements.")
                    elif overall_rate >= 0.3:
                        st.warning("⚠️ Significant differences remain. Continue deep discussion to build bridges.")
                    else:
                        st.error("❌ Major disagreement. Use Comments on each other to understand different perspectives.")
                
                with tab3:
                    st.subheader("💬 Mutual Feedback & Next Steps")
                    
                    st.markdown("""
                    ### 🎯 How to Build on Each Other's Ideas:
                    
                    **1. Comments on Each Other (互评)**
                    - Ask clarifying questions about others' viewpoints
                    - Share what you agree with in others' perspectives
                    - Example: "我同意你的观点，但我想补充..."
                    
                    **2. Express Your Stance (立场表达)**
                    - Use clear language: "我赞成/反对..."
                    - Provide reasons and evidence
                    - Example: "我反对这个观点，因为..."
                    
                    **3. Build Consensus (构建共识)**
                    - Find common ground between different viewpoints
                    - Propose compromises or integrated solutions
                    - Example: "也许我们可以..."
                    
                    ### 📊 Current Status:
                    """)
                    
                    # 显示现在的共识情况
                    agree_points = [arg for arg, data in convergence_data.items() if data["rate"] == 1.0]
                    disagree_points = [arg for arg, data in convergence_data.items() if data["rate"] == 0]
                    
                    if agree_points:
                        st.success(f"✅ **Full Consensus on:** {', '.join(agree_points)}")
                    
                    if disagree_points:
                        st.error(f"❌ **Major Disagreement on:** {', '.join(disagree_points)}")
                    
                    # AI建议
                    st.markdown("""
                    ### 🤖 AI Suggestions for Deeper Discussion:
                    """)
                    
                    st.markdown("""
                    - **For Points with Full Consensus:** Solidify your agreement by explaining WHY you all agree
                    - **For Disagreement:** Use @AI to ask for perspective from the other side
                    - **For Neutral Points:** Share concrete examples or evidence to clarify your position
                    """)
            
            else:
                st.info(f"💭 **Waiting for more data...** \n\nConsensus Matrix will appear when you have:\n- At least 2 participants (current: {len(participants)})\n- At least 3 messages (current: {len(messages)})\n\nKeep discussing!")