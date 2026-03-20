# db.py - 数据库管理模块（支持多成员会话）
import sqlite3
import time
from datetime import datetime, timedelta

DB_PATH = "chat_logs.db"

DEBUG = False  # 调试模式

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Messages 表 - 讨论消息
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        user TEXT,
        role TEXT,
        message TEXT,
        timestamp TEXT
    )
    """)
    
    # Sessions 表 - 讨论会话（NEW）
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        team_name TEXT,
        topic TEXT,
        mode TEXT,
        created_at TEXT,
        created_by TEXT
    )
    """)
    
    # Participants 表 - 参与者（NEW）
    c.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        user_name TEXT,
        joined_at TEXT,
        last_active TEXT
    )
    """)
    
    conn.commit()
    conn.close()


def save_message(session_id, user, role, message):
    """保存消息到数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    c.execute(
        "INSERT INTO messages (session_id, user, role, message, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, user, role, message, ts)
    )
    conn.commit()
    conn.close()
    if DEBUG:
        print(f"[DB] 保存消息: {session_id} - {user} - {message[:30]}...")


def get_history(session_id, limit=100):
    """获取会话的对话历史"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT user, role, message, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
        (session_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [{"user": r[0], "role": r[1], "message": r[2], "timestamp": r[3]} for r in rows]


def get_or_create_session(team_name, topic, mode, created_by):
    """
    获取或创建会话
    如果已存在相同的 team_name + topic，返回现有的 session_id
    否则创建新的 session_id
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 检查是否已存在
    c.execute(
        "SELECT session_id FROM sessions WHERE team_name = ? AND topic = ?",
        (team_name, topic)
    )
    result = c.fetchone()
    
    if result:
        session_id = result[0]
        if DEBUG:
            print(f"[DB] 找到现有会话: {session_id}")
    else:
        # 创建新会话
        # 使用小组名称 + 主题摘要 + 时间戳作为 session_id
        topic_short = topic.replace('？', '').replace('?', '')[:20]
        session_id = f"{team_name}_{topic_short}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        c.execute(
            "INSERT INTO sessions (session_id, team_name, topic, mode, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, team_name, topic, mode, ts, created_by)
        )
        conn.commit()
        if DEBUG:
            print(f"[DB] 创建新会话: {session_id}")
    
    conn.close()
    return session_id


def add_participant(session_id, user_name):
    """添加或更新参与者"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # 检查是否已存在
    c.execute(
        "SELECT id FROM participants WHERE session_id = ? AND user_name = ?",
        (session_id, user_name)
    )
    
    if not c.fetchone():
        # 新参与者，插入
        c.execute(
            "INSERT INTO participants (session_id, user_name, joined_at, last_active) VALUES (?, ?, ?, ?)",
            (session_id, user_name, ts, ts)
        )
        if DEBUG:
            print(f"[DB] 新参与者加入: {user_name}")
    else:
        # 已存在，更新最后活动时间
        c.execute(
            "UPDATE participants SET last_active = ? WHERE session_id = ? AND user_name = ?",
            (ts, session_id, user_name)
        )
        if DEBUG:
            print(f"[DB] 更新参与者活动时间: {user_name}")
    
    conn.commit()
    conn.close()


def get_session_participants(session_id):
    """获取会话的活跃参与者（5分钟内）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 获取5分钟内活跃的参与者
    cutoff_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute(
        "SELECT user_name FROM participants WHERE session_id = ? AND last_active > ? ORDER BY joined_at ASC",
        (session_id, cutoff_time)
    )
    
    participants = [row[0] for row in c.fetchall()]
    conn.close()
    
    if DEBUG:
        print(f"[DB] 获取参与者: {session_id} - {participants}")
    
    return participants


def get_session_info(session_id):
    """获取会话信息"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute(
        "SELECT team_name, topic, mode, created_at, created_by FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    
    result = c.fetchone()
    conn.close()
    
    if result:
        info = {
            "team_name": result[0],
            "topic": result[1],
            "mode": result[2],
            "created_at": result[3],
            "created_by": result[4]
        }
        if DEBUG:
            print(f"[DB] 获取会话信息: {session_id}")
        return info
    return None


def set_group_condition(group_id, condition):
    """设置讨论组条件（保持兼容性）"""
    pass


def get_group_condition(group_id):
    """获取讨论组条件（保持兼容性）"""
    pass