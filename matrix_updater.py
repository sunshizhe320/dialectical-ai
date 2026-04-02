"""
矩阵更新管理器 - 完整版本
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import threading


class MatrixUpdater:
    """实时矩阵更新器"""
    
    def __init__(self, cache_dir: str = "matrix_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.locks = {}
    
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
            print(f"警告: 加载缓存失败 {e}")
        return None
    
    def save_cache(self, session_id: str, data: Dict) -> bool:
        """保存缓存"""
        try:
            cache_file = self.get_cache_file(session_id)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"错误: 保存缓存失败 {e}")
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载状态"""
        try:
            state_file = self.get_state_file(session_id)
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"警告: 加载状态失败 {e}")
        return {"processed_count": 0, "viewpoint_count": 0}
    
    def save_state(self, session_id: str, processed_count: int) -> bool:
        """保存状态"""
        try:
            state_file = self.get_state_file(session_id)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_count": processed_count,
                    "timestamp": datetime.now().isoformat()
                }, f)
            return True
        except Exception as e:
            print(f"错误: 保存状态失败 {e}")
            return False
    
    def update_state(self, session_id: str, processed_count: int, viewpoint_count: int) -> bool:
        """更新状态（包括观点数）"""
        try:
            state_file = self.get_state_file(session_id)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_count": processed_count,
                    "viewpoint_count": viewpoint_count,
                    "timestamp": datetime.now().isoformat()
                }, f)
            return True
        except Exception as e:
            print(f"错误: 更新状态失败 {e}")
            return False
    
    def should_update(self, session_id: str, messages: List[Dict]) -> bool:
        """判断是否需要更新矩阵"""
        try:
            state = self.load_state(session_id)
            user_count = len([m for m in messages if m.get('user') != 'AI'])
            processed = state.get("processed_count", 0)
            return user_count > processed
        except Exception as e:
            print(f"警告: 判断更新失败 {e}")
            return False
    
    def should_update_viewpoints(self, session_id: str, messages: List[Dict]) -> bool:
        """判断是否需要更新观点"""
        try:
            state = self.load_state(session_id)
            user_count = len([m for m in messages if m.get('user') != 'AI'])
            processed = state.get("processed_count", 0)
            return user_count > processed
        except Exception as e:
            print(f"警告: 判断观点更新失败 {e}")
            return False
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓���和状态"""
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
            print(f"警告: 清空缓存失败 {e}")
    
    def acquire_lock(self, session_id: str, timeout: int = 60) -> bool:
        """获取锁（用于并发安全）"""
        try:
            if session_id not in self.locks:
                self.locks[session_id] = threading.Lock()
            return self.locks[session_id].acquire(timeout=timeout)
        except Exception as e:
            print(f"警告: 获取锁失败 {e}")
            return False
    
    def release_lock(self, session_id: str) -> None:
        """释放锁"""
        try:
            if session_id in self.locks:
                self.locks[session_id].release()
        except Exception as e:
            print(f"警告: 释放锁失败 {e}")


# 全局实例
updater = MatrixUpdater()