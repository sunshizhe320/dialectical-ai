import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd


def render_voice_balance(messages, participants):
    """人声平衡仪表盘"""
    
    st.markdown("### 🎙️ Voice Balance (声音墙指标)")
    
    user_msg_count = {}
    ai_msg_count = 0
    user_char_count = {}
    ai_char_count = 0
    
    for msg in messages:
        if msg.get('user') == 'AI':
            ai_msg_count += 1
            ai_char_count += len(msg.get('message', ''))
        else:
            user = msg.get('user', 'Unknown')
            user_msg_count[user] = user_msg_count.get(user, 0) + 1
            user_char_count[user] = user_char_count.get(user, 0) + len(msg.get('message', ''))
    
    total_messages = len(messages)
    
    if total_messages == 0:
        st.info("💭 No messages yet")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总消息数", total_messages)
    col2.metric("人类消息数", sum(user_msg_count.values()))
    col3.metric("AI消息数", ai_msg_count)
    col4.metric("AI比例", f"{ai_msg_count/total_messages*100:.1f}%")
    
    st.info("✓ Voice balance analysis")


def render_viewpoint_evolution(messages, participants, topic=""):
    """观点演化轨迹"""
    
    st.markdown("### 📈 观点演化轨迹")
    
    if len(messages) < 2:
        st.info("💭 Need more messages")
        return
    
    evolution_data = {p: [] for p in participants}
    
    for msg in messages:
        user = msg.get('user')
        if user and user != 'AI' and user in evolution_data:
            stance_score = calculate_stance_score(msg.get('message', ''), topic)
            evolution_data[user].append({
                'stance': stance_score,
                'message': msg.get('message', '')[:60]
            })
    
    fig = go.Figure()
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    
    for i, (participant, data) in enumerate(evolution_data.items()):
        if not data:
            continue
        
        stances = [d['stance'] for d in data]
        fig.add_trace(go.Scatter(
            y=stances,
            mode='lines+markers',
            name=participant,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title="Viewpoint Evolution",
        xaxis_title="Message Index",
        yaxis_title="Stance Score",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def calculate_stance_score(message, topic=""):
    """计算立场评分"""
    
    keywords_pro_algo = ['算法', 'algorithm', '推荐', '平台', '系统']
    keywords_pro_human = ['个人', 'personal', '选择', '用户', '教育']
    
    message_lower = message.lower()
    
    pro_algo = sum(1 for kw in keywords_pro_algo if kw in message_lower)
    pro_human = sum(1 for kw in keywords_pro_human if kw in message_lower)
    
    total = pro_algo + pro_human
    
    if total == 0:
        return 0
    
    return (pro_algo - pro_human) / total