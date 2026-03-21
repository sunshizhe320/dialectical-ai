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
from streamlit_autorefresh import st_autorefresh


load_dotenv()

st.set_page_config(
    page_title="Dialectical AI Partner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 使用文件系统作为共享存储（跨设备同步） ==========

SESSIONS_FILE = "sessions_data.json"
PARTICIPANTS_FILE = "participants_data.json"

def load_all_sessions():
    """从文件加载所有会话"""
    if Path(SESSIONS_FILE).exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_sessions(data):
    """保存所有会话到文件"""
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存会话失败: {e}")

def load_all_participants():
    """从文件加载所有参与者"""
    if Path(PARTICIPANTS_FILE).exists():
        try:
            with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_participants(data):
    """保存所有参与者到文件"""
    try:
        with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存参与者失败: {e}")

def get_or_create_session(team_name, topic, mode, created_by):
    """获取或创建会话 - 真正的跨设备同步"""
    all_sessions = load_all_sessions()
    
    # 检查是否已存在相同的小组+主题
    for sid, info in all_sessions.items():
        if info.get("team_name") == team_name and info.get("topic") == topic:
            print(f"✅ 找到现有会话: {sid}")
            return sid
    
    # 创建新会话
    topic_short = topic.replace('？', '').replace('?', '')[:20]
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
    print(f"✅ 创建新会话: {session_id}")
    return session_id

def add_participant(session_id, user_name):
    """添加参与者"""
    all_participants = load_all_participants()
    
    if session_id not in all_participants:
        all_participants[session_id] = {}
    
    all_participants[session_id][user_name] = datetime.now().isoformat()
    save_all_participants(all_participants)

def get_session_participants(session_id):
    """获取活跃参与者"""
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
    """保存消息 - 同步到文件"""
    all_sessions = load_all_sessions()
    
    if session_id not in all_sessions:
        print(f"❌ 会话不存在: {session_id}")
        return
    
    all_sessions[session_id]["messages"].append({
        "user": user,
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    
    save_all_sessions(all_sessions)
    print(f"✅ 消息已保存")

def get_history(session_id, limit=100):
    """获取对话历史"""
    all_sessions = load_all_sessions()
    
    if session_id not in all_sessions:
        return []
    
    messages = all_sessions[session_id].get("messages", [])
    return messages[-limit:] if len(messages) > limit else messages

def get_session_info(session_id):
    """获取会话信息"""
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

# ========== CSS 和其他代码保持不变 ==========
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

# 每隔一段时间刷新，以同步其他设备的消息
if st.session_state.session_started:
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    if (datetime.now() - st.session_state.last_refresh).seconds > 2:
        st.session_state.last_refresh = datetime.now()
        st.rerun()

# ========== AI 模式配置 ==========
MODE_OPTIONS = {
    "AI-Scaffolded": {
        "name": "🎓 苏格拉底式教学",
        "description": "AI将通过问题引导你深入思考",
        "icon": "🎓"
    },
    "AI-Free-Debater": {
        "name": "⚔️ 积极辩手",
        "description": "AI将提出反对观点并要求证据",
        "icon": "⚔️"
    },
    "Control": {
        "name": "👥 纯人类讨论",
        "description": "无AI干预，进行自由讨论",
        "icon": "👥"
    }
}

def stream_ai_response(ai_reply, placeholder_container):
    """流式显示 AI 回复"""
    
    # 检查 ai_reply 是否为空
    if not ai_reply:
        placeholder_container.markdown("""
        <div class="ai-bubble">
            <div class="bubble-header">
                <span class="speaker-name">🤖 AI Assistant</span>
                <span class="timestamp">❌ 错误</span>
            </div>
            <div class="message-content">AI 服务暂时无法响应，请稍后重试</div>
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
# ========== 登录页面 ==========
if not st.session_state.session_started:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-header">
            <h1>📱 Dialectical AI Partner</h1>
            <p>批判性思维与协作学习平台</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("""
    ## 🎓 研究项目介绍
    
    本研究探索**生成式AI作为辩证合作伙伴**如何促进学生的批判性思维发展。
    
    ### 📋 你将体验：
    - **深度讨论**：围绕自定义主题进行讨论
    - **👥 小组协作**：多名成员进入同一小组，共同讨论
    - **🤖 AI辅助**：获得不同方式的讨论支持
    - **📊 实时分析**：系统自动分析批判性思维指标
    
    ### 💡 加入小组说明
    **重要：** 与其他成员填写**相同的「小组名称」和「讨论主题」**即可进入同一讨论界面！
    
    **示例：**
    - 小组名称：`小组1`
    - 讨论主题：`人工智能是否应该被允许参与中小学教育？`
    
    只要两个人填的完全一样，就会自动同步到一个界面！
    """)
    
    st.divider()
    
    st.markdown("## 🎯 讨论设置")
    
    col1, col2 = st.columns([0.5, 0.5])
    
    with col1:
        st.markdown("### 👤 基本信息")
        user_name = st.text_input(
            "你的名字/昵称",
            placeholder="输入你的名字",
            max_chars=20,
            key="login_username"
        )
        
        team_name = st.text_input(
            "🏢 小组名称（与同组成员保持一致！）",
            placeholder="如：小组1、Team A",
            max_chars=30,
            key="login_team"
        )
    
    with col2:
        st.markdown("### 🤖 AI 模式选择")
        mode_select = st.selectbox(
            "选择 AI 讨论模式",
            list(MODE_OPTIONS.keys()),
            format_func=lambda x: MODE_OPTIONS[x]["name"],
            key="login_mode"
        )
    
    st.divider()
    
    st.markdown("### 📌 讨论主题")
    st.info("💡 请输入要讨论的主题。**同组成员必须填入相同的主题**才能进入同一讨论")
    
    topic = st.text_area(
        "讨论主题",
        placeholder="例如：企业应该采用远程工作制度吗？",
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
        consent = st.checkbox("✅ 我已阅读并同意参与本研究")
        
        if st.button("🚀 进入讨论", use_container_width=True):
            if not user_name.strip():
                st.error("❌ 请输入你的名字")
            elif not team_name.strip():
                st.error("❌ 请输入小组名称")
            elif not topic.strip():
                st.error("❌ 请输入讨论主题")
            elif not consent:
                st.error("❌ 请同意参与本研究")
            else:
                # 创建或获取会话
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
                
                st.success(f"✅ 成功进入讨论！")
                time.sleep(1)
                st.rerun()

# ========== 讨论页面 ==========
else:
    session_info = get_session_info(st.session_state.session_id)
    
    if not session_info:
        st.error("❌ 会话信息丢失，请重新登录")
        if st.button("返回登录"):
            st.session_state.session_started = False
            st.rerun()
    else:
        topic = session_info.get("topic", "讨论主题")
        team_name = session_info.get("team_name", "小组")
        mode = session_info.get("mode", "Control")
        mode_info = MODE_OPTIONS.get(mode, {})
        
        add_participant(st.session_state.session_id, st.session_state.user_name)
        current_participants = get_session_participants(st.session_state.session_id)
        
        current_history = get_history(st.session_state.session_id, limit=500)
        
        # 左侧栏
        with st.sidebar:
            st.title("📱 Dialectical AI")
            
            st.markdown("### 👥 会话信息")
            st.markdown(f"""
            <div class="team-info-card">
                <strong>🏢 小组名称：</strong> {team_name}<br>
                <strong>👤 你的名字：</strong> {st.session_state.user_name}<br>
                <strong>🤖 AI 模式：</strong> {mode_info.get('name', '未知')}<br>
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
                    <span>💬 消息数：</span>
                    <strong>{len(current_history)}</strong>
                </div>
                <div class="session-item">
                    <span>👥 小组成员：</span>
                    <strong>{len(current_participants)}</strong>
                </div>
                <div class="session-item">
                    <span>⏱️ 剩余时间：</span>
                    <span class="timer">{minutes:02d}:{seconds:02d}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown("**👥 小组成员在线**")
            if current_participants:
                for member in current_participants:
                    if member == st.session_state.user_name:
                        st.caption(f"✓ 🟢 {member} (你)")
                    else:
                        st.caption(f"● 🔵 {member}")
            else:
                st.caption("暂无在线成员")
            
            st.divider()
            
            st.markdown(f"""
            <div class="topic-card">
                <strong>📌 讨论主题：</strong><br><br>
                {topic}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown(f"""
            <div class="mode-card">
                <strong>{mode_info.get('name', '未知模式')}</strong><br><br>
                {mode_info.get('description', '')}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            if st.button("📥 导出讨论记录", use_container_width=True):
                history = get_history(st.session_state.session_id, limit=1000)
                if history:
                    buffer = io.StringIO()
                    writer = csv.writer(buffer)
                    writer.writerow(["用户", "角色", "消息", "时间"])
                    for h in history:
                        writer.writerow([h["user"], h["role"], h["message"], h["timestamp"]])
                    st.download_button(
                        "📥 下载 CSV",
                        buffer.getvalue(),
                        f"讨论记录_{team_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
        
        # ===== 主区域 =====
        st.markdown(f"## 💬 {team_name} 的讨论")
        
        members_str = ", ".join(current_participants) if current_participants else "暂无成员"
        st.markdown(f"**👥 参与成员：** {members_str}")
        st.markdown(f"**📌 主题：** {topic}")
        
        st.divider()
        
        if mode != "Control":
            st.markdown("""
            <div class="ai-hint">
                💡 <strong>提示：</strong>在消息中使用 <code>@AI</code> 来艾特 AI 获得帮助。
            </div>
            """, unsafe_allow_html=True)
        
        progress = min(len(current_history) / 40, 1.0)
        st.progress(progress, f"📊 {len(current_history)} 条消息")
        
        st.markdown("### 💬 讨论记录")
        
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
                                <span class="speaker-name">👤 {user} {'(你)' if is_self else ''} {('🔔' if has_ai_mention else '')}</span>
                                <span class="timestamp">{time_str}</span>
                            </div>
                            <div class="message-content">{content}</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("💭 开始讨论！")
        
        st.divider()
        
        st.markdown("### ✏️ 你的消息")
        
        col1, col2, col3 = st.columns([0.72, 0.14, 0.14])
        
        with col1:
            user_input = st.text_area(
                "",
                placeholder="分享你的想法... (使用 @AI 艾特 AI)",
                height=80,
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("")
            send_btn = st.button("📤 发送", use_container_width=True)
        
        with col3:
            st.write("")
            clear_btn = st.button("🗑️ 清空", use_container_width=True)
        
               # ===== 处理发送 =====
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
                    
                    with st.spinner("🤖 AI 正在思考中..."):
                        try:
                            ai_reply = generate_response(
                                mode,
                                user_input,
                                group_id=st.session_state.session_id,
                                user=st.session_state.user_name,
                                conversation_history=conversation_history
                            )
                            
                            if ai_reply:
                                # 保存消息
                                save_message(
                                    st.session_state.session_id, 
                                    "AI", 
                                    "assistant", 
                                    ai_reply
                            )
                                
                                # 显示回复
                                ai_placeholder = st.empty()
                                stream_ai_response(ai_reply, ai_placeholder)
                            else:
                                st.error("❌ AI 返回空结果")
                        
                        except Exception as e:
                            st.error(f"❌ 调用 AI 时出错: {str(e)}")
                            print(f"错误: {e}")
                
                time.sleep(0.3)
                st.rerun()
        
        if clear_btn:
            st.rerun()
            st.session_state.current_arg_map = None
# --- 只有在进入讨论 Session 后才显示图谱 ---
    if "session_id" in st.session_state and st.session_state.session_id:
        st.divider()
        st.subheader("🕸️ 实时论证图谱 (Argumentation Map)")

        # 刷新按钮
        if st.button("🔍 更新论证分析", use_container_width=True):
            # 注意：这里直接引用你文件里已有的函数
            from ai_agent import generate_argument_map
            
            # 获取当前所有消息
            current_msgs = get_history(st.session_state.session_id, limit=100)
            
            if len(current_msgs) > 1:
                with st.spinner("AI 正在解析深度逻辑并构建图谱..."):
                    # 调用 AI 生成
                    map_result = generate_argument_map(current_msgs, st.session_state.login_topic)
                    # 【核心修正】：统一使用 current_arg_map 这个变量名
                    st.session_state.current_arg_map = map_result
                    st.rerun()
            else:
                st.warning("⚠️ 讨论消息太少（至少需要2条），AI 尚无法分析论证结构。")

        # 【核心修正】：检查对应的变量名
        if "current_arg_map" in st.session_state and st.session_state.current_arg_map:
            with st.container(border=True):
                st.markdown(st.session_state.current_arg_map)
                st.caption("注：图谱基于当前对话生成。若有新发言，请再次点击更新。")
        else:
            st.info("💡 点击上方按钮，AI 将根据当前的对话生成论证图谱。")