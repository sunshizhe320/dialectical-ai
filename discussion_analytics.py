discussion_analytics.py
"""
讨论分析与可视化
- 人声比例（Voice Balance）
- 观点演化轨迹（Viewpoint Evolution）
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

def render_voice_balance(messages, participants):
    """
    人声平衡仪表盘
    防止"Sound Wall" 问题：AI声音过多
    """
    
    st.markdown("### 🎙️ Voice Balance (声音墙指标)")
    
    # 统计消息
    user_msg_count = {}
    ai_msg_count = 0
    user_char_count = {}
    ai_char_count = 0
    
    for msg in messages:
        if msg['user'] == 'AI':
            ai_msg_count += 1
            ai_char_count += len(msg['message'])
        else:
            user = msg['user']
            user_msg_count[user] = user_msg_count.get(user, 0) + 1
            user_char_count[user] = user_char_count.get(user, 0) + len(msg['message'])
    
    total_messages = len(messages)
    total_chars = sum(user_char_count.values()) + ai_char_count
    
    # 指标行
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总消息数", total_messages)
    col2.metric("人类消息数", sum(user_msg_count.values()))
    col3.metric("AI消息数", ai_msg_count)
    col4.metric("AI比例", f"{ai_msg_count/total_messages*100:.1f}%", 
                delta="⚠️ 过高" if ai_msg_count/total_messages > 0.4 else "✓ 适中" if ai_msg_count/total_messages >= 0.15 else "💡 偏低")
    
    # 分组柱状图：消息数 vs 字符数
    col1, col2 = st.columns(2)
    
    with col1:
        # 消息数分布
        fig1 = go.Figure()
        
        participants_sorted = sorted(user_msg_count.items(), key=lambda x: x[1], reverse=True)
        names = [p[0] for p in participants_sorted]
        counts = [p[1] for p in participants_sorted]
        
        fig1.add_trace(go.Bar(
            x=names,
            y=counts,
            name='Human',
            marker_color='#4CAF50',
            text=counts,
            textposition='outside'
        ))
        
        fig1.add_trace(go.Bar(
            x=['AI'],
            y=[ai_msg_count],
            name='AI',
            marker_color='#2196F3',
            text=[ai_msg_count],
            textposition='outside'
        ))
        
        fig1.update_layout(
            title="消息数分布",
            xaxis_title="参与者",
            yaxis_title="消息数",
            barmode='group',
            showlegend=True,
            height=350
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 字符数分布（权重）
        fig2 = go.Figure()
        
        names_chars = sorted(user_char_count.items(), key=lambda x: x[1], reverse=True)
        names = [p[0] for p in names_chars]
        chars = [p[1] for p in names_chars]
        
        fig2.add_trace(go.Bar(
            x=names,
            y=chars,
            name='Human',
            marker_color='#FF6B6B',
            text=[f"{c//100}k" for c in chars],
            textposition='outside'
        ))
        
        fig2.add_trace(go.Bar(
            x=['AI'],
            y=[ai_char_count],
            name='AI',
            marker_color='#FFC107',
            text=[f"{ai_char_count//100}k"],
            textposition='outside'
        ))
        
        fig2.update_layout(
            title="字符数分布（权重）",
            xaxis_title="参与者",
            yaxis_title="字符数",
            barmode='group',
            showlegend=True,
            height=350
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # 参与度分布
    st.write("**参与度细分：**")
    
    total_human_msg = sum(user_msg_count.values())
    
    cols = st.columns(len(user_msg_count))
    for col, (user, count) in enumerate(sorted(user_msg_count.items(), key=lambda x: x[1], reverse=True)):
        with cols[col]:
            percentage = count / total_human_msg * 100
            st.metric(f"👤 {user}", f"{count}", f"{percentage:.1f}%")
    
    # 健康度评估
    st.divider()
    st.write("**讨论健康度评估：**")
    
    # 指标1：AI占比
    ai_ratio = ai_msg_count / total_messages
    if ai_ratio > 0.4:
        st.warning("⚠️ **AI声音过多** - AI占比超过40%，建议增加人类讨论")
    elif ai_ratio < 0.1:
        st.info("💡 **可增加AI引导** - AI参与度偏低，可通过@AI让AI参与更多")
    else:
        st.success(f"✓ **平衡适中** - AI占比{ai_ratio*100:.1f}%，符合支架教学规范")
    
    # 指标2：参与均衡度
    if len(user_msg_count) > 1:
        msg_std = pd.Series(list(user_msg_count.values())).std()
        msg_mean = pd.Series(list(user_msg_count.values())).mean()
        uniformity = 1 - (msg_std / msg_mean if msg_mean > 0 else 1)
        
        if uniformity > 0.8:
            st.success(f"✓ **参与均衡** - 所有参与者发言数量分布均衡（均匀度{uniformity:.1%}）")
        elif uniformity > 0.5:
            st.info(f"💡 **略有不均** - 建议鼓励参与度低的成员发言（均匀度{uniformity:.1%}）")
        else:
            st.warning(f"⚠️ **严重不均** - 某些参与者参与度过低，讨论质量可能受影响（均匀度{uniformity:.1%}）")


def render_viewpoint_evolution(messages, participants, topic=""):
    """
    观点演化轨迹
    显示每个参与者的立场如何随讨论变化
    """
    
    st.markdown("### 📈 观点演化轨迹")
    
    # 提取时间序列数据
    evolution_data = {p: [] for p in participants}
    
    for msg in sorted(messages, key=lambda x: x['timestamp']):
        user = msg['user']
        if user != 'AI' and user in evolution_data:
            # 计算立场评分
            stance_score = calculate_stance_score(msg['message'], topic)
            timestamp = datetime.fromisoformat(msg['timestamp'])
            
            evolution_data[user].append({
                'time': timestamp,
                'stance': stance_score,
                'message': msg['message'][:60] + "..." if len(msg['message']) > 60 else msg['message']
            })
    
    # 绘图
    fig = go.Figure()
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    
    for i, (participant, data) in enumerate(evolution_data.items()):
        if not data:
            continue
        
        times = [d['time'] for d in data]
        stances = [d['stance'] for d in data]
        
        fig.add_trace(go.Scatter(
            x=times,
            y=stances,
            mode='lines+markers',
            name=participant,
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(size=10, symbol='circle'),
            text=[d['message'] for d in data],
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         '时间: %{x|%H:%M:%S}<br>' +
                         '立场评分: %{y:.2f}<br>' +
                         '内容: %{text}<extra></extra>',
            connectgaps=True
        ))
    
    # 添加中线（立场中立线）
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  annotation_text="立场中立", annotation_position="right")
    
    fig.update_layout(
        title="观点演化轨迹（Y轴：-1=完全支持人类因素 → +1=完全支持算法因素）",
        xaxis_title="讨论时间轴",
        yaxis_title="立场评分",
        hovermode='x unified',
        height=450,
        yaxis=dict(range=[-1.2, 1.2]),
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 分析总结
    st.write("**演化分析：**")
    
    for participant in participants:
        if not evolution_data[participant]:
            continue
        
        initial_stance = evolution_data[participant][0]['stance']
        final_stance = evolution_data[participant][-1]['stance']
        change = final_stance - initial_stance
        
        col1, col2, col3, col4 = st.columns(4)
        col1.write(f"**{participant}**")
        col2.metric("初始立场", f"{initial_stance:.2f}")
        col3.metric("最终立场", f"{final_stance:.2f}")
        
        if abs(change) > 0.3:
            col4.metric("变化", f"{change:+.2f}", 
                       delta="📈 思想开放" if change > 0 else "📉 立场调整")
        else:
            col4.metric("变化", f"{change:+.2f}", delta="➡️ 观点稳定")


def calculate_stance_score(message, topic=""):
    """
    计算消息中的立场评分（针对社交媒体算法话题）
    返回: -1 (完全支持人类因素) ~ +1 (完全支持算法因素)
    
    可以根据不同话题灵活调整关键词
    """
    
    # 支持"算法"假说的关键词
    keywords_pro_algo = [
        '算法', 'algorithm', '推荐', 'recommend', '平台',
        '机制', 'mechanism', '设计', 'design', '系统',
        'system', '筛选', 'filter', '内容分发', '加剧',
        'exacerbate', '主要原因', 'primary', '根本'
    ]
    
    # 支持"人类因素"假说的关键词
    keywords_pro_human = [
        '个人', 'personal', '选择', 'choice', '用户',
        'user', '习惯', 'habit', '偏见', 'bias',
        '人类', 'human', '教育', 'education', '文化',
        'culture', '心理', 'psychology', '也'
    ]
    
    message_lower = message.lower()
    
    pro_algo_count = sum(1 for kw in keywords_pro_algo if kw in message_lower)
    pro_human_count = sum(1 for kw in keywords_pro_human if kw in message_lower)
    
    total = pro_algo_count + pro_human_count
    
    if total == 0:
        return 0  # 中立
    
    # 权重计算：算法得分 - 人类得分 / 总数
    stance = (pro_algo_count - pro_human_count) / total
    
    # 限制在 [-1, 1] 范围内
    return max(-1, min(1, stance))