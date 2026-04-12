import streamlit as st
from datetime import datetime, timedelta
st.write("DEBUG app file:", __file__)
st.write("DEBUG app loaded at:", datetime.now())
st.write("DEBUG git check:", "v2-send-fix")
import time
import io
import csv
import json

from pathlib import Path
from dotenv import load_dotenv
from consensus_matrix import ConsensusMatrix

import db
from api_wrapper import KimiAPIWrapper
from ai_agent import generate_response, generate_argument_map

db.init_db()

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
        if (existing_team == team_name and existing_topic == topic and existing_mode == mode):
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
    """Save message (legacy file storage)"""
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
    @keyframes blink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
    @keyframes slideIn { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }
    .main .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    .welcome-container { max-width: 900px; margin: 0 auto; padding: 40px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 12px; }
    .welcome-header { text-align: center; margin-bottom: 30px; }
    .welcome-header h1 { color: #1f77b4; font-size: 2.5rem; margin-bottom: 10px; }
    .welcome-header p { color: #666; font-size: 1.1rem; }
    .mode-card { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #1976d2; margin-bottom: 15px; }
    .session-panel { background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%); padding: 16px; border-radius: 10px; border-left: 4px solid #1f77b4; margin-bottom: 16px; }
    .session-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; font-size: 0.95rem; }
    .timer { font-weight: 700; color: #ff6b6b; font-size: 1.2rem; }
    .ai-bubble { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); padding: 12px 14px; border-radius: 10px; margin: 8px 0; box-shadow: 0 1px 3px rgba(76, 175, 80, 0.15); border-left: 3px solid #4caf50; word-wrap: break-word; animation: slideIn 0.3s ease-out; }
    .student-bubble { background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%); padding: 12px 14px; border-radius: 10px; margin: 8px 0; box-shadow: 0 1px 3px rgba(31, 119, 180, 0.1); border-right: 3px solid #1f77b4; margin-left: auto; word-wrap: break-word; animation: slideIn 0.3s ease-out; }
    .bubble-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .speaker-name { font-weight: 700; font-size: 0.85rem; color: #333; }
    .timestamp { font-size: 0.7rem; color: #999; }
    .message-content { font-size: 0.9rem; line-height: 1.5; color: #333; }
    .ai-hint { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; border-radius: 4px; font-size: 0.85rem; margin-bottom: 12px; color: #856404; }
    .team-info-card { background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #7b1fa2; margin-bottom: 15px; }
    .topic-card { background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%); padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1f77b4; margin-top: 0.5rem; margin-bottom: 0.8rem; }
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
if "sending" not in st.session_state:
    st.session_state.sending = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# ========== AI Mode Configuration ==========
MODE_OPTIONS = {
    "AI-Scaffolded": {"name": "🎓 Socratic Tutoring", "description": "AI will guide you to think deeply through questions", "icon": "🎓"},
    "AI-Free-Debater": {"name": "⚔️ Active Debater", "description": "AI will present counterarguments and request evidence", "icon": "⚔️"},
    "Control": {"name": "👥 Human-Only Discussion", "description": "No AI intervention, free discussion", "icon": "👥"}
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
        user_name = st.text_input("Your Name/Nickname", placeholder="Enter your name", max_chars=20, key="login_username")
        team_name = st.text_input("🏢 Group Name (Must be the same as group members!)", placeholder="e.g.: Group1, Team A", max_chars=30, key="login_team")
    with col2:
        st.markdown("### 🤖 AI Mode Selection")
        mode_select = st.selectbox("Select AI Discussion Mode", list(MODE_OPTIONS.keys()), format_func=lambda x: MODE_OPTIONS[x]["name"], key="login_mode")

    st.divider()
    st.markdown("### 📌 Discussion Topic")
    st.info("💡 Enter the topic you want to discuss. **Group members must enter the same topic** to join the same discussion")
    topic = st.text_area("Discussion Topic", placeholder="e.g.: Should companies adopt remote work policies?", height=100, key="login_topic")

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
                session_id = get_or_create_session(team_name=team_name.strip(), topic=topic.strip(), mode=mode_select, created_by=user_name.strip())
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
                <div class="session-item"><span>💬 Messages:</span><strong>{len(current_history)}</strong></div>
                <div class="session-item"><span>👥 Group Members:</span><strong>{len(current_participants)}</strong></div>
                <div class="session-item"><span>⏱️ Time Remaining:</span><span class="timer">{minutes:02d}:{seconds:02d}</span></div>
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
                    st.download_button("📥 Download CSV", buffer.getvalue(),
                        f"discussion_record_{team_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")

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

        # Message Input (use form to avoid rerun issues)
        st.markdown("### ✏️ Your Message")
        with st.form("send_form", clear_on_submit=False):
            col1, col2, col3 = st.columns([0.72, 0.14, 0.14])
            with col1:
                user_input = st.text_area(
                    "",
                    placeholder="Share your thoughts... (use @AI to mention AI)",
                    height=80,
                    label_visibility="collapsed",
                    key="user_input"
                )
            with col2:
                st.write("")
                send_btn = st.form_submit_button("📤 Send")
            with col3:
                st.write("")
                clear_btn = st.form_submit_button("🗑️ Clear")

        # ========== Handle Send ==========
        if send_btn:
            if user_input.strip():
                st.session_state.sending = True

                db.save_message(
                    session_id=st.session_state.session_id,
                    user=st.session_state.user_name,
                    role="user",
                    message=user_input,
                    latency=0,
                    tokens_used=0,
                    tokens_input=0,
                    tokens_output=0,
                    is_success=1
                )

                add_participant(st.session_state.session_id, st.session_state.user_name)
                ai_triggered = "@AI" in user_input or "@ai" in user_input or "＠AI" in user_input

                if ai_triggered and mode != "Control":
                    conversation_history = db.get_history(st.session_state.session_id, limit=20)

                    with st.spinner("🤖 AI is thinking..."):
                        try:
                            result = generate_response(
                                mode,
                                user_input,
                                group_id=st.session_state.session_id,
                                user=st.session_state.user_name,
                                conversation_history=conversation_history
                            )

                            if isinstance(result, tuple):
                                ai_reply, metadata = result
                                tokens_used = metadata.get('tokens_used', 0)
                                tokens_input = metadata.get('tokens_input', 0)
                                tokens_output = metadata.get('tokens_output', 0)
                                latency = metadata.get('latency', 0)
                            else:
                                ai_reply = result
                                tokens_used = 0
                                tokens_input = 0
                                tokens_output = 0
                                latency = 0

                            if ai_reply:
                                db.save_message(
                                    session_id=st.session_state.session_id,
                                    user="AI",
                                    role="assistant",
                                    message=ai_reply,
                                    latency=latency,
                                    tokens_used=tokens_used,
                                    tokens_input=tokens_input,
                                    tokens_output=tokens_output,
                                    is_success=1
                                )

                                ai_placeholder = st.empty()
                                stream_ai_response(ai_reply, ai_placeholder)

                                with st.expander("��� API Performance Details"):
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("⏱️ Response Latency", f"{latency:.2f}s")
                                    with col2:
                                        st.metric("📊 Total Tokens", tokens_used)
                                    with col3:
                                        st.metric("Input | Output", f"{tokens_input} | {tokens_output}")

                            else:
                                st.error("❌ AI returned empty result")

                        except Exception as e:
                            st.error(f"❌ Error calling AI: {str(e)}")
                            db.save_message(
                                session_id=st.session_state.session_id,
                                user="AI",
                                role="assistant",
                                message=f"[Exception: {str(e)}]",
                                latency=0,
                                tokens_used=0,
                                tokens_input=0,
                                tokens_output=0,
                                error_code='EXCEPTION',
                                error_message=str(e),
                                is_success=0
                            )

                st.session_state.sending = False
                time.sleep(0.3)
                st.rerun()

        if clear_btn:
            st.session_state.user_input = ""
            st.rerun()

        # ========== Consensus Matrix ==========
        st.divider()
        st.markdown("## 📊 Consensus Matrix (AI-Powered)")

        all_data = load_all_sessions()
        current_sess = all_data.get(st.session_state.session_id, {})
        messages = current_sess.get("messages", [])
        participants = get_session_participants(st.session_state.session_id)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Messages", len(messages))
        with col2:
            st.metric("Participants", len(participants))
        with col3:
            user_msg_count = len([m for m in messages if m.get('user') != 'AI'])
            st.metric("Discussions", user_msg_count)
        with col4:
            if st.button("🔄 Refresh", key="refresh_matrix"):
                st.rerun()

        user_message_count = len([m for m in messages if m.get('user') != 'AI'])

        if user_message_count < 1:
            st.info("⏳ Waiting for discussion...")
        else:
            try:
                import pandas as pd
                from consensus_matrix import ConsensusMatrix

                matrix_calc = ConsensusMatrix()

                with st.spinner("🤖 AI extracting viewpoints..."):
                    viewpoints_pairs = matrix_calc.extract_and_simplify_viewpoints(
                        messages,
                        participants,
                        llm_mode=mode,
                        session_id=st.session_state.session_id
                    )

                if viewpoints_pairs and len(viewpoints_pairs) > 0:
                    simplified_vps = [vp[1] for vp in viewpoints_pairs]
                    full_vps = [vp[0] for vp in viewpoints_pairs]

                    with st.spinner("🤖 AI analyzing participant stances..."):
                        stances_dict = matrix_calc.analyze_stances(
                            messages,
                            participants,
                            viewpoints_pairs,
                            llm_mode=mode,
                            session_id=st.session_state.session_id
                        )

                    if stances_dict:
                        matrix_data = {}
                        for participant in participants:
                            matrix_data[participant] = {}
                            for i, full_vp in enumerate(full_vps):
                                stance = stances_dict.get(participant, {}).get(simplified_vps[i], '△')
                                matrix_data[participant][simplified_vps[i]] = stance

                        df = pd.DataFrame.from_dict(matrix_data, orient='index')

                        def style_cells(val):
                            if val == "✅":
                                return 'background-color: #90EE90; text-align: center; font-weight: bold; font-size: 18px;'
                            elif val == "❌":
                                return 'background-color: #FFB6C6; text-align: center; font-weight: bold; font-size: 18px;'
                            else:
                                return 'background-color: #FFE4B5; text-align: center; font-weight: bold; font-size: 16px;'

                        try:
                            styled_df = df.style.applymap(style_cells)
                        except:
                            styled_df = df.style.map(style_cells)

                        st.dataframe(styled_df, use_container_width=True, height=300)

                        st.markdown("---")
                        st.markdown("### Legend:")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown("✅ **Support / Agree**")
                            st.caption("Based on participant's actual statements")
                        with col2:
                            st.markdown("❌ **Oppose / Disagree**")
                            st.caption("Based on participant's actual statements")
                        with col3:
                            st.markdown("△ **Neutral / Not Mentioned**")
                            st.caption("Not clearly expressed or not mentioned")

                        with st.expander("📋 View Full Viewpoints"):
                            for i, (full, simp) in enumerate(viewpoints_pairs, 1):
                                st.markdown(f"**{i}. [{simp}]**")
                                st.caption(full)

                        st.markdown("---")
                        if st.button("📥 Export as CSV"):
                            csv_data = df.to_csv()
                            st.download_button(label="Download CSV", data=csv_data, file_name="consensus_matrix.csv", mime="text/csv")
                    else:
                        st.warning("⚠️ AI analysis failed. Please try again.")
                else:
                    st.warning("⚠️ AI could not extract viewpoints. Need more discussion.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

        # ========== API Performance & Error Tracking ==========
        st.markdown("---")
        st.markdown("## 📊 API Performance & Error Tracking")

        all_messages = db.get_history(st.session_state.session_id, limit=1000)
        if all_messages:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                successful = len([m for m in all_messages if m.get('is_success') == 1])
                st.metric("Successful Calls", successful)

            with col2:
                failed = len([m for m in all_messages if m.get('is_success') == 0])
                st.metric("Failed Calls", failed)

            with col3:
                total_tokens = sum([m.get('tokens_used', 0) for m in all_messages if m.get('tokens_used')])
                st.metric("Total Tokens Used", total_tokens)

            with col4:
                avg_latency = sum([m.get('latency', 0) for m in all_messages if m.get('latency')]) / max(len(all_messages), 1)
                st.metric("Avg Latency", f"{avg_latency:.2f}s")

# ========== Auto-refresh (SAFE) ==========
if st.session_state.session_started:
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if "last_action" not in st.session_state:
        st.session_state.last_action = datetime.now()

    # 3 秒内有操作就不刷新
    if (datetime.now() - st.session_state.last_action).total_seconds() >= 3:
        if not st.session_state.get("sending", False):
            if (datetime.now() - st.session_state.last_refresh).total_seconds() > 3.0:
                st.session_state.last_refresh = datetime.now()
                st.rerun()