# db.py - 数据库管理模块（修复版）
import sqlite3
import time
from datetime import datetime, timedelta

DB_PATH = "chat_logs.db"

DEBUG = False

def init_db():
    """初始化数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Messages 表
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
        
        # Sessions 表
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
        
        # Participants 表
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
        print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")


def save_message(session_id, user, role, message):
    """保存消息到数据库"""
    try:
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
            print(f"[DB] 保存消息: {session_id} - {user}")
    except Exception as e:
        print(f"❌ 保存消息失败: {e}")


def get_history(session_id, limit=100):
    """获取会话的对话历史 - 修复版"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 修复：使用正确的 SQL 语法
        c.execute(
            "SELECT user, role, message, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit)
        )
        rows = c.fetchall()
        conn.close()
        
        return [{"user": r[0], "role": r[1], "message": r[2], "timestamp": r[3]} for r in rows]
    except Exception as e:
        print(f"❌ 获取历史失败: {e}")
        return []


def get_or_create_session(team_name, topic, mode, created_by):
    """获取或创建会话"""
    try:
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
    except Exception as e:
        print(f"❌ 会话操作失败: {e}")
        return None


def add_participant(session_id, user_name):
    """添加或更新参与者"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # 检查是否已存在
        c.execute(
            "SELECT id FROM participants WHERE session_id = ? AND user_name = ?",
            (session_id, user_name)
        )
        
        if not c.fetchone():
            c.execute(
                "INSERT INTO participants (session_id, user_name, joined_at, last_active) VALUES (?, ?, ?, ?)",
                (session_id, user_name, ts, ts)
            )
        else:
            c.execute(
                "UPDATE participants SET last_active = ? WHERE session_id = ? AND user_name = ?",
                (ts, session_id, user_name)
            )
        
        conn.commit()
        conn.close()
        if DEBUG:
            print(f"[DB] 参与者: {user_name}")
    except Exception as e:
        print(f"❌ 参与者操作失败: {e}")


def get_session_participants(session_id):
    """获取会话的活跃参与者"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute(
            "SELECT user_name FROM participants WHERE session_id = ? AND last_active > ? ORDER BY joined_at ASC",
            (session_id, cutoff_time)
        )
        
        participants = [row[0] for row in c.fetchall()]
        conn.close()
        
        if DEBUG:
            print(f"[DB] 获取参与者: {session_id}")
        
        return participants
    except Exception as e:
        print(f"❌ 获取参与者失败: {e}")
        return []


def get_session_info(session_id):
    """获取会话信息"""
    try:
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
    except Exception as e:
        print(f"❌ 获取会话信息失败: {e}")
        return None


def set_group_condition(group_id, condition):
    """兼容函数"""
    pass


def get_group_condition(group_id):
    """兼容函数"""
    pass