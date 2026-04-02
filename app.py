"""
讨论页面 - 实验管理和共识矩阵
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
sys.path.insert(0, str(Path(__file__).parent.parent))

# 检查是否在讨论中
if not st.session_state.get("in_discussion", False):
    st.warning("请先从首页进入讨论")
    st.switch_page("app.py")

# 导入自定义模块
try:
    from consensus_matrix import ConsensusMatrix
    from matrix_updater import updater
except ImportError as e:
    st.error(f"❌ 导入模块失败: {e}")
    st.stop()

# 导入 AI Agent
try:
    from ai_agent import generate_response
except ImportError:
    st.error("❌ 无法导入 ai_agent")
    st.stop()

st.set_page_config(
    page_title="Dialectical Discussion",
    page_icon="💬",
    layout="wide"
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
        all_data[session_id] = {"messages": [], "participants": []}
    
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

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## 🤖 Dialectical AI")
    
    # 会话信息
    st.markdown("### 📋 Session Information")
    st.info(f"""
**Group Name:** {st.session_state.group_name}

**Your Name:** {st.session_state.user_name}

**AI Mode:** {st.session_state.ai_mode}
    """)
    
    # 获取会话数据
    session_id = st.session_state.session_id
    all_data = load_all_sessions()
    current_sess = all_data.get(session_id, {})
    messages = current_sess.get("messages", [])
    participants = get_session_participants(session_id)
    
    st.markdown("### 📊 Session Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📨 Messages", len(messages))
    with col2:
        st.metric("👥 Participants", len(participants))
    
    user_msg_count = len([m for m in messages if m.get('user') != 'AI'])
    st.metric("💬 User Discussions", user_msg_count)
    
    # 时间显示（如果需要）
    st.markdown("### ⏱️ Time Remaining")
    st.warning(f"**33:42**")

# ==================== 主界面 ====================
st.markdown(f"## 💬 {st.session_state.group_name} Discussion")
st.markdown(f"**👥 Participants:** {', '.join(participants) if participants else 'Waiting for participants...'}")
st.markdown(f"**🎯 Topic:** {st.session_state.discussion_topic}")

st.info("💡 **Tip:** Use `@AI` in your message to mention AI for help.")

# ==================== 显示消息 ====================
message_container = st.container()
with message_container:
    for msg in messages:
        if msg.get('role') == 'assistant':
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg.get('message', ''))
        else:
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"**{msg.get('user')}**: {msg.get('message', '')}")

# ==================== 输入区域 ====================
st.divider()

col_input, col_buttons = st.columns([0.85, 0.15])

with col_input:
    user_input = st.text_area(
        "Share your thoughts...",
        height=100,
        placeholder="Use @AI to mention AI",
        label_visibility="collapsed",
        key="user_input"
    )

with col_buttons:
    send_btn = st.button("📤 Send", use_container_width=True)
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

# 处理发送
if send_btn:
    if user_input.strip():
        session_id = st.session_state.session_id
        
        # 保存用户消息
        save_message(session_id, st.session_state.user_name, "user", user_input)
        add_participant(session_id, st.session_state.user_name)
        
        # 检查是否需要 AI 回复
        ai_triggered = "@AI" in user_input or "@ai" in user_input
        
        if ai_triggered and st.session_state.ai_mode != "Control":
            conversation_history = get_history(session_id, limit=20)
            
            with st.spinner("🤖 AI 思考中..."):
                try:
                    ai_reply = generate_response(
                        st.session_state.ai_mode,
                        user_input,
                        group_id=session_id,
                        user=st.session_state.user_name,
                        conversation_history=conversation_history
                    )
                    
                    if ai_reply:
                        save_message(session_id, "AI", "assistant", ai_reply)
                
                except Exception as e:
                    st.error(f"❌ AI 错误: {str(e)}")
        
        time.sleep(0.5)
        st.rerun()

if clear_btn:
    st.rerun()

# ==================== 共识矩阵 ====================
st.divider()
st.markdown("## 📊 Consensus Matrix")

session_id = st.session_state.session_id
all_data = load_all_sessions()
current_sess = all_data.get(session_id, {})
messages = current_sess.get("messages", [])
participants = get_session_participants(session_id)

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
            updater.clear_cache(session_id)
            st.success("✓ Cache cleared")
        except Exception as e:
            st.warning(f"清空缓存: {e}")
        st.rerun()

user_message_count = len([m for m in messages if m.get('user') != 'AI'])

if user_message_count < 1:
    st.warning(f"⏳ 等待讨论... (至少需要 1 条消息)")
else:
    try:
        matrix_calc = ConsensusMatrix()
        
        if updater.should_update(session_id, messages):
            with st.spinner("📊 提取并简化观点..."):
                viewpoints_pairs = matrix_calc.extract_and_summarize_viewpoints(
                    messages,
                    participants,
                    llm_mode=st.session_state.ai_mode
                )
            
            if viewpoints_pairs:
                simplified_vps = [vp[1] for vp in viewpoints_pairs]
                
                with st.spinner("📈 分析态度..."):
                    stances_dict = matrix_calc.analyze_stances_step2(
                        messages,
                        participants,
                        viewpoints_pairs,
                        llm_mode=st.session_state.ai_mode
                    )
                
                if stances_dict:
                    cache_data = {
                        "viewpoints_full": [vp[0] for vp in viewpoints_pairs],
                        "viewpoints_simplified": simplified_vps,
                        "stances": stances_dict,
                        "timestamp": datetime.now().isoformat()
                    }
                    updater.save_cache(session_id, cache_data)
                    updater.save_state(session_id, user_message_count)
                    st.success("✅ 矩阵已更新!")
        
        cached_matrix = updater.load_cache(session_id)
        
        if cached_matrix:
            viewpoints_simplified = cached_matrix.get("viewpoints_simplified", [])
            stances_dict = cached_matrix.get("stances", {})
            
            if viewpoints_simplified and stances_dict:
                st.markdown(f"### 📋 Matrix ({len(participants)}×{len(viewpoints_simplified)})")
                
                matrix_data = {
                    p: {sv: stances_dict.get(p, {}).get(sv, '△') for sv in viewpoints_simplified}
                    for p in participants
                }
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
                
                st.dataframe(styled_df, use_container_width=True, height=200)
                
                st.divider()
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    st.markdown("**Legend:**")
                with col2:
                    st.markdown("""
- ✅ Support / Mentioned
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

# 自动刷新
if "matrix_last_check" not in st.session_state:
    st.session_state.matrix_last_check = datetime.now()

time_since_check = (datetime.now() - st.session_state.matrix_last_check).total_seconds()
if time_since_check > 5:
    st.session_state.matrix_last_check = datetime.now()
    st.rerun()