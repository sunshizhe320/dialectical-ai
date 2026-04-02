"""
experiment_manager.py
實驗分組管理介面
- 批量建立 groups
- 分配 condition（Socratic / Debater / Control）
- 匯出實驗配置
- 查看 & 刪除現有 groups
"""
import streamlit as st
import sqlite3
import csv
import io
from datetime import datetime

DB_PATH = "chat_logs.db"

st.set_page_config(page_title="Experiment Manager", layout="wide")
st.title("🔬 實驗分組管理")

st.markdown("""
本頁面用於建立與管理實驗分組。你可以：
- 批量建立多個 groups（例如 A1, A2, ... B1, B2...）
- 為每個 group 分配實驗條件（condition）
- 匯出實驗配置作為參考
- 查看與刪除現有分組
""")

st.markdown("---")

# ===== Tab 1: 批量建立分組 =====
tab1, tab2, tab3 = st.tabs(["批量建立", "查看現有分組", "設定 Prompt"])

with tab1:
    st.subheader("批量建立 Groups")
    
    st.write("**方式 1：按模式快速建立**")
    col1, col2, col3 = st.columns(3)
    with col1:
        num_groups_per_condition = st.number_input(
            "每個 condition 建立幾個 groups？", 
            min_value=1, max_value=20, value=3, step=1
        )
    with col2:
        prefix = st.text_input("Group 前綴（例如 A, B, C）", value="Exp")
    with col3:
        st.write("")  # 對齊
        st.write("")
    
    # 預覽建立的 groups
    st.write("**預覽即將建立的分組：**")
    conditions = ["AI-Scaffolded", "AI-Free-Debater", "Control"]
    preview_groups = []
    for cond_idx, cond in enumerate(conditions):
        for i in range(1, num_groups_per_condition + 1):
            group_id = f"{prefix}_{cond[0]}{i}"  # 例如 Exp_S1, Exp_F1, Exp_C1
            preview_groups.append({"Group ID": group_id, "Condition": cond})
    
    preview_df = __import__('pandas').DataFrame(preview_groups)
    st.dataframe(preview_df, use_container_width=True)
    
    if st.button("✓ 建立上述所有 Groups"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        created_count = 0
        
        for group_info in preview_groups:
            group_id = group_info["Group ID"]
            condition = group_info["Condition"]
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                c.execute("""
                INSERT INTO groups (group_id, condition, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(group_id) DO NOTHING
                """, (group_id, condition, ts))
                created_count += 1
            except Exception as e:
                st.error(f"建立 {group_id} 失敗：{e}")
        
        conn.commit()
        conn.close()
        st.success(f"✓ 成功建立 {created_count} 個 groups！")
    
    st.markdown("---")
    
    st.write("**方式 2：自訂建立**")
    st.write("若需要更自訂的分組（例如 GroupA, GroupB, ...），請在下方輸入：")
    
    custom_groups_text = st.text_area(
        "輸入自訂 groups（每行一個，格式：group_id,condition）",
        placeholder="Group_001,AI-Scaffolded\nGroup_002,AI-Free-Debater\nGroup_003,Control",
        height=150
    )
    
    if st.button("✓ 建立自訂 Groups"):
        if not custom_groups_text.strip():
            st.warning("請輸入分組資訊")
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            created_count = 0
            error_count = 0
            
            for line in custom_groups_text.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    st.warning(f"格式錯誤：{line}")
                    error_count += 1
                    continue
                
                group_id = parts[0].strip()
                condition = parts[1].strip()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                try:
                    c.execute("""
                    INSERT INTO groups (group_id, condition, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(group_id) DO NOTHING
                    """, (group_id, condition, ts))
                    created_count += 1
                except Exception as e:
                    st.error(f"建立 {group_id} 失敗：{e}")
                    error_count += 1
            
            conn.commit()
            conn.close()
            st.success(f"✓ 成功建立 {created_count} 個 groups！（{error_count} 個失敗）")

# ===== Tab 2: 查看現有分組 =====
with tab2:
    st.subheader("現有 Groups")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT group_id, condition, updated_at FROM groups ORDER BY group_id")
    groups = c.fetchall()
    conn.close()
    
    if not groups:
        st.info("暫無 groups，請先在「批量建立」頁面建立。")
    else:
        # 轉成 DataFrame 顯示
        import pandas as pd
        df_groups = pd.DataFrame(groups, columns=["Group ID", "Condition", "Last Updated"])
        st.dataframe(df_groups, use_container_width=True)
        
        # 統計資訊
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("總 Groups", len(groups))
        with col2:
            socratic_count = len([g for g in groups if g[1] == "AI-Scaffolded"])
            st.metric("Socratic", socratic_count)
        with col3:
            debater_count = len([g for g in groups if g[1] == "AI-Free-Debater"])
            st.metric("Free Debater", debater_count)
        with col4:
            control_count = len([g for g in groups if g[1] == "Control"])
            st.metric("Control", control_count)
        
        st.markdown("---")
        
        # 匯出為 CSV
        st.write("**匯出實驗配置**")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Group ID", "Condition", "Last Updated"])
        for group in groups:
            writer.writerow(group)
        
        st.download_button(
            "📥 下載實驗配置 CSV",
            data=buffer.getvalue(),
            file_name=f"experiment_groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        
        # 刪除選項（謹慎使用）
        st.write("**刪除 Groups（謹慎使用）**")
        if st.checkbox("我要刪除某個 group（包括其對話紀錄）"):
            group_to_delete = st.selectbox(
                "選擇要刪除的 group",
                [g[0] for g in groups]
            )
            
            if st.button(f"🗑️ 確認刪除 {group_to_delete}"):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM messages WHERE group_id = ?", (group_to_delete,))
                c.execute("DELETE FROM groups WHERE group_id = ?", (group_to_delete,))
                conn.commit()
                conn.close()
                st.success(f"✓ 已刪除 {group_to_delete} 及其所有��話紀錄")
                st.rerun()

# ===== Tab 3: 設定 Prompt =====
with tab3:
    st.subheader("設定預設 Prompts")
    
    st.write("在此設定各 condition 的預設 system prompt（可選，會用於新建立的 groups）")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**AI-Scaffolded Prompt**")
        scaffolded_prompt = st.text_area(
            "Socratic 教學助理 prompt",
            value=(
                "你是一個蘇格拉底式的教學助理。"
                "你主要提出引導性問題，幫助學生反思與拆解論點，而非給出直接答案。"
                "請問明確並循序地提出問題，引導學生檢驗假設與證據。"
            ),
            height=150,
            key="scaffolded"
        )
    
    with col2:
        st.write("**AI-Free-Debater Prompt**")
        debater_prompt = st.text_area(
            "積極辯手 prompt",
            value=(
                "你是一名積極辯手，會提出與學生不同的立場與反駁，"
                "並要求學生給予證據來支持其主張。保持禮貌且具建設性。"
            ),
            height=150,
            key="debater"
        )
    
    st.write("**Control Condition Prompt**（通常不使用 AI 干預）")
    control_prompt = st.text_area(
        "Control 組 prompt",
        value="（此組為控制組，系統不提供 AI 干預。）",
        height=100,
        key="control"
    )
    
    if st.button("💾 儲存 Prompts 為預設"):
        # 儲存到本地配置檔（簡易版，直接存成文本）
        config = {
            "AI-Scaffolded": scaffolded_prompt,
            "AI-Free-Debater": debater_prompt,
            "Control": control_prompt
        }
        import json
        with open("prompt_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        st.success("✓ 已儲存預設 prompts！")
    
    st.info("💡 提示：這些預設 prompts 可在建立新 groups 時自動使用，或在主頁面手動套用。")