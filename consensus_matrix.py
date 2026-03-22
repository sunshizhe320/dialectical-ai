import streamlit as st
import pandas as pd
import numpy as np


def render_consensus_matrix(messages, participants):
    """生成共识矩阵"""
    
    st.markdown("## 📊 Consensus Matrix")
    
    if len(messages) < 2 or len(participants) < 2:
        st.info("💭 Need more messages from multiple participants")
        return
    
    # 提取观点
    viewpoints = extract_key_viewpoints(messages)
    
    if not viewpoints:
        st.info("💭 Not enough viewpoints to analyze")
        return
    
    # 构建矩阵
    matrix_data = []
    for participant in participants:
        row = []
        for viewpoint in viewpoints:
            stance = classify_stance(participant, viewpoint, messages)
            row.append(stance)
        matrix_data.append(row)
    
    df_matrix = pd.DataFrame(
        matrix_data,
        index=participants,
        columns=[vp[:12] + "..." if len(vp) > 12 else vp for vp in viewpoints]
    )
    
    # 颜色映射
    def color_stance(val):
        if val == "✓":
            return 'background-color: #90EE90'
        elif val == "×":
            return 'background-color: #FFB6C6'
        else:
            return 'background-color: #FFE4B5'
    
    styled_df = df_matrix.style.map(color_stance)
    st.dataframe(styled_df, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✓ = 同意**")
        st.markdown("**× = 不同意**")
    with col2:
        st.markdown("**△ = 中立**")


def extract_key_viewpoints(messages):
    """提取关键观点"""
    viewpoints = set()
    
    keywords_map = {
        "算法": "算法影响",
        "个人": "个人选择",
        "教育": "教育作用",
        "平台": "平台设计"
    }
    
    for msg in messages:
        content = msg.get('message', '').lower()
        for keyword, viewpoint in keywords_map.items():
            if keyword.lower() in content:
                viewpoints.add(viewpoint)
    
    return list(viewpoints)[:4] if viewpoints else ["观点1", "观点2", "观点3"]


def classify_stance(participant, viewpoint, messages):
    """判断立场"""
    participant_msgs = [m for m in messages if m.get('user') == participant]
    
    if not participant_msgs:
        return '△'
    
    support = 0
    oppose = 0
    
    for m in participant_msgs:
        content = m.get('message', '').lower()
        if any(w in content for w in ['同意', '支持', '对', 'yes', 'agree']):
            support += 1
        if any(w in content for w in ['反对', '不同意', 'no', 'disagree']):
            oppose += 1
    
    if support > oppose:
        return '✓'
    elif oppose > support:
        return '×'
    else:
        return '△'