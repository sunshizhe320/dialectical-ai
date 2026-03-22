import streamlit as st
import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go

def render_consensus_matrix(messages, participants):
    """
    生成共识矩阵：
    - 横轴：主要观点/论点（自动提取）
    - 纵轴：参与者
    - 单元格：✓/×/△（同意/不同意/中立）
    """
    
    st.markdown("## 📊 **Consensus Matrix (共识热力图)**")
    
    # 自动提取关键观点
    viewpoints = extract_key_viewpoints(messages)  # 从讨论中提取
    
    # 构建矩阵数据
    matrix_data = []
    for participant in participants:
        row = []
        for viewpoint in viewpoints:
            # 通过AI判断该参与者是否支持该观点
            stance = classify_stance(participant, viewpoint, messages)
            row.append(stance)  # ✓ / × / △
        matrix_data.append(row)
    
    # 创建dataframe
    df_matrix = pd.DataFrame(
        matrix_data,
        index=participants,
        columns=[vp[:15] + "..." for vp in viewpoints]  # 截断长观点名
    )
    
    # 方法A: 表格化呈现
    st.write("### 观点同意度矩阵")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 用颜色编码
        def color_stance(val):
            if val == "✓":
                return 'background-color: #90EE90'  # 绿色=同意
            elif val == "×":
                return 'background-color: #FFB6C6'  # 红色=不同意
            else:
                return 'background-color: #FFE4B5'  # 黄色=中立
        
        styled_df = df_matrix.style.map(color_stance)
        st.dataframe(styled_df, use_container_width=True)
    
    with col2:
        st.write("**图例**")
        st.markdown("🟢 ✓ = 同意")
        st.markdown("🔴 × = 不同意")
        st.markdown("🟡 △ = 中立/未表态")
    
    # 方法B: 热力图（更炫酷）
    st.write("### 热力图视图")
    
    # 转换为数值（便于热力图）
    matrix_numeric = df_matrix.replace({
        '✓': 1,
        '△': 0,
        '×': -1
    })
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix_numeric.values,
        x=matrix_numeric.columns,
        y=matrix_numeric.index,
        colorscale='RdYlGn',  # 红-黄-绿
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
    consensus_score = (matrix_numeric == 1).sum().sum() / matrix_numeric.size
    disagreement_score = (matrix_numeric == -1).sum().sum() / matrix_numeric.size
    
    col1, col2, col3 = st.columns(3)
    col1.metric("共识度", f"{consensus_score*100:.1f}%", "✓")
    col2.metric("分歧度", f"{disagreement_score*100:.1f}%", "×")
    col3.metric("中立度", f"{(1-consensus_score-disagreement_score)*100:.1f}%", "△")


def extract_key_viewpoints(messages):
    """从讨论中自动提取关键观点"""
    # 调用AI分析关键论点
    viewpoints = [
        "社交媒体算法加剧极化",
        "人类偏见是主要原因",
        "个人使用习惯重要",
        "教育可以缓解问题",
        "平台设计需要改进"
    ]
    return viewpoints[:4]  # 取前4个


def classify_stance(participant, viewpoint, messages):
    """判断参与者对某观点的立场"""
    # 简化版：可以调用AI或规则引擎
    # 这里示例用规则
    participant_messages = [m for m in messages if m['user'] == participant]
    
    # 计算支持/反对的词频
    support_count = sum(1 for m in participant_messages if '同意' in m['message'] or '支持' in m['message'])
    oppose_count = sum(1 for m in participant_messages if '不同意' in m['message'] or '反对' in m['message'])
    
    if support_count > oppose_count:
        return '✓'
    elif oppose_count > support_count:
        return '×'
    else:
        return '△'