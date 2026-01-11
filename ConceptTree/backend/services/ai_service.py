"""AI服务实现 - Mock版本"""
import json
from typing import List, Dict
from models import (
    BackgroundSummary, 
    SplitSuggestion, 
    NodeData, 
    Edge, 
    NodeStatus,
    Resource
)


def parse_goal_service(user_input: str, user_profile: dict) -> dict:
    """解析学习目标
    
    Args:
        user_input: 用户输入的学习目标
        user_profile: 用户画像数据
    
    Returns:
        解析结果，包含interpretation, backgroundSummary等
    """
    # Mock实现：简单的规则提取
    interpretation = user_input.strip()
    
    # 构建背景摘要
    background_summary = []
    
    # 从用户画像中提取相关能力（取前2个）
    if user_profile and user_profile.get("abilities"):
        for ability in user_profile["abilities"][:2]:
            background_summary.append(BackgroundSummary(
                text=ability,
                source="profile",
                isStrength=True
            ))
    
    # 从输入中提取背景信息
    if "不好" in user_input or "薄弱" in user_input or "不会" in user_input:
        # 提取弱项
        if "数学" in user_input:
            background_summary.append(BackgroundSummary(
                text="数学基础薄弱",
                source="input",
                isStrength=False
            ))
        elif "编程" in user_input:
            background_summary.append(BackgroundSummary(
                text="编程基础薄弱",
                source="input",
                isStrength=False
            ))
    
    if "基础" in user_input or "会" in user_input or "熟悉" in user_input:
        # 提取优势
        if "Python" in user_input:
            background_summary.append(BackgroundSummary(
                text="有Python基础",
                source="input",
                isStrength=True
            ))
    
    # 判断是否需要拆分（简单规则：目标太宽泛）
    should_split = False
    split_suggestions = None
    
    # 如果输入很短且很宽泛，建议拆分
    broad_keywords = ["深度学习", "机器学习", "人工智能", "数据科学", "算法", "编程"]
    if any(keyword in user_input for keyword in broad_keywords) and len(user_input) < 15:
        should_split = True
        suggested_node_count = 20
        
        # 生成拆分建议
        topic = next((kw for kw in broad_keywords if kw in user_input), "该主题")
        split_suggestions = [
            SplitSuggestion(
                title=f"{topic} - 基础入门",
                description="从基础概念开始，建立初步认知",
                estimatedNodes=5
            ),
            SplitSuggestion(
                title=f"{topic} - 核心原理",
                description="深入理解核心算法和原理",
                estimatedNodes=7
            ),
            SplitSuggestion(
                title=f"{topic} - 实践应用",
                description="动手实践，掌握应用技巧",
                estimatedNodes=6
            )
        ]
    else:
        suggested_node_count = 5
    
    return {
        "interpretation": interpretation,
        "backgroundSummary": [bg.model_dump() for bg in background_summary],
        "suggestedNodeCount": suggested_node_count,
        "shouldSplit": should_split,
        "splitSuggestions": [s.model_dump() for s in split_suggestions] if split_suggestions else None
    }


def generate_graph_service(user_input: str, interpretation: str, user_profile: dict) -> dict:
    """生成知识图谱
    
    Args:
        user_input: 原始输入
        interpretation: AI解释的学习目标
        user_profile: 用户画像
    
    Returns:
        图谱数据，包含nodes, edges, targetNodeId
    """
    # Mock实现：生成简单的图谱结构
    
    # 目标节点
    target_node = NodeData(
        id="n1",
        name=interpretation,
        status=NodeStatus.UNLEARNED,
        x=0,
        y=-100,
        why="这是你的学习目标。",
        what=["核心概念理解", "实际应用场景", "常见问题解决"],
        mastery=["能够清晰解释核心概念", "能够独立完成基础应用"],
        prompt=f"请帮我讲解{interpretation}，我的背景是：{', '.join(user_profile.get('abilities', [])) if user_profile else '无特殊背景'}。请用简单的例子说明。",
        resources=[],
        isTarget=True,
        domain="核心"
    )
    
    # 前置节点
    prerequisite_nodes = [
        NodeData(
            id="n2",
            name="基础概念",
            status=NodeStatus.UNLEARNED,
            x=-150,
            y=100,
            why=f"理解{interpretation}的前置知识，为后续学习打基础。",
            what=["基本定义", "核心术语", "基础原理"],
            mastery=["能够准确描述基本定义", "理解基础术语含义"],
            prompt="请帮我讲解相关的基础概念...",
            resources=[],
            isTarget=False,
            domain="基础"
        ),
        NodeData(
            id="n3",
            name="核心原理",
            status=NodeStatus.UNLEARNED,
            x=0,
            y=100,
            why="掌握核心原理是深入理解的关键。",
            what=["工作原理", "内部机制", "理论依据"],
            mastery=["能够解释工作原理", "理解内部机制"],
            prompt="请帮我讲解核心原理...",
            resources=[],
            isTarget=False,
            domain="原理"
        ),
        NodeData(
            id="n4",
            name="实践应用",
            status=NodeStatus.UNLEARNED,
            x=150,
            y=100,
            why="将理论知识应用到实际场景。",
            what=["应用场景", "实践技巧", "案例分析"],
            mastery=["能够在实际场景中应用", "完成基础项目"],
            prompt="请帮我讲解实践应用...",
            resources=[],
            isTarget=False,
            domain="应用"
        )
    ]
    
    # 检查用户已掌握的知识，自动标记为skipped
    mastered = user_profile.get("masteredKnowledge", []) if user_profile else []
    all_nodes = [target_node] + prerequisite_nodes
    
    for node in all_nodes:
        if node.name in mastered:
            node.status = NodeStatus.SKIPPED
    
    # 构建依赖边
    edges = [
        Edge(from_="n2", to="n1"),
        Edge(from_="n3", to="n1"),
        Edge(from_="n4", to="n1"),
    ]
    
    return {
        "interpretation": interpretation,
        "nodes": [node.model_dump() for node in all_nodes],
        "edges": [edge.model_dump(by_alias=True) for edge in edges],
        "targetNodeId": "n1"
    }
