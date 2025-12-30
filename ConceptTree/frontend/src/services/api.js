/**
 * API 服务层 - 基于 LocalStorage 的模拟后端
 * 实现数据持久化，确保刷新页面后数据不丢失
 * 
 * 注意：正式开发时需将 storage.get/set 替换为真实的 fetch 请求
 */

import { createEmptyUserProfile } from '../types';

const STORAGE_KEYS = {
  PROFILE: 'concept_tree_profile',
  PLANS: 'concept_tree_plans',
  NOTES: 'concept_tree_notes',
  GRAPHS: 'concept_tree_graphs' // 存储 planId -> { nodes, edges } 的映射
};

// 本地存储帮助函数
const storage = {
  get: (key, defaultValue) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
      console.error(`Error reading ${key} from localStorage`, e);
      return defaultValue;
    }
  },
  set: (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error(`Error writing ${key} to localStorage`, e);
    }
  }
};

// 模拟延迟，让体验更真实
const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms));

// 用户画像 API
export const userProfileApi = {
  get: async () => {
    await delay();
    let profile = storage.get(STORAGE_KEYS.PROFILE, null);
    if (!profile) {
      profile = createEmptyUserProfile();
      storage.set(STORAGE_KEYS.PROFILE, profile);
    }
    return profile;
  },
  
  update: async (profile) => {
    await delay();
    storage.set(STORAGE_KEYS.PROFILE, profile);
    console.log('API: 更新用户画像', profile);
    return profile;
  }
};

// 学习计划 API
export const plansApi = {
  list: async () => {
    await delay();
    return storage.get(STORAGE_KEYS.PLANS, []);
  },
  
  create: async (input) => {
    await delay();
    const plans = storage.get(STORAGE_KEYS.PLANS, []);
    const newPlan = {
      id: `p${Date.now()}`,
      title: input.title || '新计划',
      progress: 0,
      total: input.nodes ? input.nodes.length : 0,
      status: 'active',
      lastAccess: '刚刚',
      createdAt: new Date().toISOString()
    };
    
    // 如果创建时包含了图谱数据，也保存图谱
    if (input.nodes || input.edges) {
      const graphs = storage.get(STORAGE_KEYS.GRAPHS, {});
      graphs[newPlan.id] = {
        nodes: input.nodes || [],
        edges: input.edges || []
      };
      storage.set(STORAGE_KEYS.GRAPHS, graphs);
    }

    const updatedPlans = [newPlan, ...plans];
    storage.set(STORAGE_KEYS.PLANS, updatedPlans);
    
    console.log('API: 创建学习计划', newPlan);
    return newPlan;
  },
  
  update: async (id, data) => {
    await delay();
    const plans = storage.get(STORAGE_KEYS.PLANS, []);
    const updatedPlans = plans.map(p => p.id === id ? { ...p, ...data } : p);
    storage.set(STORAGE_KEYS.PLANS, updatedPlans);
    console.log('API: 更新计划', id, data);
    return data;
  },
  
  archive: async (id) => {
    await delay();
    const plans = storage.get(STORAGE_KEYS.PLANS, []);
    const updatedPlans = plans.map(p => p.id === id ? { ...p, status: 'archived' } : p);
    storage.set(STORAGE_KEYS.PLANS, updatedPlans);
    return { id, status: 'archived' };
  },
  
  restore: async (id) => {
    await delay();
    const plans = storage.get(STORAGE_KEYS.PLANS, []);
    const updatedPlans = plans.map(p => p.id === id ? { ...p, status: 'active' } : p);
    storage.set(STORAGE_KEYS.PLANS, updatedPlans);
    return { id, status: 'active' };
  },
  
  delete: async (id) => {
    await delay();
    // 删除计划
    const plans = storage.get(STORAGE_KEYS.PLANS, []);
    const updatedPlans = plans.filter(p => p.id !== id);
    storage.set(STORAGE_KEYS.PLANS, updatedPlans);
    
    // 删除关联的图谱数据
    const graphs = storage.get(STORAGE_KEYS.GRAPHS, {});
    delete graphs[id];
    storage.set(STORAGE_KEYS.GRAPHS, graphs);
    
    // 删除关联的笔记 (可选，取决于是否需要彻底清理)
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const updatedNotes = notes.filter(n => n.planId !== id);
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);

    return { success: true };
  }
};

