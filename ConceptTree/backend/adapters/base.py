"""数据库适配器抽象接口"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class DatabaseAdapter(ABC):
    """数据库适配器抽象基类
    
    定义所有数据库操作的接口，具体实现由子类提供
    """
    
    # ==================== 连接管理 ====================
    
    @abstractmethod
    async def connect(self):
        """建立数据库连接"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """关闭数据库连接"""
        pass
    
    @abstractmethod
    def init_database(self, run_seed: bool = True):
        """初始化数据库表结构"""
        pass
    
    # ==================== 用户管理 ====================
    
    @abstractmethod
    def create_user(self, user_id: str, email: str, password_hash: str) -> Dict[str, Any]:
        """创建用户
        
        Args:
            user_id: 用户ID
            email: 邮箱
            password_hash: 密码哈希
            
        Returns:
            用户数据字典
        """
        pass
    
    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            用户数据字典，不存在返回 None
        """
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户数据字典，不存在返回 None
        """
        pass
    
    # ==================== 用户画像 ====================
    
    @abstractmethod
    def create_user_profile(
        self, 
        profile_id: str, 
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建用户画像
        
        Args:
            profile_id: 画像ID
            user_id: 用户ID
            **kwargs: 其他画像字段
            
        Returns:
            画像数据字典
        """
        pass
    
    @abstractmethod
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            画像数据字典，不存在返回 None
        """
        pass
    
    @abstractmethod
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户画像
        
        Args:
            user_id: 用户ID
            updates: 更新的字段
            
        Returns:
            更新后的画像数据
        """
        pass
    
    # ==================== 学习计划 ====================
    
    @abstractmethod
    def create_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建学习计划"""
        pass
    
    @abstractmethod
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取学习计划"""
        pass
    
    @abstractmethod
    def list_user_plans(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有计划"""
        pass
    
    @abstractmethod
    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新学习计划"""
        pass
    
    @abstractmethod
    def delete_plan(self, plan_id: str):
        """删除学习计划"""
        pass
    
    # ==================== 知识节点 ====================
    
    @abstractmethod
    def create_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建知识节点"""
        pass
    
    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取知识节点"""
        pass
    
    @abstractmethod
    def list_plan_nodes(self, plan_id: str) -> List[Dict[str, Any]]:
        """获取计划的所有节点"""
        pass
    
    @abstractmethod
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新知识节点"""
        pass
    
    # ==================== 边（依赖关系）====================
    
    @abstractmethod
    def create_edge(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建边"""
        pass
    
    @abstractmethod
    def list_plan_edges(self, plan_id: str) -> List[Dict[str, Any]]:
        """获取计划的所有边"""
        pass
    
    # ==================== 笔记 ====================
    
    @abstractmethod
    def create_note(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建笔记"""
        pass
    
    @abstractmethod
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """获取笔记"""
        pass
    
    @abstractmethod
    def list_notes(
        self, 
        user_id: str, 
        plan_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取笔记列表"""
        pass
    
    @abstractmethod
    def update_note(self, note_id: str, content: str) -> Dict[str, Any]:
        """更新笔记"""
        pass
    
    @abstractmethod
    def delete_note(self, note_id: str):
        """删除笔记"""
        pass
