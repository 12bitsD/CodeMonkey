"""SQLite 数据库适配器

实现基于 SQLite 的数据库操作
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .base import DatabaseAdapter


class SQLiteAdapter(DatabaseAdapter):
    """SQLite 数据库适配器"""
    
    def __init__(self, database_path: str = "./database.sqlite"):
        self.database_path = database_path
        self._connection = None
    
    @contextmanager
    def _get_db(self):
        """获取数据库连接上下文"""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将 sqlite3.Row 转换为字典"""
        if row is None:
            return None
        return dict(row)
    
    # ==================== 连接管理 ====================
    
    async def connect(self):
        """SQLite 不需要显式连接"""
        pass
    
    async def disconnect(self):
        """SQLite 不需要显式断开"""
        pass
    
    def init_database(self, run_seed: bool = True):
        """初始化数据库表结构"""
        with self._get_db() as db:
            # 用户表
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 用户画像表
            db.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT UNIQUE NOT NULL,
                    occupation TEXT,
                    education TEXT,
                    programming_level TEXT DEFAULT '入门',
                    math_level TEXT DEFAULT '入门',
                    abilities TEXT DEFAULT '[]',
                    mastered_knowledge TEXT DEFAULT '[]',
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # 学习计划表
            db.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    original_input TEXT,
                    target_node_id TEXT,
                    progress INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    last_access_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 知识节点表
            db.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT DEFAULT 'unlearned',
                    x REAL DEFAULT 0,
                    y REAL DEFAULT 0,
                    why TEXT,
                    what TEXT,
                    mastery TEXT,
                    prompt TEXT,
                    resources TEXT,
                    is_target INTEGER DEFAULT 0,
                    domain TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
                )
            """)
            
            # 边表
            db.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT NOT NULL,
                    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
                    FOREIGN KEY (from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (to_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    UNIQUE(plan_id, from_node_id, to_node_id)
                )
            """)
            
            # 学习会话表
            db.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_name TEXT,
                    action TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
            """)
            
            # 笔记表
            db.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # 创建默认用户
            db.execute("""
                INSERT OR IGNORE INTO users (id, email, password_hash)
                VALUES ('user_default', 'default@example.com', 'mock_hash')
            """)
            
            db.commit()
    
    # ==================== 用户管理 ====================
    
    def create_user(self, user_id: str, email: str, password_hash: str) -> Dict[str, Any]:
        """创建用户"""
        with self._get_db() as db:
            db.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash)
            )
            db.commit()
            
            row = db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return self._row_to_dict(row)
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户"""
        with self._get_db() as db:
            row = db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            return self._row_to_dict(row)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        with self._get_db() as db:
            row = db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return self._row_to_dict(row)
    
    # ==================== 用户画像 ====================
    
    def create_user_profile(
        self, 
        profile_id: str, 
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建用户画像"""
        with self._get_db() as db:
            db.execute(
                """INSERT INTO user_profiles 
                   (id, user_id, occupation, education, programming_level, math_level, abilities, mastered_knowledge)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile_id,
                    user_id,
                    kwargs.get('occupation'),
                    kwargs.get('education'),
                    kwargs.get('programming_level', '入门'),
                    kwargs.get('math_level', '入门'),
                    '[]',
                    '[]'
                )
            )
            db.commit()
            
            row = db.execute(
                "SELECT * FROM user_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            return self._row_to_dict(row)
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        with self._get_db() as db:
            row = db.execute(
                """SELECT occupation, education, programming_level, math_level, 
                          abilities, mastered_knowledge
                   FROM user_profiles WHERE user_id = ?""",
                (user_id,)
            ).fetchone()
            
            if not row:
                return None
            
            profile = self._row_to_dict(row)
            # 解析 JSON 字段
            profile['abilities'] = json.loads(profile['abilities']) if profile['abilities'] else []
            profile['mastered_knowledge'] = json.loads(profile['mastered_knowledge']) if profile['mastered_knowledge'] else []
            
            return profile
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户画像"""
        with self._get_db() as db:
            update_fields = []
            params = []
            
            if 'occupation' in updates:
                update_fields.append("occupation = ?")
                params.append(updates['occupation'])
            
            if 'education' in updates:
                update_fields.append("education = ?")
                params.append(updates['education'])
            
            if 'programmingLevel' in updates:
                update_fields.append("programming_level = ?")
                params.append(updates['programmingLevel'])
            
            if 'mathLevel' in updates:
                update_fields.append("math_level = ?")
                params.append(updates['mathLevel'])
            
            if 'abilities' in updates:
                update_fields.append("abilities = ?")
                params.append(json.dumps(updates['abilities'], ensure_ascii=False))
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)
                
                query = f"UPDATE user_profiles SET {', '.join(update_fields)} WHERE user_id = ?"
                db.execute(query, params)
                db.commit()
            
            return self.get_user_profile(user_id)
    
    # ==================== 学习计划 ====================
    
    def create_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建学习计划"""
        with self._get_db() as db:
            db.execute(
                """INSERT INTO plans (id, user_id, title, original_input, target_node_id, progress, total, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan_data['id'],
                    plan_data['user_id'],
                    plan_data['title'],
                    plan_data.get('original_input'),
                    plan_data.get('target_node_id'),
                    plan_data.get('progress', 0),
                    plan_data.get('total', 0),
                    plan_data.get('status', 'active')
                )
            )
            db.commit()
            
            row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_data['id'],)).fetchone()
            return self._row_to_dict(row)
    
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取学习计划"""
        with self._get_db() as db:
            row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            return self._row_to_dict(row)
    
    def list_user_plans(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有计划"""
        with self._get_db() as db:
            rows = db.execute(
                "SELECT * FROM plans WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新学习计划"""
        with self._get_db() as db:
            update_fields = []
            params = []
            
            for key, value in updates.items():
                update_fields.append(f"{key} = ?")
                params.append(value)
            
            if update_fields:
                params.append(plan_id)
                query = f"UPDATE plans SET {', '.join(update_fields)} WHERE id = ?"
                db.execute(query, params)
                db.commit()
            
            return self.get_plan(plan_id)
    
    def delete_plan(self, plan_id: str):
        """删除学习计划"""
        with self._get_db() as db:
            db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
            db.commit()
    
    # ==================== 知识节点 ====================
    
    def create_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建知识节点"""
        with self._get_db() as db:
            db.execute(
                """INSERT INTO nodes 
                   (id, plan_id, name, status, x, y, why, what, mastery, prompt, resources, is_target, domain)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node_data['id'],
                    node_data['plan_id'],
                    node_data['name'],
                    node_data.get('status', 'unlearned'),
                    node_data.get('x', 0),
                    node_data.get('y', 0),
                    node_data.get('why'),
                    json.dumps(node_data.get('what', []), ensure_ascii=False),
                    json.dumps(node_data.get('mastery', []), ensure_ascii=False),
                    node_data.get('prompt'),
                    json.dumps(node_data.get('resources', []), ensure_ascii=False),
                    1 if node_data.get('is_target') else 0,
                    node_data.get('domain')
                )
            )
            db.commit()
            
            row = db.execute("SELECT * FROM nodes WHERE id = ?", (node_data['id'],)).fetchone()
            return self._row_to_dict(row)
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取知识节点"""
        with self._get_db() as db:
            row = db.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
            return self._row_to_dict(row)
    
    def list_plan_nodes(self, plan_id: str) -> List[Dict[str, Any]]:
        """获取计划的所有节点"""
        with self._get_db() as db:
            rows = db.execute(
                "SELECT * FROM nodes WHERE plan_id = ?", (plan_id,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新知识节点"""
        with self._get_db() as db:
            update_fields = []
            params = []
            
            for key, value in updates.items():
                if key in ['what', 'mastery', 'resources'] and isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
                update_fields.append(f"{key} = ?")
                params.append(value)
            
            if update_fields:
                params.append(node_id)
                query = f"UPDATE nodes SET {', '.join(update_fields)} WHERE id = ?"
                db.execute(query, params)
                db.commit()
            
            return self.get_node(node_id)
    
    # ==================== 边（依赖关系）====================
    
    def create_edge(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建边"""
        with self._get_db() as db:
            db.execute(
                "INSERT INTO edges (id, plan_id, from_node_id, to_node_id) VALUES (?, ?, ?, ?)",
                (edge_data['id'], edge_data['plan_id'], edge_data['from_node_id'], edge_data['to_node_id'])
            )
            db.commit()
            
            row = db.execute("SELECT * FROM edges WHERE id = ?", (edge_data['id'],)).fetchone()
            return self._row_to_dict(row)
    
    def list_plan_edges(self, plan_id: str) -> List[Dict[str, Any]]:
        """获取计划的所有边"""
        with self._get_db() as db:
            rows = db.execute(
                "SELECT * FROM edges WHERE plan_id = ?", (plan_id,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    # ==================== 笔记 ====================
    
    def create_note(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建笔记"""
        with self._get_db() as db:
            db.execute(
                "INSERT INTO notes (id, plan_id, node_id, user_id, content) VALUES (?, ?, ?, ?, ?)",
                (note_data['id'], note_data['plan_id'], note_data['node_id'], note_data['user_id'], note_data['content'])
            )
            db.commit()
            
            row = db.execute("SELECT * FROM notes WHERE id = ?", (note_data['id'],)).fetchone()
            return self._row_to_dict(row)
    
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """获取笔记"""
        with self._get_db() as db:
            row = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
            return self._row_to_dict(row)
    
    def list_notes(
        self, 
        user_id: str, 
        plan_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取笔记列表"""
        with self._get_db() as db:
            if plan_id:
                rows = db.execute(
                    "SELECT * FROM notes WHERE user_id = ? AND plan_id = ? ORDER BY created_at DESC",
                    (user_id, plan_id)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                ).fetchall()
            
            return [self._row_to_dict(row) for row in rows]
    
    def update_note(self, note_id: str, content: str) -> Dict[str, Any]:
        """更新笔记"""
        with self._get_db() as db:
            db.execute(
                "UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (content, note_id)
            )
            db.commit()
            
            return self.get_note(note_id)
    
    def delete_note(self, note_id: str):
        """删除笔记"""
        with self._get_db() as db:
            db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            db.commit()
