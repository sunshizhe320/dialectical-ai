"""
矩阵更新管理器 - 简化版本
"""

import json
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
            cache_file = self.get_cache_file(session_id)
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
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
            pass
        return {"processed_count": 0}
    
    def save_state(self, session_id: str, processed_count: int) -> bool:
        """保存状态"""
        try:
            with open(self.get_state_file(session_id), 'w', encoding='utf-8') as f:
                json.dump({"processed_count": processed_count, "timestamp": datetime.now().isoformat()}, f)
            return True
        except:
            return False
    
    def should_update(self, session_id: str, messages: List[Dict]) -> bool:
        """判断是否需要更新"""
        state = self.load_state(session_id)
        user_count = len([m for m in messages if m.get('user') != 'AI'])
        processed = state.get("processed_count", 0)
        return user_count > processed
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓存"""
        for f in [self.get_cache_file(session_id), self.get_state_file(session_id)]:
            try:
                if f.exists():
                    f.unlink()
            except:
                pass


# 创建全局实例
updater = MatrixUpdater()