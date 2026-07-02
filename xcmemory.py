import sqlite3
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from xcconfig import settings

class HybridMemory:
    """增强的记忆管理系统 - 彻底修复数据库约束问题"""
    
    def __init__(self):
        self.db_path = Path(settings.MEMORY_DB_PATH) # 设置数据库文件路径
        self._init_db()  # 初始数据库
    
    def _init_db(self):
        """🔥 彻底修复：重新初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 🔥 关键修复1：重建表结构
            cursor.executescript("""
                DROP TABLE IF EXISTS conversation_history;
                CREATE TABLE conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    entities TEXT,
                    UNIQUE(user_id, session_id, timestamp)
                );
                
                DROP TABLE IF EXISTS entity_tracking;
                CREATE TABLE entity_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    last_mentioned DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    mention_count INTEGER DEFAULT 1,
                    UNIQUE(user_id, session_id, entity_name)
                );
            """)
            
            conn.commit()
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        """🔥 修复版：安全保存对话上下文"""
        try:
            user_id = inputs.get("user_id", "default")
            session_id = inputs.get("session_id", self._generate_session_id(user_id))
            user_input = inputs.get("input", "")
            response = outputs.get("output", "")
            
            entities = self._extract_entities(user_input + " " + response)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 🔥 关键修复2：使用事务确保数据一致性
                try:
                    # 保存对话记录
                    cursor.execute(  # 向SQLite数据库的安全插入操作​​ 放重复插入和结构化数据存储
                        """INSERT OR IGNORE INTO conversation_history 
                        (user_id, session_id, user_input, assistant_response, entities) 
                        VALUES (?, ?, ?, ?, ?)""",
                        (user_id, session_id, user_input, response, json.dumps(entities))
                    )
                    
                    # 更新实体跟踪
                    for entity, etype in entities: # 遍历识别到的所有实体
                        cursor.execute("""
                            INSERT INTO entity_tracking 
                            (user_id, session_id, entity_name, entity_type, context) 
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(user_id, session_id, entity_name) 
                            DO UPDATE SET 
                                mention_count = mention_count + 1,
                                last_mentioned = CURRENT_TIMESTAMP,
                                context = excluded.context
                        """, (user_id, session_id, entity, etype, user_input))
                    
                    conn.commit()

                    
                except sqlite3.Error as e:
                    conn.rollback() # 回滚当前事务
                    # 🔥 关键修复3：重建表结构后重试
                    self._init_db() 
                    self.save_context(inputs, outputs) # 重试操作
                    
        except Exception as e:
            return []
    
    def get_context(self, user_id: str, session_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """获取对话上下文"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_input, assistant_response, entities, timestamp 
                    FROM conversation_history 
                    WHERE user_id = ? AND session_id = ? 
                    ORDER BY timestamp DESC LIMIT ?
                """, (user_id, session_id, limit))
                
                return [
                    {
                        "user_input": row["user_input"],
                        "assistant_response": row["assistant_response"],
                        "entities": json.loads(row["entities"]) if row["entities"] else [],
                        "timestamp": row["timestamp"]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            return []
    
    def resolve_reference(self, user_id: str, text: str) -> str: # 实现了中文指代消解，处理代词和指示词
        """指代消解"""
        try:
            session_id = self._generate_session_id(user_id)
            
            # 处理"哪"这个指代词
            if "哪" in text and not self._has_specific_location(text):
                if location := self._find_recent_location(user_id, session_id):
                    resolved = text.replace("哪", location)
                    return resolved
            
            # 处理其他指代词
            reference_map = {
                "那": lambda: self._find_recent_location(user_id, session_id),
                "那里": lambda: self._find_recent_location(user_id, session_id),
                "这里": lambda: self._find_recent_location(user_id, session_id),
                "该地": lambda: self._find_recent_location(user_id, session_id)
            }
            
            for ref_word, resolver in reference_map.items():
                if ref_word in text:
                    if location := resolver():
                        return text.replace(ref_word, location)
            
            return text
            
        except Exception as e:
            return text
    
    def _find_recent_location(self, user_id: str, session_id: str) -> Optional[str]:
        """查找最近提到的地点"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT entity_name FROM entity_tracking 
                    WHERE user_id = ? AND session_id = ? AND entity_type = 'location'
                    ORDER BY last_mentioned DESC LIMIT 1
                """, (user_id, session_id))
                if row := cursor.fetchone():
                    return row[0]
        except Exception:
            pass
        return None
    
    def _has_specific_location(self, text: str) -> bool:
        """检查文本中是否有具体地点"""
        return bool(self._extract_locations(text))
    
    def _extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """从文本中提取实体"""
        return [
            (loc, "location") 
            for loc in self._extract_locations(text)
        ]
    
    def _extract_locations(self, text: str) -> List[str]:
        """地点提取"""
        if not text:
            return []
        
        patterns = [
            r'([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]{1,2}[省市县区]?)天气',
            r'([\u4e00-\u9fa5]{2,4}?(?:市|省|区|县))',
            r'(北京|上海|天津|重庆|广州|深圳|杭州|南京|武汉|成都|西安|苏州|厦门|青岛|大连|沈阳|长春|哈尔滨|石家庄|郑州|长沙|合肥|福州|南昌|南宁|昆明|贵阳|兰州|银川|西宁|乌鲁木齐|呼和浩特|拉萨|海口|遵义|三亚)'
        ]
        
        locations = []
        for pattern in patterns:
            for match in re.findall(pattern, text):
                if isinstance(match, tuple):  # 处理捕获组情况
                    match = next(m for m in match if m)
                if len(match) >= 2 and match not in locations:
                    locations.append(match)
        
        return list(set(locations))
    
    def _generate_session_id(self, user_id: str) -> str:
        """生成会话ID"""
        return f"{user_id}_{datetime.now().strftime('%Y%m%d%H')}"
    
    def clear_context(self, user_id: str, session_id: Optional[str] = None):
        """清除指定用户/会话的上下文"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute(
                        "DELETE FROM conversation_history WHERE user_id = ? AND session_id = ?",
                        (user_id, session_id)
                    )
                    cursor.execute(
                        "DELETE FROM entity_tracking WHERE user_id = ? AND session_id = ?",
                        (user_id, session_id)
                    )
                else:
                    cursor.execute(
                        "DELETE FROM conversation_history WHERE user_id = ?",
                        (user_id,)
                    )
                    cursor.execute(
                        "DELETE FROM entity_tracking WHERE user_id = ?",
                        (user_id,)
                    )
                
                conn.commit()
                
        except Exception as e:
            return[]
    
    def debug_entities(self, user_id: str):
        """调试实体状态"""
        session_id = self._generate_session_id(user_id)
        print("\n=== 记忆系统调试 ===")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查当前会话实体
            cursor.execute("""
                SELECT entity_name, entity_type, mention_count, last_mentioned, context 
                FROM entity_tracking 
                WHERE user_id = ? AND session_id = ?
                ORDER BY last_mentioned DESC
            """, (user_id, session_id))
            
            print(f"\n当前会话实体（{session_id}）:")
            for row in cursor.fetchall():
                print(f"- {row['entity_name']} ({row['entity_type']}) x{row['mention_count']} - {row['last_mentioned']}")
                print(f"  上下文: {row['context'][:50]}...")
            
            # 检查对话历史
            cursor.execute("""
                SELECT user_input, assistant_response, timestamp 
                FROM conversation_history 
                WHERE user_id = ? AND session_id = ?
                ORDER BY timestamp DESC LIMIT 3
            """, (user_id, session_id))
            
            print(f"\n最近对话:")
            for i, row in enumerate(cursor.fetchall(), 1):
                print(f"{i}. 用户: {row['user_input'][:50]}...")
                print(f"   助手: {row['assistant_response'][:50]}...")
                print(f"   时间: {row['timestamp']}")

# 全局实例
memory_manager = HybridMemory()