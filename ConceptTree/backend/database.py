import sqlite3
from contextlib import contextmanager
from typing import Generator

DATABASE_PATH = "./database.sqlite"


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                last_access_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

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

        seed_data(db)
        db.commit()


def seed_data(db: sqlite3.Connection):
    row = db.execute("SELECT count(*) as count FROM plans").fetchone()
    if row["count"] > 0:
        return

    user_id = "u_test"
    db.execute(
        "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
        (user_id, "test@example.com", "hashed_pw")
    )

    plan_id = "p_demo"
    db.execute(
        "INSERT INTO plans (id, user_id, title, progress, total, status) VALUES (?, ?, ?, ?, ?, ?)",
        (plan_id, user_id, "理解反向传播的数学原理", 0, 4, "active")
    )

    nodes = [
        {
            "id": "n1",
            "name": "矩阵乘法",
            "status": "unlearned",
            "x": -150,
            "y": 100,
            "why": "神经网络的前向传播本质就是 y = Wx + b...",
            "what": '["矩阵乘法的定义", "维度匹配规则"]',
            "mastery": '["手算2x3矩阵相乘"]',
            "prompt": "请帮我讲解矩阵乘法...",
            "is_target": 0
        },
        {
            "id": "n2",
            "name": "导数与偏导数",
            "status": "unlearned",
            "x": -150,
            "y": -100,
            "why": "反向传播的核心是链式法则，而链式法则的基础是偏导数。",
            "what": '["导数的几何意义", "偏导数计算"]',
            "mastery": '["计算简单多元函数的偏导"]',
            "prompt": "请讲解偏导数...",
            "is_target": 0
        },
        {
            "id": "n3",
            "name": "链式法则",
            "status": "unlearned",
            "x": 0,
            "y": 0,
            "why": "用于计算复合函数的导数，是误差反向传播的数学基础。",
            "what": '["链式法则公式", "计算图理解"]',
            "mastery": '["使用链式法则求导"]',
            "prompt": "请讲解链式法则...",
            "is_target": 0
        },
        {
            "id": "n4",
            "name": "反向传播",
            "status": "unlearned",
            "x": 150,
            "y": 0,
            "why": "这是你的学习目标。",
            "what": '["误差反向传递", "参数更新"]',
            "mastery": '["推导全连接层的梯度"]',
            "prompt": "请讲解反向传播...",
            "is_target": 1
        }
    ]

    for n in nodes:
        db.execute(
            """INSERT INTO nodes (id, plan_id, name, status, x, y, why, what, mastery, prompt, is_target)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (n["id"], plan_id, n["name"], n["status"], n["x"], n["y"], n["why"],
             n["what"], n["mastery"], n["prompt"], n["is_target"])
        )

    edges = [
        {"id": "e1", "from": "n1", "to": "n3"},
        {"id": "e2", "from": "n2", "to": "n3"},
        {"id": "e3", "from": "n3", "to": "n4"}
    ]

    for e in edges:
        db.execute(
            "INSERT INTO edges (id, plan_id, from_node_id, to_node_id) VALUES (?, ?, ?, ?)",
            (e["id"], plan_id, e["from"], e["to"])
        )
