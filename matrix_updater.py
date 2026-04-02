"""
实时矩阵更新管理模块
负责实时检测新消息并触发矩阵更新
支持多人讨论和动态观点识别
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class MatrixCache:
    """矩阵缓存数据结构"""
    session_id: str
    viewpoints: List[str]
    stances: Dict
    processed_message_count: int
    last_update_time: str
    content_hash: str


class MatrixUpdater:
    """实时矩阵更新器 - 支持多人讨论和动态观点"""
    
    def __init__(self, cache_dir: str = "matrix_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.locks = {}  # 会话级锁
    
    def get_cache_file(self, session_id: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{session_id}_matrix.json"
    
    def get_lock_file(self, session_id: str) -> Path:
        """获取锁文件路径"""
        return self.cache_dir / f"{session_id}.lock"
    
    def get_state_file(self, session_id: str) -> Path:
        """获取状态文件路径"""
        return self.cache_dir / f"{session_id}_state.json"
    
    def load_cache(self, session_id: str) -> Optional[Dict]:
        """加载缓存数据"""
        cache_file = self.get_cache_file(session_id)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ 缓存加载失败: {e}")
                return None
        return None
    
    def save_cache(self, session_id: str, data: Dict) -> bool:
        """保存缓存数据"""
        cache_file = self.get_cache_file(session_id)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 缓存保存失败: {e}")
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载会话状态"""
        state_file = self.get_state_file(session_id)
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "processed_count": 0,
            "last_update": None,
            "viewpoints_count": 0
        }
    
    def save_state(self, session_id: str, state: Dict) -> bool:
        """保存会话状态"""
        state_file = self.get_state_file(session_id)
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 状态保存失败: {e}")
            return False
    
    def needs_update(self, session_id: str, current_message_count: int) -> bool:
        """检查是否需要更新矩阵"""
        state = self.load_state(session_id)
        processed_count = state.get("processed_count", 0)
        
        # 如果有新消息，需要更新
        return current_message_count > processed_count
    
    def should_update_viewpoints(
        self, 
        session_id: str, 
        current_messages: List[Dict]
    ) -> bool:
        """
        判断是否需要重新更新观点
        当消息数量变化超过 20% 时触发重新分析
        """
        state = self.load_state(session_id)
        
        previous_count = state.get("processed_count", 0)
        current_count = len([m for m in current_messages if m.get('user') != 'AI'])
        
        if current_count == 0:
            return False
        
        # 第一次分析或消息增加 20% 以上
        if previous_count == 0:
            return True
        
        change_ratio = (current_count - previous_count) / current_count
        return change_ratio > 0.2
    
    def get_new_messages(
        self, 
        all_messages: List[Dict], 
        session_id: str
    ) -> Tuple[List[Dict], int]:
        """获取自上次更新以来的新消息"""
        state = self.load_state(session_id)
        processed_count = state.get("processed_count", 0)
        
        # 只取用户消息（不包含AI）
        user_messages = [m for m in all_messages if m.get('user') != 'AI']
        new_messages = user_messages[processed_count:]
        
        return new_messages, len(user_messages)
    
    def acquire_lock(self, session_id: str, timeout: int = 60) -> bool:
        """获取会话锁（防止并发冲突）"""
        lock_file = self.get_lock_file(session_id)
        start_time = time.time()
        
        while lock_file.exists():
            if time.time() - start_time > timeout:
                # 超时强制删除旧锁
                try:
                    lock_file.unlink()
                    print(f"⚠️ 强制删除超时锁: {session_id}")
                except:
                    pass
                break
            time.sleep(0.1)
        
        try:
            lock_file.touch()
            return True
        except:
            return False
    
    def release_lock(self, session_id: str) -> None:
        """释放会话锁"""
        lock_file = self.get_lock_file(session_id)
        try:
            if lock_file.exists():
                lock_file.unlink()
        except:
            pass
    
    def update_state(
        self, 
        session_id: str, 
        processed_count: int,
        viewpoints_count: int
    ) -> None:
        """更新处理状态"""
        state = {
            "processed_count": processed_count,
            "last_update": datetime.now().isoformat(),
            "viewpoints_count": viewpoints_count
        }
        self.save_state(session_id, state)
    
    def compute_content_hash(self, messages: List[Dict]) -> str:
        """计算消息内容哈希"""
        content = json.dumps(
            [(m.get('user'), m.get('message')) for m in messages],
            ensure_ascii=False
        )
        return hashlib.md5(content.encode()).hexdigest()
    
    def should_force_refresh(self, session_id: str, current_hash: str) -> bool:
        """判断是否应该强制刷新"""
        cache = self.load_cache(session_id)
        if not cache:
            return True
        
        cached_hash = cache.get("content_hash")
        return current_hash != cached_hash
    
    def update_participant_stances(
        self,
        session_id: str,
        new_viewpoints: List[str],
        old_stances: Dict,
        participants: List[str]
    ) -> Dict:
        """
        当新增观点时，为新观点添加所有参与者的态度
        支持动态观点添加
        """
        updated_stances = dict(old_stances)
        
        # 获取旧观点
        old_viewpoints = []
        if participants and old_stances:
            first_participant = list(participants)[0]
            if first_participant in old_stances:
                old_viewpoints = list(old_stances[first_participant].keys())
        
        # 找出新增观点
        new_viewpoint_set = set(new_viewpoints) - set(old_viewpoints)
        
        if new_viewpoint_set:
            print(f"🆕 检测到 {len(new_viewpoint_set)} 个新观点")
            
            # 为所有参与者初始化新观点的态度
            for participant in participants:
                if participant not in updated_stances:
                    updated_stances[participant] = {}
                
                for new_vp in new_viewpoint_set:
                    updated_stances[participant][new_vp] = '△'
        
        return updated_stances
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓存"""
        cache_file = self.get_cache_file(session_id)
        state_file = self.get_state_file(session_id)
        lock_file = self.get_lock_file(session_id)
        
        for f in [cache_file, state_file, lock_file]:
            if f.exists():
                try:
                    f.unlink()
                except:
                    pass
        
        print(f"✅ 已清空 {session_id} 的缓存")
    
    def get_update_stats(self, session_id: str) -> Dict:
        """获取更新统计信息"""
        cache = self.load_cache(session_id)
        state = self.load_state(session_id)
        
        return {
            "has_cache": cache is not None,
            "processed_count": state.get("processed_count", 0),
            "viewpoints_count": state.get("viewpoints_count", 0),
            "last_update": state.get("last_update"),
            "cache_exists": self.get_cache_file(session_id).exists()
        }


# 全局实例
updater = MatrixUpdater()