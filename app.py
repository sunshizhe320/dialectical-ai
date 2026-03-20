# app.py - 完整优化版本（多成员同步讨论+自动会话管理）
import streamlit as st
import time
import io
import csv
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from ai_agent import generate_response
from db import (
    init_db, save_message, get_history, 
    get_or_create_session, add_participant, 
    get_session_participants, get_session_info
)
from discourse_analysis import analyzer

load_dotenv()
init_db()

st.set_page_config(
    page_title="Dialectical AI Partner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CSS 优化 ==========
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
    
    /* 欢迎页样式 */
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
    
    /* AI 模式说明 */
    .mode-card {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1976d2;
        margin-bottom: 15px;
    }
    
    /* 会话面板 */
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
    
    /* 消息气泡 */
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
    
    /* @AI 提示样式 */
    .ai-hint {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        margin-bottom: 12px;
        color: #856404;
    }
    
    /* 小组信息卡片 */
    .team-info-card {
        background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #7b1fa2;
        margin-bottom: 15px;
    }
    
    /* 主题卡片 */
    .topic-card {
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .topic-card h3 {
        color: #ff9800;
        margin-top: 0;
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
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# 自动刷新
if (datetime.now() - st.session_state.last_refresh).seconds > 3:
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

# ========== 流式显示 AI 响应函数 ==========
def stream_ai_response(ai_reply, placeholder_container):
    """流式显示 AI 回复 - 逐字出现的动画效果"""
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
    
    # 移除光标，显示完整内容
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
    
    ### 🔐 知情同意
    
    **参与须知：**
    - ✅ 你的所有对话数据将被记录用于研究
    - ✅ 数据仅用于学术研究，不会公开个人身份
    - ✅ 你可以随时退出研究
    - ✅ 没有对错答案，我们关注你的思考过程
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
            placeholder="如：小组1、Team A、讨论小组A",
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
    
    st.markdown("### 📌 讨论主题（与同组成员保持一致！）")
    st.info("💡 请输入要讨论的主题。**同组成员必须填入完全相同的主题**才能进入同一讨论")
    
    topic = st.text_area(
        "讨论主题",
        placeholder="例如：企业应该采用远程工作制度吗？",
        height=100,
        key="login_topic"
    )
    
    # 显示选中的 AI 模式信息
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
            # 验证输入
            if not user_name.strip():
                st.error("❌ 请输入你的名字")
            elif not team_name.strip():
                st.error("❌ 请输入小组名称")
            elif not topic.strip():
                st.error("❌ 请输入讨论主题")
            elif not consent:
                st.error("❌ 请同意参与本研究")
            else:
                # 🎯 关键：获取或创建会话
                session_id = get_or_create_session(
                    team_name=team_name.strip(),
                    topic=topic.strip(),
                    mode=mode_select,
                    created_by=user_name.strip()
                )
                
                # 添加参与者
                add_participant(session_id, user_name.strip())
                
                # 保存到 session_state
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
    # 获取会话信息
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
        
        # 更新参与者状态
        add_participant(st.session_state.session_id, st.session_state.user_name)
        current_participants = get_session_participants(st.session_state.session_id)
        
        # 获取讨论历史
        current_history = get_history(st.session_state.session_id, limit=500)
        
        # 左侧栏
        with st.sidebar:
            st.title("📱 Dialectical AI")
            
            # ===== 小组信息 =====
            st.markdown("### 👥 会话信息")
            st.markdown(f"""
            <div class="team-info-card">
                <strong>🏢 小组名称：</strong> {team_name}<br>
                <strong>👤 你的名字：</strong> {st.session_state.user_name}<br>
                <strong>🤖 AI 模式：</strong> {mode_info.get('name', '未知')}<br>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # ===== 会话统计 =====
            st.markdown("### 📊 Session Status")
            
            # 计时器
            elapsed = datetime.now() - st.session_state.session_start_time
            remaining = max(0, 2400 - int(elapsed.total_seconds()))  # 40分钟
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
            
            # ===== 小组成员在线列表 =====
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
            
            # ===== 讨论主题 =====
            st.markdown(f"""
            <div class="topic-card">
                <strong>📌 讨论主题：</strong><br><br>
                {topic}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # ===== AI 模式说明 =====
            st.markdown(f"""
            <div class="mode-card">
                <strong>{mode_info.get('name', '未知模式')}</strong><br><br>
                {mode_info.get('description', '')}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # ===== 导出数据 =====
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
        
        # 显示参与成员
        members_str = ", ".join(current_participants)
        st.markdown(f"**👥 参与成员：** {members_str}")
        st.markdown(f"**📌 主题：** {topic}")
        
        st.divider()
        
        # @AI 使用提示
        if mode != "Control":
            st.markdown("""
            <div class="ai-hint">
                💡 <strong>提示：</strong>在消息中使用 <code>@AI</code> 来艾特 AI 获得帮助。例如："这个例子对吗？@AI"
            </div>
            """, unsafe_allow_html=True)
        
        # 进度条
        progress = min(len(current_history) / 40, 1.0)
        st.progress(progress, f"📊 {len(current_history)} 条消息")
        
        # ===== 对话区域 =====
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
                    # AI 消息
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
                    # 学生消息
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
        
        # ===== 输入区域 =====
        st.markdown("### ✏️ 你的消息")
        
        col1, col2, col3 = st.columns([0.72, 0.14, 0.14])
        
        with col1:
            user_input = st.text_area(
                "",
                placeholder="分享你的想法... (使用 @AI 艾特 AI 寻求帮助)",
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
                # 保存用户消息
                save_message(
                    st.session_state.session_id, 
                    st.session_state.user_name, 
                    "user", 
                    user_input
                )
                add_participant(st.session_state.session_id, st.session_state.user_name)
                
                # 检查是否艾特了 AI
                ai_triggered = "@AI" in user_input or "@ai" in user_input or "＠AI" in user_input
                
                # 只有在非对照组且消息中包含 @AI 时才生成 AI 回复
                if ai_triggered and mode != "Control":
                    conversation_history = get_history(st.session_state.session_id, limit=20)
                    
                    with st.spinner("🤖 AI正在思考中..."):
                        ai_reply = generate_response(
                            mode,
                            user_input,
                            group_id=st.session_state.session_id,
                            user=st.session_state.user_name,
                            conversation_history=conversation_history
                        )
                        # 保存 AI 消息到数据库
                        save_message(
                            st.session_state.session_id, 
                            "AI", 
                            "assistant", 
                            ai_reply
                        )
                        
                        # 显示流式 AI 响应
                        ai_placeholder = st.empty()
                        stream_ai_response(ai_reply, ai_placeholder)
                
                time.sleep(0.3)
                st.rerun()
        
        if clear_btn:
            st.rerun()
        
        st.divider()
        
        # ===== 分析区域 =====
        st.markdown("### 📊 批判性思维分析")
        
        if history:
            stats = analyzer.analyze_history(history, verbose=True)
            
            # ===== 核心指标 =====
            st.markdown("#### 🎯 讨论质量指标")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            metrics = [
                ("❓", "提问", stats["questions"], "引导式提问次数"),
                ("🔄", "反驳", stats["counterarguments"], "提出反对意见次数"),
                ("📊", "证据", stats["evidence"], "引用证据或例子次数"),
                ("🎯", "澄清", stats["clarifications"], "澄清或重述次数"),
                ("👍", "同意", stats["agreements"], "表示同意或补充次数"),
            ]
            
            for col, (emoji, label, val, description) in zip(
                [col1, col2, col3, col4, col5],
                metrics
            ):
                with col:
                    st.metric(
                        label=f"{emoji} {label}",
                        value=val,
                        help=description
                    )
            
            # ===== 汇总统计 =====
            st.markdown("#### 📈 讨论统计")
            col1, col2, col3 = st.columns(3)
            
            total = sum([stats["questions"], stats["counterarguments"], stats["evidence"], 
                         stats["clarifications"], stats["agreements"]])
            avg = total / max(stats["user_messages"], 1)
            
            with col1:
                st.metric(
                    label="💬 平均指标/条消息",
                    value=f"{avg:.2f}",
                    help="每条学生消息中平均出现的批判性思维指标个数（越高越好）"
                )
            
            with col2:
                st.metric(
                    label="🗣️ 学生发言数",
                    value=stats["user_messages"],
                    help="学生发送的消息总数"
                )
            
            with col3:
                st.metric(
                    label="🤖 AI 回复数",
                    value=stats["ai_messages"],
                    help="AI 助手的回复总数"
                )
            
            # ===== 详细说明 =====
            st.markdown("#### 📝 指标说明")
            
            with st.expander("📖 展开查看各指标的详细解释", expanded=False):
                st.markdown("""
                **❓ 提问 (Questions)**
                - 包括「为什么」「如何」「是否」等疑问
                - 高分表示学生主动提问，激发深度思考
                
                **🔄 反驳 (Counterarguments)**
                - 包括「但是」「相反」「我不同意」等相反观点
                - 高分表示学生能进行批判性分析
                
                **📊 证据 (Evidence)**
                - 包括引用例子、数据、研究、事实等
                - 高分表示学生论证有据可查
                
                **🎯 澄清 (Clarifications)**
                - 包括重述、解释、简化复杂概念
                - 高分表示学生思考严谨、表达清晰
                
                **👍 同意 (Agreements)**
                - 包括表示赞成、补充观点、延伸讨论
                - 高分表示学生能建立在他人观点基础上
                """)
            
            # ===== 讨论深度评估 =====
            st.markdown("#### 🎓 讨论深度评估")
            
            if avg >= 1.5:
                assessment = "🌟 **优秀** - 你的讨论非常深入，批判性思维指标特别高！"
                color = "#4CAF50"
            elif avg >= 1.0:
                assessment = "⭐ **良好** - 你的讨论质量不错，能很好地展现批判性思维。"
                color = "#2196F3"
            elif avg >= 0.5:
                assessment = "👍 **中等** - 你的讨论有一定深度，可以继续增强论证和提问。"
                color = "#FF9800"
            else:
                assessment = "💡 **需要改进** - 尝试更多提问、引用证据或提出反对意见。"
                color = "#F44336"
            
            st.markdown(f"""
            <div style="background-color: {color}; padding: 15px; border-radius: 8px; color: white;">
                {assessment}
            </div>
            """, unsafe_allow_html=True)
        
        else:
            st.info("💭 开始聊天以查看批判性思维分析")