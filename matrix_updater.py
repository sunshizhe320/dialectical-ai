"""
矩阵增量更新管理器
支持实时动态更新，每条新消息触发刷新
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class MatrixUpdater:
    """实时矩阵更新器"""
    
    def __init__(self, cache_dir: str = "matrix_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.locks = {}
    
    def get_cache_file(self, session_id: str) -> Path:
        return self.cache_dir / f"{session_id}_matrix.json"
    
    def get_state_file(self, session_id: str) -> Path:
        return self.cache_dir / f"{session_id}_state.json"
    
    def get_lock_file(self, session_id: str) -> Path:
        return self.cache_dir / f"{session_id}.lock"
    
    def load_cache(self, session_id: str) -> Optional[Dict]:
        """加载缓存"""
        cache_file = self.get_cache_file(session_id)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def save_cache(self, session_id: str, data: Dict) -> bool:
        """保存缓存"""
        cache_file = self.get_cache_file(session_id)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载状态"""
        state_file = self.get_state_file(session_id)
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "processed_message_count": 0,
            "last_update_time": None,
            "last_message_hash": None
        }
    
    def save_state(self, session_id: str, state: Dict) -> bool:
        """保存状态"""
        state_file = self.get_state_file(session_id)
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def should_update_matrix(self, session_id: str, current_messages: List[Dict]) -> bool:
        """判断是否需要更新表格"""
        state = self.load_state(session_id)
        processed_count = state.get("processed_message_count", 0)
        
        # 计算当前用户消息数
        current_count = len([m for m in current_messages if m.get('user') != 'AI'])
        
        # 如果有新消息，触发更新
        return current_count > processed_count
    
    def get_new_messages(
        self, 
        all_messages: List[Dict], 
        session_id: str
    ) -> Tuple[List[Dict], int, int]:
        """获取新消息"""
        state = self.load_state(session_id)
        processed_count = state.get("processed_message_count", 0)
        
        user_messages = [m for m in all_messages if m.get('user') != 'AI']
        
        new_messages = user_messages[processed_count:]
        total_count = len(user_messages)
        
        return new_messages, total_count, processed_count
    
    def acquire_lock(self, session_id: str, timeout: int = 30) -> bool:
        """获取锁"""
        lock_file = self.get_lock_file(session_id)
        start_time = time.time()
        
        while lock_file.exists():
            if time.time() - start_time > timeout:
                try:
                    lock_file.unlink()
                except:
                    pass
                break
            time.sleep(0.05)
        
        try:
            lock_file.touch()
            return True
        except:
            return False
    
    def release_lock(self, session_id: str) -> None:
        """释放锁"""
        lock_file = self.get_lock_file(session_id)
        try:
            if lock_file.exists():
                lock_file.unlink()
        except:
            pass
    
    def update_state(
        self, 
        session_id: str, 
        processed_count: int
    ) -> None:
        """更新状态"""
        state = {
            "processed_message_count": processed_count,
            "last_update_time": datetime.now().isoformat()
        }
        self.save_state(session_id, state)
    
    def compute_content_hash(self, messages: List[Dict]) -> str:
        """计算消息哈希"""
        content = json.dumps(
            [(m.get('user'), m.get('message')) for m in messages],
            ensure_ascii=False
        )
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓存"""
        for f in [self.get_cache_file(session_id), self.get_state_file(session_id)]:
            if f.exists():
                try:
                    f.unlink()
                except:
                    pass


updater = MatrixUpdater()