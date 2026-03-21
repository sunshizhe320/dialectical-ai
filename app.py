import streamlit as st
import time
import io
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from ai_agent import generate_response
from discourse_analysis import analyzer

load_dotenv()

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
    """Get or create session - true cross-device synchronization"""
    all_sessions = load_all_sessions()
    
    # Check if session with same team and topic exists
    for sid, info in all_sessions.items():
        if info.get("team_name") == team_name and info.get("topic") == topic:
            print(f"✅ Found existing session: {sid}")
            return sid
    
    # Create new session
    topic_short = topic.replace('?', '').replace('？', '')[:20]
    session_id = f"{team_name}_{topic_short}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    all_sessions[session_id] = {
        "team_name": team_name,
        "topic": topic,
        "mode": mode,
        "created_at": datetime.now().isoformat(),
        "created_by": created_by,
        "messages": []
    }
    
    save_all_sessions(all_sessions)
    print(f"✅ Created new session: {session_id}")
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
    """Save message - synchronize to file"""
    all_sessions = load_all_sessions()
    
    if session_id not in all_sessions:
        print(f"❌ Session does not exist: {session_id}")
        return
    
    all_sessions[session_id]["messages"].append({
        "user": user,
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    
    save_all_sessions(all_sessions)
    print(f"✅ Message saved")

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

# Auto-refresh to synchronize across devices
if st.session_state.session_started:
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    if (datetime.now() - st.session_state.last_refresh).seconds > 2:
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
    
    # Check if ai_reply is empty
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
                # Create or get session
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
        
        # ===== Main Area =====
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
                        st.markdown(f"""
                        <div class="student-bubble" style="{'border: 2px solid #ff9800;' if has_ai_mention else ''}">
                            <div class="bubble-header">
                                <span class="speaker-name">👤 {user} {'(you)' if is_self else ''} {('🔔' if has_ai_mention else '')}</span>
                                <span class="timestamp">{time_str}</span>
                            </div>
                            <div class="message-content">{content}</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("💭 Start discussing!")
        
        st.divider()
        
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
        
        # ===== Handle Send =====
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
                            ai_reply = generate_response(
                                mode,
                                user_input,
                                group_id=st.session_state.session_id,
                                user=st.session_state.user_name,
                                conversation_history=conversation_history
                            )
                            
                            if ai_reply:
                                # Save message
                                save_message(
                                    st.session_state.session_id, 
                                    "AI", 
                                    "assistant", 
                                    ai_reply
                                )
                                
                                # Display reply
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
            st.session_state.current_arg_map = None

    # --- Argumentation Map (displayed after entering discussion) ---
    if "session_id" in st.session_state and st.session_state.session_id:
            st.divider()
            st.subheader("🕸️ Real-time Argument Map")

            if st.button("🔍 Update Argument Analysis", key="update_map_final", use_container_width=True):
                from ai_agent import generate_argument_map
                
                # 【核心修正】直接在这里调用全局定义的函数
                try:
                    # 显式获取最新的 session 数据
                    all_data = load_all_sessions() 
                    current_sess = all_data.get(st.session_state.session_id, {})
                    messages = current_sess.get("messages", [])
                    
                    if len(messages) > 1:
                        with st.spinner("AI is analyzing the logic in depth..."):
                            # 注意：确保这里用的是 login_topic，和你登录时存的一致
                            topic = st.session_state.get('login_topic', 'Current Discussion')
                            map_result = generate_argument_map(messages, topic)
                            st.session_state.current_arg_map = map_result
                            st.rerun()
                    else:
                        st.warning("⚠️ Not enough messages yet. Please chat more!")
                except NameError:
                    # 万一全局找不到，这里做一个备选保护（通常不会发生，但能防止崩掉）
                    st.error("System error: load_all_sessions function is missing. Please refresh the page.")

            # Display area
            if "current_arg_map" in st.session_state and st.session_state.current_arg_map:
                with st.container(border=True):
                    st.markdown(st.session_state.current_arg_map)
                    st.caption("Note: The map reflects the current argumentation structure.")
                    if st.button("Clear Map"):
                        st.session_state.current_arg_map = None
                        st.rerun()