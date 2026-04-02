 """
矩阵更新管理器 - 全局统一版本
确保所有设备看到相同的矩阵
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class MatrixUpdater:
    """实时矩阵更新器 - 全局统一"""
    
    def __init__(self, cache_dir: str = "matrix_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_session_cache_file(self, session_id: str) -> Path:
        """会话级缓存 - 全局统一"""
        return self.cache_dir / f"{session_id}_matrix_global.json"
    
    def get_session_state_file(self, session_id: str) -> Path:
        """会话级状态"""
        return self.cache_dir / f"{session_id}_state_global.json"
    
    def load_global_matrix(self, session_id: str) -> Optional[Dict]:
        """加载全局矩阵 - 所有设备看这个"""
        try:
            cache_file = self.get_session_cache_file(session_id)
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✓ 从缓存加载矩阵 (版本: {data.get('version', 'unknown')})")
                    return data
        except Exception as e:
            print(f"⚠️ 加载缓存失败: {e}")
        return None
    
    def save_global_matrix(self, session_id: str, data: Dict) -> bool:
        """保存全局矩阵 - 所有设备共用"""
        try:
            cache_file = self.get_session_cache_file(session_id)
            
            # 添加版本号和时间戳确保一致性
            data['version'] = int(time.time() * 1000)  # 毫秒级时间戳作为版本
            data['saved_at'] = datetime.now().isoformat()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 保存全局矩阵 (版本: {data['version']})")
            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def load_state(self, session_id: str) -> Dict:
        """加载状态"""
        try:
            with open(self.get_session_state_file(session_id), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"processed_count": 0, "last_version": None}
    
    def save_state(self, session_id: str, processed_count: int, version: int = 0) -> bool:
        """保存状态"""
        try:
            with open(self.get_session_state_file(session_id), 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_count": processed_count,
                    "last_version": version,
                    "timestamp": datetime.now().isoformat()
                }, f)
            return True
        except:
            return False
    
    def should_update(self, session_id: str, messages: List[Dict]) -> bool:
        """判断是否需要更新"""
        state = self.load_state(session_id)
        user_count = len([m for m in messages if m.get('user') != 'AI'])
        processed = state.get("processed_count", 0)
        
        # 只在消息数变化时更新
        should_update = user_count > processed
        
        if should_update:
            print(f"📢 需要更新: 新消息数 {user_count} > 已处理 {processed}")
        
        return should_update
    
    def clear_cache(self, session_id: str) -> None:
        """清空缓存"""
        for f in [self.get_session_cache_file(session_id), self.get_session_state_file(session_id)]:
            try:
                if f.exists():
                    f.unlink()
                    print(f"✓ 删除缓存: {f.name}")
            except:
                pass


updater = MatrixUpdater()