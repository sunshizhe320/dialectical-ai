"""
矩阵更新管理器
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class MatrixUpdater:
    """实时矩阵更新器"""
    
    def __init__(self, cache_dir: str = "matrix_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_file(self, session_id: str) -> Path:
        return self.cache_dir / f"{session_id}_matrix.json"
    
    def get_state_file(self, session_id: str) -> Path:
        return self.cache_dir / f"{session_id}_state.json"
    
    def load_cache(self, session_id: str) -> Optional[Dict]:
        """加载缓存"""
        try:
            with open(self.get_cache_file(session_id), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def save_cache(self, session_id: str, data: Dict) -> bool:
        """保存缓存"""
        try:
            with open(self.get_cache_file(session_id), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载状态"""
        try:
            with open(self.get_state_file(session_id), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"processed_count": 0, "last_hash": None}
    
    def save_state(self, session_id: str, processed_count: int, content_hash: str = "") -> bool:
        """保存状态"""
        try:
            with open(self.get_state_file(session_id), 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_count": processed_count,
                    "last_hash": content_hash,
                    "timestamp": datetime.now().isoformat()
                }, f)
            return True
        except:
            return False
    
    def should_update(self, session_id: str, messages: List[Dict]) -> bool:
        """【关键】判断是否需要更新"""
        state = self.load_state(session_id)
        user_count = len([m for m in messages if m.get('user') != 'AI'])
        processed = state.get("processed_count", 0)
        
        # 消息数增加时更新
        return user_count > processed
    
    def should_update_viewpoints(self, session_id: str, messages: List[Dict]) -> bool:
        """判断是否需要更新观点（兼容旧版本）"""
        return self.should_update(session_id, messages)
    
    def update_state(self, session_id: str, processed_count: int, viewpoint_count: int = 0) -> None:
        """更新状态"""
        self.save_state(session_id, processed_count, "")
    
    def acquire_lock(self, session_id: str, timeout: int = 30) -> bool:
        """获取锁（简化版）"""
        return True  # 简化：直接返回 True
    
    def release_lock(self, session_id: str) -> None:
        """释放锁"""
        pass
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓存"""
        for f in [self.get_cache_file(session_id), self.get_state_file(session_id)]:
            try:
                f.unlink()
            except:
                pass
    
    def compute_content_hash(self, messages: List[Dict]) -> str:
        """计算消息哈希"""
        try:
            content = json.dumps(
                [(m.get('user'), m.get('message')) for m in messages],
                ensure_ascii=False
            )
            return hashlib.md5(content.encode()).hexdigest()
        except:
            return ""


# 全局实例
updater = MatrixUpdater()