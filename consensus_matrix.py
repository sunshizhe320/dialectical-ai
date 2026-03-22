import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go  # ✅ 改回原来的方式

def render_consensus_matrix(messages, participants):
    """
    生成共识矩阵：
    - 横轴：主要观点/论点（自动提取）
    - 纵轴：参与者
    - 单元格：✓/×/△（同意/不同意/中立）
    """
    
    st.markdown("## 📊 **Consensus Matrix (共识热力图)**")
    
    # 自动提取关键观点
    viewpoints = extract_key_viewpoints(messages)
    
    if not viewpoints:
        st.info("💭 需要更多讨论数据来生成观点矩阵")
        return
    
    # 构建矩阵数据
    matrix_data = []
    for participant in participants:
        row = []
        for viewpoint in viewpoints:
            stance = classify_stance(participant, viewpoint, messages)
            row.append(stance)
        matrix_data.append(row)
    
    # 创建dataframe
    df_matrix = pd.DataFrame(
        matrix_data,
        index=participants,
        columns=[vp[:15] + "..." if len(vp) > 15 else vp for vp in viewpoints]
    )
    
    # 表格化呈现
    st.write("### 观点同意度矩阵")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        def color_stance(val):
            if val == "✓":
                return 'background-color: #90EE90'
            elif val == "×":
                return 'background-color: #FFB6C6'
            else:
                return 'background-color: #FFE4B5'
        
        styled_df = df_matrix.style.map(color_stance)
        st.dataframe(styled_df, use_container_width=True)
    
    with col2:
        st.write("**图例**")
        st.markdown("🟢 ✓ = 同意")
        st.markdown("🔴 × = 不同意")
        st.markdown("🟡 △ = 中立/未表态")
    
    # 热力图
    st.write("### 热力图视图")
    
    matrix_numeric = df_matrix.replace({
        '✓': 1,
        '△': 0,
        '×': -1
    })
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix_numeric.values,
        x=matrix_numeric.columns,
        y=matrix_numeric.index,
        colorscale='RdYlGn',
        zmid=0,
        text=df_matrix.values,
        texttemplate='%{text}',
        textfont={"size": 14},
        colorbar=dict(
            title="Stance",
            tickvals=[-1, 0, 1],
            ticktext=['Disagree', 'Neutral', 'Agree']
        )
    ))
    
    fig.update_layout(
        title="参与者-观点共识热力图",
        xaxis_title="关键观点",
        yaxis_title="参与者",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 统计数据
    st.write("### 共识度分析")
    
    if matrix_numeric.size > 0:
        consensus_score = (matrix_numeric == 1).sum().sum() / matrix_numeric.size
        disagreement_score = (matrix_numeric == -1).sum().sum() / matrix_numeric.size
        
        col1, col2, col3 = st.columns(3)
        col1.metric("共识度", f"{consensus_score*100:.1f}%", "✓")
        col2.metric("分歧度", f"{disagreement_score*100:.1f}%", "×")
        col3.metric("中立度", f"{(1-consensus_score-disagreement_score)*100:.1f}%", "△")


def extract_key_viewpoints(messages):
    """从讨论中自动提取关键观点"""
    
    if not messages:
        return []
    
    viewpoints = set()
    
    keywords_map = {
        "算法": "社交媒体算法影响",
        "个人选择": "个人使用习惯重要",
        "教育": "教育可以缓解问题",
        "平台": "平台设计需要改进",
        "偏见": "人类偏见是主要原因",
        "推荐": "推荐系统加剧极化",
        "内容": "内容分发机制有问题",
        "用户": "用户自主选择重要"
    }
    
    for msg in messages:
        content = msg.get('message', '').lower()
        for keyword, viewpoint in keywords_map.items():
            if keyword.lower() in content:
                viewpoints.add(viewpoint)
    
    if not viewpoints:
        viewpoints = {
            "算法是主要原因",
            "人类偏见很重要",
            "平台需要改进",
            "教育可以帮助"
        }
    
    return list(viewpoints)[:4]


def classify_stance(participant, viewpoint, messages):
    """判断参与者对某观点的立场"""
    
    participant_messages = [m for m in messages if m.get('user') == participant]
    
    if not participant_messages:
        return '△'
    
    support_count = 0
    oppose_count = 0
    
    for m in participant_messages:
        content = m.get('message', '').lower()
        
        if any(word in content for word in ['同意', '支持', '赞同', '确实', '是的', '对', 'agree', 'yes', 'support']):
            support_count += 1
        
        if any(word in content for word in ['不同意', '反对', '否则', '反而', '但是', 'disagree', 'no', 'oppose']):
            oppose_count += 1
    
    if support_count > oppose_count:
        return '✓'
    elif oppose_count > support_count:
        return '×'
    else:
        return '△'