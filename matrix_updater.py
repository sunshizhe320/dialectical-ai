"""
矩阵更新管理器
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
    (self, session_id: str) -> Optional[Dict]:
        """加载缓存"""
        try:
            cache_file = self.get_cache_file(session_id)
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载缓存失败: {e}")
        return None
    
    def save_cache(self, session_id: str, data: Dict) -> bool:
        """保存缓存"""
        try:
            cache_file = self.get_cache_file(session_id)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存缓存失败: {e}")
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载状态"""
        try:
            state_file = self.get_state_file(session_id)
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载状态失败: {e}")
        return {"processed_count": 0}
    
    def save_state(self, session_id: str, processed_count: int) -> bool:
        """保存状态"""
        try:
            state_file = self.get_state_file(session_id)
            with open(state_file, 'w', encoding='utf-8
    def get_cache_file(self, session_id: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{session_id}_matrix.json"
    
    def get_state_file(self, session_id: str) -> Path:
        """获取状态文件路径"""
        return self.cache_dir / f"{session_id}_state.json"
    
    def load_cache(self, session_id: str) -> Optional[Dict]:
        """加载缓存"""
        try:
            cache_file = self.get_cache_file(session_id)
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载缓存失败: {e}")
        return None
    
    def save_cache(self, session_id: str, data: Dict) -> bool:
        """保存缓存"""
        try:
            cache_file = self.get_cache_file(session_id)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存缓存失败: {e}")
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载状态"""
        try:
            state_file = self.get_state_file(session_id)
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)') as f:
                json.dump({
                    "processed_count": processed_count,
                    "timestamp": datetime.now().isoformat()
                }, f)
            return True
        except Exception as e:
            print(f"❌ 保存状态失败: {e}")
            return False
    
    def should_update(self, session_id: str, messages: List[Dict]) -> bool:
        """判断是否需要更新"""
        try:
            state = self.load_state(session_id)
            user_count = len([m for m in messages if m.get('user') != 'AI'])
            processed = state.get("processed_count", 0)
            return user_count > processed
        except Exception as e:
            print(f"⚠️ 判断更新失败: {e}")
            return False
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓存"""
        try:
            cache_file = self.get_cache_file(session_id)
            state_file = self.get_state_file(session_id)
            
            if cache_file.exists():
                cache_file.unlink()
                print(f"✓ 删除缓存: {cache_file.name}")
            
            if state_file.exists():
                state_file.unlink()
                print(f"✓ 删除状态: {state_file.name}")
        except Exception as e:
            print(f"❌ 清空缓存失败: {e}")


# 全局实例
updater = MatrixUpdater()