"""数据库适配器工厂

根据配置自动选择和创建数据库适配器实例
"""

from typing import Optional
from .base import DatabaseAdapter
from .sqlite import SQLiteAdapter
# from .supabase import SupabaseAdapter  # 未来启用


class DatabaseFactory:
    """数据库适配器工厂"""
    
    _instance: Optional[DatabaseAdapter] = None
    
    @classmethod
    def create_adapter(
        cls, 
        db_type: str = "sqlite",
        **config
    ) -> DatabaseAdapter:
        """创建数据库适配器实例
        
        Args:
            db_type: 数据库类型 ("sqlite" | "supabase")
            **config: 数据库配置参数
            
        Returns:
            DatabaseAdapter 实例
            
        Raises:
            ValueError: 不支持的数据库类型
        """
        if db_type == "sqlite":
            database_path = config.get('database_path', './database.sqlite')
            return SQLiteAdapter(database_path)
        
        elif db_type == "supabase":
            # TODO: 启用 Supabase 适配器
            # url = config.get('url')
            # key = config.get('key')
            # if not url or not key:
            #     raise ValueError("Supabase requires 'url' and 'key' in config")
            # return SupabaseAdapter(url, key)
            raise NotImplementedError(
                "Supabase adapter is not yet implemented. "
                "Please see adapters/supabase.py for template."
            )
        
        else:
            raise ValueError(
                f"Unsupported database type: {db_type}. "
                f"Supported types: sqlite, supabase"
            )
    
    @classmethod
    def get_adapter(cls, db_type: str = "sqlite", **config) -> DatabaseAdapter:
        """获取或创建数据库适配器单例
        
        Args:
            db_type: 数据库类型
            **config: 数据库配置参数
            
        Returns:
            DatabaseAdapter 实例（单例）
        """
        if cls._instance is None:
            cls._instance = cls.create_adapter(db_type, **config)
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置适配器实例（用于测试）"""
        cls._instance = None


def get_database_adapter(db_type: str = "sqlite", **config) -> DatabaseAdapter:
    """便捷函数：获取数据库适配器
    
    这是推荐的获取适配器的方式
    
    Usage:
        from adapters import get_database_adapter
        
        # 使用 SQLite（默认）
        db = get_database_adapter()
        
        # 使用 Supabase（未来）
        db = get_database_adapter(
            db_type="supabase",
            url="https://xxx.supabase.co",
            key="your-key"
        )
    
    Args:
        db_type: 数据库类型
        **config: 数据库配置参数
        
    Returns:
        DatabaseAdapter 实例
    """
    return DatabaseFactory.get_adapter(db_type, **config)
