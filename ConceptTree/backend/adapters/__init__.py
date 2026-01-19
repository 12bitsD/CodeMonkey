"""数据库适配器包

支持多种数据库后端：
- SQLite (本地开发)
- Supabase (生产环境)
"""

from .base import DatabaseAdapter
from .sqlite import SQLiteAdapter
from .factory import get_database_adapter

__all__ = ['DatabaseAdapter', 'SQLiteAdapter', 'get_database_adapter']
