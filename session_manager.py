session_manager.py
"""
对话会话管理 - 支持长期和短期对话
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class ConversationSession:
    """单个对话会话"""
    def __init__(self, session_id: str, group_id: str, topic: str, condition: str):
        self.session_id = session_id
        self.group_id = group_id
        self.topic = topic
        self.condition = condition
        self.created_at = datetime.now().isoformat()
        self.messages = []
        self.metadata = {}
    
    def add_message(self, role: str, user: str, content: str):
        """添加消息"""
        self.messages.append({
            "role": role,
            "user": user,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict:
        """转为字典"""
        return {
            "session_id": self.session_id,
            "group_id": self.group_id,
            "topic": self.topic,
            "condition": self.condition,
            "created_at": self.created_at,
            "message_count": len(self.messages),
            "messages": self.messages
        }


class SessionManager:
    """对话会话管理器"""
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)
        self.current_session: Optional[ConversationSession] = None
    
    def create_session(self, group_id: str, topic: str, condition: str) -> str:
        """创建新会话"""
        session_id = f"{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = ConversationSession(session_id, group_id, topic, condition)
        self.current_session = session
        self._save_session(session)
        return session_id
    
    def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """加载已有会话"""
        path = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                session = ConversationSession(
                    data["session_id"],
                    data["group_id"],
                    data["topic"],
                    data["condition"]
                )
                session.messages = data["messages"]
                self.current_session = session
                return session
        return None
    
    def get_group_sessions(self, group_id: str) -> List[Dict]:
        """获取某个Group的所有会话"""
        sessions = []
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json") and filename.startswith(group_id):
                path = os.path.join(self.sessions_dir, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data["session_id"],
                        "topic": data["topic"],
                        "created_at": data["created_at"],
                        "message_count": len(data["messages"]),
                        "condition": data["condition"]
                    })
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)
    
    def get_all_groups(self) -> List[str]:
        """获取所有Group ID"""
        groups = set()
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                group_id = filename.split('_')[0]
                groups.add(group_id)
        return sorted(list(groups))
    
    def _save_session(self, session: ConversationSession):
        """保存会话到文件"""
        path = os.path.join(self.sessions_dir, f"{session.session_id}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
    
    def save_current_session(self):
        """保存当前会话"""
        if self.current_session:
            self._save_session(self.current_session)
    
    def add_message_to_current(self, role: str, user: str, content: str):
        """添加消息到当前会话"""
        if self.current_session:
            self.current_session.add_message(role, user, content)
            self.save_current_session()