// 图谱 API
export const graphApi = {
  generate: async (input, userProfile) => {
    await delay(1500); // 生成图谱通常较慢
    console.log('API: 生成图谱', { input, userProfile });
    
    // Mock生成逻辑 - 字段与后端文档保持一致
    const mockNodes = [
      { 
        id: 'n1', 
        name: input,
        status: 'unlearned',
        x: 0, 
        y: -100,
        why: '这是你的学习目标。',
        what: ['核心概念理解', '实际应用场景'],
        mastery: ['能够清晰解释核心概念', '能够独立完成基础应用'],
        prompt: `请帮我讲解${input}，我的背景是：${userProfile?.abilities?.join('、') || '无特殊背景'}。请用简单的例子说明。`,
        resources: [],
        isTarget: true,
        domain: '通用'
      },
      { 
        id: 'n2', 
        name: '基础概念',
        status: 'unlearned',
        x: -150, 
        y: 100,
        why: `理解${input}的前置知识，为后续学习打基础。`,
        what: ['基本定义', '核心术语'],
        mastery: ['能够准确描述基本定义'],
        prompt: '请帮我讲解相关的基础概念...',
        resources: [],
        isTarget: false,
        domain: '基础'
      },
      { 
        id: 'n3', 
        name: '核心原理',
        status: 'unlearned',
        x: 0, 
        y: 100,
        why: '掌握核心原理是深入理解的关键。',
        what: ['工作原理', '内部机制'],
        mastery: ['能够解释工作原理'],
        prompt: '请帮我讲解核心原理...',
        resources: [],
        isTarget: false,
        domain: '原理'
      },
      { 
        id: 'n4', 
        name: '实践应用',
        status: 'unlearned',
        x: 150, 
        y: 100,
        why: '将理论知识应用到实际场景。',
        what: ['应用场景', '实践技巧'],
        mastery: ['能够在实际场景中应用'],
        prompt: '请帮我讲解实践应用...',
        resources: [],
        isTarget: false,
        domain: '应用'
      },
    ];
    
    const mockEdges = [
      { from: 'n2', to: 'n1' },
      { from: 'n3', to: 'n1' },
      { from: 'n4', to: 'n1' },
    ];

    return {
      interpretation: input,
      nodes: mockNodes,
      edges: mockEdges,
      targetNodeId: 'n1'
    };
  },
  
  get: async (planId) => {
    await delay();
    const graphs = storage.get(STORAGE_KEYS.GRAPHS, {});
    return graphs[planId] || { nodes: [], edges: [] };
  },
  
  updateNodeStatus: async (planId, nodeId, status) => {
    await delay();
    const graphs = storage.get(STORAGE_KEYS.GRAPHS, {});
    if (graphs[planId]) {
      const node = graphs[planId].nodes.find(n => n.id === nodeId);
      if (node) {
        node.status = status;
        storage.set(STORAGE_KEYS.GRAPHS, graphs);
        
        // 更新计划进度
        // progress = learned 节点数, total = 非 skipped 节点数
        const plans = storage.get(STORAGE_KEYS.PLANS, []);
        const plan = plans.find(p => p.id === planId);
        if (plan) {
           const learned = graphs[planId].nodes.filter(n => n.status === 'learned').length;
           const total = graphs[planId].nodes.filter(n => n.status !== 'skipped').length;
           plan.progress = learned;
           plan.total = total;
           storage.set(STORAGE_KEYS.PLANS, plans);
        }
        
        // 如果标记为已学习，更新用户画像的 masteredKnowledge
        if (status === 'learned' && node.name) {
          const profile = storage.get(STORAGE_KEYS.PROFILE, {});
          if (!profile.masteredKnowledge) {
            profile.masteredKnowledge = [];
          }
          if (!profile.masteredKnowledge.includes(node.name)) {
            profile.masteredKnowledge.push(node.name);
            storage.set(STORAGE_KEYS.PROFILE, profile);
          }
        }
      }
    }
    return { nodeId, status };
  },
  
  updateNodePosition: async (planId, nodeId, x, y) => {
    // 拖拽频繁触发，不加 delay
    const graphs = storage.get(STORAGE_KEYS.GRAPHS, {});
    if (graphs[planId]) {
      const node = graphs[planId].nodes.find(n => n.id === nodeId);
      if (node) {
        node.x = x;
        node.y = y;
        storage.set(STORAGE_KEYS.GRAPHS, graphs);
      }
    }
    return { nodeId, x, y };
  }
};

