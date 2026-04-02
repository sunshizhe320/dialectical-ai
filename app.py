"""
Dialectical AI - 完整应用主文件
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
from pathlib import Path
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# ==================== 导入自定义模块 ====================
try:
    from consensus_matrix import ConsensusMatrix
    from matrix_updater import updater
except ImportError as e:
    st.error(f"❌ 导入模块失败: {e}")
    st.stop()

# ==================== AI Agent 配置 ====================
try:
    from ai_agent import generate_response
except ImportError:
    st.error("❌ 无法导入 ai_agent")
    st.stop()

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="Dialectical AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 全局状态 ====================
DATA_FILE = "sessions_data.json"

def load_all_sessions() -> dict:
    """加载所有会话"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_sessions(data: dict) -> None:
    """保存所有会话"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存会话失败: {e}")

def save_message(session_id: str, user: str, role: str, message: str) -> None:
    """保存消息"""
    all_data = load_all_sessions()
    if session_id not in all_data:
        all_data[session_id] = {
            "messages": [],
            "participants": [],
            "created_at": datetime.now().isoformat()
        }
    
    all_data[session_id]["messages"].append({
        "user": user,
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    save_all_sessions(all_data)

def get_history(session_id: str, limit: int = 20) -> list:
    """获取消息历史"""
    all_data = load_all_sessions()
    messages = all_data.get(session_id, {}).get("messages", [])
    return messages[-limit:]

def get_session_participants(session_id: str) -> list:
    """获取会话参与者"""
    all_data = load_all_sessions()
    messages = all_data.get(session_id, {}).get("messages", [])
    participants = list(set([m.get('user') for m in messages if m.get('user') != 'AI']))
    return sorted(participants)

def add_participant(session_id: str, user: str) -> None:
    """添加参与者"""
    all_data = load_all_sessions()
    if session_id not in all_data:
        all_data[session_id] = {"messages": [], "participants": []}
    
    if user not in all_data[session_id]["participants"]:
        all_data[session_id]["participants"].append(user)
    
    save_all_sessions(all_data)

def stream_ai_response(response: str, placeholder) -> None:
    """流式显示 AI 响应"""
    full_response = ""
    for chunk in response.split():
        full_response += chunk + " "
        placeholder.markdown(full_response + "▌")
        time.sleep(0.01)
    placeholder.markdown(full_response)

# ==================== 初始化会话状态 ====================
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time() * 1000)}"
if "user_name" not in st.session_state:
    st.session_state.user_name = "User"
if "matrix_last_check" not in st.session_state:
    st.session_state.matrix_last_check = datetime.now()

# ==================== 侧边栏配置 ====================
with st.sidebar:
    st.markdown("## 🤖 Dialectical AI")
    
    # 会话信息
    st.markdown("### 📋 Session Information")
    session_col1, session_col2 = st.columns(2)
    with session_col1:
        st.caption("Group Name")
        st.text_input("Group", value=st.session_state.session_id[:8], disabled=True, key="group_display")
    with session_col2:
        st.caption("Your Name")
        st.session_state.user_name = st.text_input("Name", value=st.session_state.user_name, key="user_name_input")
    
    # AI 模式选择
    st.markdown("### 🧠 AI Mode")
    mode = st.radio(
        "Select Mode",
        ["Control", "AI-Scaffolded", "Socratic Tutoring"],
        label_visibility="collapsed"
    )
    
    # 会话状态
    all_data = load_all_sessions()
    current_sess = all_data.get(st.session_state.session_id, {})
    messages = current_sess.get("messages", [])
    participants = get_session_participants(st.session_state.session_id)
    
    st.markdown("### 📊 Session Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📨 Messages", len(messages))
    with col2:
        st.metric("👥 Participants", len(participants))
    
    user_msg_count = len([m for m in messages if m.get('user') != 'AI'])
    st.metric("💬 User Discussions", user_msg_count)
    
    # 时间显示
    st.markdown("### ⏱️ Time Remaining")
    remaining_time = "33:42"
    st.warning(f"**{remaining_time}**")

# ==================== 主界面 ====================
st.markdown("## 💬 Dialectical Discussion")

# 显示消息
all_data = load_all_sessions()
current_sess = all_data.get(st.session_state.session_id, {})
messages = current_sess.get("messages", [])

message_container = st.container()
with message_container:
    for msg in messages:
        if msg.get('role') == 'assistant':
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg.get('message', ''))
        else:
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"**{msg.get('user')}**: {msg.get('message', '')}")

# 输入区域
st.divider()
col_input, col_send_clear = st.columns([0.9, 0.1])

with col_input:
    user_input = st.text_area(
        "Share your thoughts... (use @AI to mention AI)",
        height=100,
        key="user_input"
    )

with col_send_clear:
    send_btn = st.button("📤 Send", key="send_btn", use_container_width=True)
    clear_btn = st.button("🗑️ Clear", key="clear_btn", use_container_width=True)

# 处理发送
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
        
        # 检查是否需要 AI 回复
        ai_triggered = "@AI" in user_input or "@ai" in user_input or "＠AI" in user_input
        
        if ai_triggered and mode != "Control":
            conversation_history = get_history(st.session_state.session_id, limit=20)
            
            with st.spinner("🤖 AI 思考中..."):
                try:
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
                        
                        # 流式显示
                        ai_placeholder = st.empty()
                        stream_ai_response(ai_reply, ai_placeholder)
                
                except Exception as e:
                    st.error(f"❌ AI 错误: {str(e)}")
        
        # 刷新
        time.sleep(0.5)
        st.rerun()

if clear_btn:
    st.rerun()

# ==================== 共识矩阵部分 ====================
st.divider()
st.markdown("## 📊 Consensus Matrix")

all_data = load_all_sessions()
current_sess = all_data.get(st.session_state.session_id, {})
messages = current_sess.get("messages", [])
participants = get_session_participants(st.session_state.session_id)

# 显示状态指标
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📨 Messages", len(messages))
with col2:
    st.metric("👥 Participants", len(participants))
with col3:
    user_msg_count = len([m for m in messages if m.get('user') != 'AI'])
    st.metric("💬 Discussions", user_msg_count)
with col4:
    if st.button("🔄 Refresh", key="refresh_matrix"):
        try:
            updater.clear_cache(st.session_state.session_id)
            st.success("✓ Cache cleared")
        except Exception as e:
            st.warning(f"清空缓存: {e}")
        st.rerun()

user_message_count = len([m for m in messages if m.get('user') != 'AI'])

if user_message_count < 1:
    st.warning(f"⏳ 等待讨论... (至少需要 1 条消息)")
else:
    try:
        session_id = st.session_state.session_id
        matrix_calc = ConsensusMatrix()
        
        # 判断是否需要更新
        if updater.should_update(session_id, messages):
            with st.spinner("📊 提取并简化观点..."):
                viewpoints_pairs = matrix_calc.extract_and_summarize_viewpoints(
                    messages,
                    participants,
                    llm_mode=mode
                )
            
            if viewpoints_pairs:
                simplified_vps = [vp[1] for vp in viewpoints_pairs]
                
                with st.spinner("📈 分析态度..."):
                    stances_dict = matrix_calc.analyze_stances_step2(
                        messages,
                        participants,
                        viewpoints_pairs,
                        llm_mode=mode
                    )
                
                if stances_dict:
                    # 保存缓存
                    cache_data = {
                        "viewpoints_full": [vp[0] for vp in viewpoints_pairs],
                        "viewpoints_simplified": simplified_vps,
                        "stances": stances_dict,
                        "timestamp": datetime.now().isoformat()
                    }
                    updater.save_cache(session_id, cache_data)
                    updater.save_state(session_id, user_message_count)
                    st.success("✅ 矩阵已更新!")
        
        # 加载并显示缓存的矩阵
        cached_matrix = updater.load_cache(session_id)
        
        if cached_matrix:
            viewpoints_simplified = cached_matrix.get("viewpoints_simplified", [])
            stances_dict = cached_matrix.get("stances", {})
            
            if viewpoints_simplified and stances_dict:
                st.markdown(f"### 📋 Matrix ({len(participants)}×{len(viewpoints_simplified)})")
                
                # 构建矩阵数据
                matrix_data = {
                    p: {sv: stances_dict.get(p, {}).get(sv, '△') for sv in viewpoints_simplified}
                    for p in participants
                }
                df = pd.DataFrame.from_dict(matrix_data, orient='index')
                
                # 样式函数
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
                
                st.dataframe(styled_df, use_container_width=True, height=200)
                
                # 底部图例
                st.divider()
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    st.markdown("**Legend:**")
                with col2:
                    st.markdown("""
- ✅ Support 
- △ Neutral / Balanced
- ❌ Oppose
                    """)
                with col3:
                    st.caption(
                        f"⏱️ {cached_matrix.get('timestamp', '')[:19]}\n"
                        f"👥 {len(participants)} | 📌 {len(viewpoints_simplified)}"
                    )
    
    except Exception as e:
        st.error(f"❌ 矩阵显示错误: {e}")
        import traceback
        with st.expander("错误详情"):
            st.code(traceback.format_exc())

# ==================== 自动刷新 ====================
time_since_check = (datetime.now() - st.session_state.matrix_last_check).total_seconds()
if time_since_check > 5:
    st.session_state.matrix_last_check = datetime.now()
    st.rerun()