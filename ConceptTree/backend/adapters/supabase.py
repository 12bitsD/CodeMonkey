"""Supabase 数据库适配器（模板）

未来集成 Supabase PostgreSQL 时的实现模板
"""

from typing import Optional, List, Dict, Any
from .base import DatabaseAdapter

# TODO: 安装 supabase 包
# pip install supabase

# TODO: 导入 supabase 客户端
# from supabase import create_client, Client


class SupabaseAdapter(DatabaseAdapter):
    """Supabase 数据库适配器
    
    注意：这是一个模板实现，需要安装 supabase 包后才能使用
    """
    
    def __init__(self, url: str = "", key: str = ""):
        """
        Args:
            url: Supabase 项目 URL
            key: Supabase API key (anon key or service role key)
        """
        self.url = url
        self.key = key
        self.client = None
        
        # TODO: 初始化 Supabase 客户端
        # self.client: Client = create_client(url, key)
    
    # ==================== 连接管理 ====================
    
    async def connect(self):
        """建立 Supabase 连接"""
        # TODO: 实现连接逻辑（如果需要）
        # Supabase 客户端在初始化时已经建立连接
        pass
    
    async def disconnect(self):
        """关闭 Supabase 连接"""
        # TODO: 实现断开逻辑（如果需要）
        pass
    
    def init_database(self, run_seed: bool = True):
        """初始化数据库表结构
        
        注意：Supabase 的表结构应该通过 Supabase Dashboard 或 SQL 编辑器创建
        """
        # TODO: 可选择通过 SQL 执行创建表
        # 或者在 Supabase Dashboard 中手动创建表
        raise NotImplementedError("Please create tables in Supabase Dashboard first")
    
    # ==================== 用户管理 ====================
    
    def create_user(self, user_id: str, email: str, password_hash: str) -> Dict[str, Any]:
        """创建用户
        
        注意：可以选择使用 Supabase Auth 或自定义用户表
        """
        # TODO: 实现创建用户
        # Option 1: 使用 Supabase Auth
        # response = self.client.auth.sign_up({
        #     "email": email,
        #     "password": password
        # })
        
        # Option 2: 插入自定义 users 表
        # response = self.client.table("users").insert({
        #     "id": user_id,
        #     "email": email,
        #     "password_hash": password_hash
        # }).execute()
        # return response.data[0]
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户"""
        # TODO: 实现查询用户
        # response = self.client.table("users")\
        #     .select("*")\
        #     .eq("email", email)\
        #     .execute()
        # 
        # if response.data:
        #     return response.data[0]
        # return None
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        # TODO: 实现查询用户
        # response = self.client.table("users")\
        #     .select("*")\
        #     .eq("id", user_id)\
        #     .execute()
        # 
        # if response.data:
        #     return response.data[0]
        # return None
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    # ==================== 用户画像 ====================
    
    def create_user_profile(
        self, 
        profile_id: str, 
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建用户画像"""
        # TODO: 实现创建画像
        # response = self.client.table("user_profiles").insert({
        #     "id": profile_id,
        #     "user_id": user_id,
        #     "occupation": kwargs.get('occupation'),
        #     "education": kwargs.get('education'),
        #     "programming_level": kwargs.get('programming_level', '入门'),
        #     "math_level": kwargs.get('math_level', '入门'),
        #     "abilities": [],
        #     "mastered_knowledge": []
        # }).execute()
        # return response.data[0]
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        # TODO: 实现查询画像
        # response = self.client.table("user_profiles")\
        #     .select("*")\
        #     .eq("user_id", user_id)\
        #     .execute()
        # 
        # if response.data:
        #     return response.data[0]
        # return None
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户画像"""
        # TODO: 实现更新画像
        # # 转换字段名（camelCase -> snake_case）
        # db_updates = {}
        # if 'programmingLevel' in updates:
        #     db_updates['programming_level'] = updates['programmingLevel']
        # if 'mathLevel' in updates:
        #     db_updates['math_level'] = updates['mathLevel']
        # # ... 其他字段
        # 
        # response = self.client.table("user_profiles")\
        #     .update(db_updates)\
        #     .eq("user_id", user_id)\
        #     .execute()
        # 
        # return response.data[0]
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    # ==================== 学习计划 ====================
    
    def create_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建学习计划"""
        # TODO: 实现创建计划
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取学习计划"""
        # TODO: 实现查询计划
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def list_user_plans(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有计划"""
        # TODO: 实现查询计划列表
        # response = self.client.table("plans")\
        #     .select("*")\
        #     .eq("user_id", user_id)\
        #     .order("created_at", desc=True)\
        #     .execute()
        # 
        # return response.data
        
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新学习计划"""
        # TODO: 实现更新计划
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def delete_plan(self, plan_id: str):
        """删除学习计划"""
        # TODO: 实现删除计划
        # self.client.table("plans").delete().eq("id", plan_id).execute()
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    # ==================== 其他方法 ====================
    # 节点、边、笔记等方法类似实现
    # 参考 SQLiteAdapter 的实现模式
    
    def create_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def list_plan_nodes(self, plan_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def create_edge(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def list_plan_edges(self, plan_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def create_note(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def list_notes(
        self, 
        user_id: str, 
        plan_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def update_note(self, note_id: str, content: str) -> Dict[str, Any]:
        raise NotImplementedError("Supabase adapter not implemented yet")
    
    def delete_note(self, note_id: str):
        raise NotImplementedError("Supabase adapter not implemented yet")


# ==================== Supabase 实时功能示例 ====================

class SupabaseRealtimeAdapter(SupabaseAdapter):
    """扩展 Supabase 适配器，支持实时功能
    
    Supabase 的一大优势是实时数据订阅
    """
    
    def subscribe_to_plan_updates(self, plan_id: str, callback):
        """订阅计划更新
        
        Args:
            plan_id: 计划ID
            callback: 回调函数，接收更新数据
        """
        # TODO: 实现实时订阅
        # self.client.table("plans")\
        #     .on("UPDATE", callback)\
        #     .eq("id", plan_id)\
        #     .subscribe()
        
        raise NotImplementedError("Supabase realtime not implemented yet")
    
    def subscribe_to_node_changes(self, plan_id: str, callback):
        """订阅节点变化
        
        支持多用户协作时的实时同步
        """
        # TODO: 实现实时订阅
        raise NotImplementedError("Supabase realtime not implemented yet")