// 笔记 API
export const notesApi = {
  list: async (planId = null) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    if (planId) {
      return notes.filter(n => n.planId === planId);
    }
    return notes;
  },
  
  create: async (planId, nodeId, content) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const newNote = {
      id: `n${Date.now()}`,
      planId,
      nodeId,
      content,
      date: new Date().toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }),
      createdAt: new Date().toISOString()
    };
    
    const updatedNotes = [newNote, ...notes];
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);
    
    console.log('API: 创建笔记', newNote);
    return newNote;
  },
  
  update: async (noteId, content) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const updatedNotes = notes.map(n => n.id === noteId ? { ...n, content } : n);
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);
    return { id: noteId, content };
  },
  
  delete: async (noteId) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const updatedNotes = notes.filter(n => n.id !== noteId);
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);
    return { success: true };
  }
};

// AI 分析 API (无状态，无需持久化)
export const aiApi = {
  parseGoal: async (input, userProfile) => {
    await delay(1000);
    console.log('API: 解析学习目标', { input, userProfile });
    
    // 构建 backgroundSummary
    const backgroundSummary = [];
    
    // 从用户画像中提取相关能力
    if (userProfile?.abilities?.length > 0) {
      userProfile.abilities.slice(0, 2).forEach(ability => {
        backgroundSummary.push({
          text: ability,
          source: 'profile',
          isStrength: true
        });
      });
    }
    
    // 从输入中提取背景信息（简单模拟）
    if (input.includes('不好') || input.includes('薄弱') || input.includes('不会')) {
      backgroundSummary.push({
        text: '相关基础薄弱',
        source: 'input',
        isStrength: false
      });
    }
    if (input.includes('基础') || input.includes('会') || input.includes('熟悉')) {
      backgroundSummary.push({
        text: '有一定基础',
        source: 'input',
        isStrength: true
      });
    }
    
    // 判断是否需要拆分（简单模拟：目标太宽泛时建议拆分）
    const shouldSplit = input.length < 10 && !input.includes('理解') && !input.includes('学会');
    
    return {
      interpretation: input,
      backgroundSummary,
      suggestedNodeCount: shouldSplit ? 15 : 5,
      shouldSplit,
      splitSuggestions: shouldSplit ? [
        { title: `${input} - 基础入门`, description: '从基础概念开始', estimatedNodes: 4 },
        { title: `${input} - 核心原理`, description: '深入理解原理', estimatedNodes: 5 },
        { title: `${input} - 实践应用`, description: '动手实践', estimatedNodes: 6 }
      ] : null
    };
  },
  
  recommendNext: async (planId) => {
    await delay(500);
    // 简单模拟：返回第一个未学习的节点
    const graphs = storage.get(STORAGE_KEYS.GRAPHS, {});
    const graph = graphs[planId];
    if (!graph) return { recommendedNodeId: null, reason: '图谱不存在' };
    
    // 找到所有前置都完成的未学习节点
    const unlearned = graph.nodes.filter(n => n.status === 'unlearned');
    if (unlearned.length === 0) {
      return { recommendedNodeId: null, reason: '恭喜！你已完成所有知识点的学习', isComplete: true };
    }
    
    // 简单返回第一个未学习的节点
    const recommended = unlearned[0];
    return {
      recommendedNodeId: recommended.id,
      nodeName: recommended.name,
      reason: `${recommended.name}是当前推荐的下一步学习内容`
    };
  }
};
