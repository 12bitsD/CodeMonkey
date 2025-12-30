/**
 * @typedef {Object} UserProfile
 * @property {string} occupation - 职业/身份
 * @property {string} education - 教育背景
 * @property {string} programmingLevel - 编程基础 (无基础/入门/熟练)
 * @property {string} mathLevel - 数学基础 (无基础/入门/熟练)
 * @property {string[]} abilities - 能力标签
 * @property {string[]} masteredKnowledge - 已掌握知识点
 */

/**
 * @typedef {Object} Note
 * @property {string} id
 * @property {string} planId
 * @property {string} nodeId
 * @property {string} content - Markdown 格式内容
 * @property {string} date
 */

/**
 * @typedef {Object} GraphNode
 * @property {string} id
 * @property {string} name
 * @property {'unlearned'|'learned'|'skipped'} status
 * @property {number} x - 画布 X 坐标
 * @property {number} y - 画布 Y 坐标
 * @property {string} why - 为什么学
 * @property {string[]} what - 学什么
 * @property {string[]} mastery - 掌握标准
 * @property {string} prompt - 学习 Prompt
 * @property {Resource[]} resources - 推荐资源
 * @property {boolean} [isTarget] - 是否为目标节点
 */

/**
 * @typedef {Object} Resource
 * @property {string} name
 * @property {string} [url]
 * @property {string} reason
 */

/**
 * @typedef {Object} GraphEdge
 * @property {string} from - 起点节点 ID
 * @property {string} to - 终点节点 ID
 */

/**
 * @typedef {Object} Plan
 * @property {string} id
 * @property {string} title
 * @property {number} progress - 已完成节点数
 * @property {number} total - 总节点数
 * @property {'active'|'archived'} status
 * @property {string} lastAccess
 */

export const createEmptyUserProfile = () => ({
  occupation: '',
  education: '',
  programmingLevel: '入门',
  mathLevel: '入门',
  abilities: [],
  masteredKnowledge: []
});

export const createEmptyNode = (id, name, x = 0, y = 0) => ({
  id,
  name,
  status: 'unlearned',
  x,
  y,
  why: '',
  what: [],
  mastery: [],
  prompt: '',
  resources: [],
  isTarget: false
});

export const createEmptyPlan = (id, title) => ({
  id,
  title,
  progress: 0,
  total: 0,
  status: 'active',
  lastAccess: '刚刚'
});
