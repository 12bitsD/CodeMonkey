/**
 * @typedef {Object} UserProfile
 * @property {string} occupation
 * @property {string} education
 * @property {string} programmingLevel
 * @property {string} mathLevel
 * @property {string[]} abilities
 * @property {string[]} masteredKnowledge
 */

/**
 * @typedef {Object} Note
 * @property {string} id
 * @property {string} planId
 * @property {string} nodeId
 * @property {string} content
 * @property {string} date
 */

/**
 * @typedef {Object} GraphNode
 * @property {string} id
 * @property {string} name
 * @property {'unlearned'|'learned'|'skipped'} status
 * @property {number} x
 * @property {number} y
 * @property {string} why
 * @property {string[]} what
 * @property {string[]} mastery
 * @property {string} prompt
 * @property {Resource[]} resources
 * @property {boolean} [isTarget]
 * @property {string | null} [targetEndDate]
 */

/**
 * @typedef {Object} Resource
 * @property {string} name
 * @property {string} [url]
 * @property {string} reason
 */

/**
 * @typedef {Object} GraphEdge
 * @property {string} from
 * @property {string} to
 */

/**
 * @typedef {Object} Plan
 * @property {string} id
 * @property {string} title
 * @property {number} progress
 * @property {number} total
 * @property {'active'|'paused'|'archived'} status
 * @property {string} lastAccess
 * @property {string | null} [createdAt]
 * @property {string | null} [startDate]
 * @property {string | null} [targetEndDate]
 * @property {string} [studyFrequency]
 * @property {number} [studyDaysPerWeek]
 * @property {boolean} [reminderEnabled]
 * @property {string} [reminderTime]
 * @property {string} [reminderTimezone]
 * @property {string | null} [archivedReason]
 */

export const createEmptyUserProfile = () => ({
  occupation: "",
  education: "",
  programmingLevel: "入门",
  mathLevel: "入门",
  abilities: [],
  masteredKnowledge: [],
});

export const createEmptyNode = (id, name, x = 0, y = 0) => ({
  id,
  name,
  status: "unlearned",
  x,
  y,
  why: "",
  what: [],
  mastery: [],
  prompt: "",
  resources: [],
  isTarget: false,
  targetEndDate: null,
});

export const createEmptyPlan = (id, title) => ({
  id,
  title,
  progress: 0,
  total: 0,
  status: "active",
  lastAccess: "刚刚",
  createdAt: null,
  startDate: null,
  targetEndDate: null,
  studyFrequency: "flexible",
  studyDaysPerWeek: 3,
  reminderEnabled: false,
  reminderTime: "",
  reminderTimezone: "",
  archivedReason: null,
});
