# AI服务Mermaid图解

> **一句话总结**：AI服务把用户模糊的学习意图转化为结构化知识图谱，核心流程是意图理解→知识拆解→图谱生成。

---

## 图1：宏观数据流（L1）

```mermaid
flowchart LR
    User["用户输入"] -->|"我想学反向传播"| Parse["parse-goal
意图理解"]
    Parse -->|目标+背景| Generate["generate-graph
知识拆解"]
    Generate -->|节点+依赖| Graph["知识图谱"]
    
    subgraph AI_Loop["学习过程中"]
        Graph -->|当前状态| Recommend["recommend-next
学习调度"]
        Recommend -->|推荐节点| User_Action["用户学习"]
        User_Action -->|更新状态| Graph
    end
    
    User -->|调整目标| Clarify["clarify-goal
动态调整"]
    Clarify -->|变更方案| Graph
```

### 说人话
用户说一句话 → AI理解意图 → 拆解成知识图谱 → 学习过程中AI推荐下一步 → 目标变了AI帮忙调整。

---

## 图2：意图理解流程（L2）

```mermaid
flowchart TB
    Input["用户输入
'我想学反向传播，有Python基础但数学不好'"] --> Extract["信息提取"]
    
    subgraph Extract["信息提取"]
        E1["目标：理解反向传播"] 
        E2["优势：Python基础"]
        E3["弱项：数学薄弱"]
    end
    
    Extract --> Judge{"目标判断"}
    
    Judge -->|节点数<12| Normal["正常目标"]
    Judge -->|节点数>12| Split["建议拆分"]
    
    Normal --> Output1["返回：interpretation + backgroundSummary"]
    Split --> Output2["返回：splitSuggestions（3个子目标）"]
```

### 说人话
从用户输入里提取：想学什么、有什么基础、哪里薄弱。如果目标太大（超过12个节点），建议拆成子目标。

---

## 图3：知识拆解流程（L2）

```mermaid
flowchart TB
    Goal["学习目标"] --> Deps["依赖分析"]
    
    subgraph Deps["依赖分析"]
        D1["目标：反向传播"] 
        D2["前置：链式法则"]
        D3["前置：梯度计算"]
        D4["前置：矩阵乘法"]
    end
    
    Deps --> Build["构建图谱"]
    
    subgraph Build["构建图谱"]
        B1["节点1：矩阵乘法
why/what/mastery/prompt/resources"]
        B2["节点2：梯度计算
why/what/mastery/prompt/resources"]
        B3["节点3：链式法则
why/what/mastery/prompt/resources"]
        B4["节点4：反向传播
isTarget=true"]
    end
    
    Build --> Edges["建立依赖边"]
    Edges -->|n1→n2→n4
n1→n3→n4| Output["返回：nodes + edges"]
```

### 说人话
分析学这个目标需要先学什么，每个知识点生成：为什么学、学什么、怎么算学会、问AI的Prompt、推荐资源。

---

## 图4：学习调度流程（L2）

```mermaid
flowchart TB
    subgraph Input["输入"]
        I1["图谱状态
哪些已学/未学"]
        I2["用户画像
背景/能力"]
        I3["学习历史
上次学了什么"]
    end
    
    Input --> Filter["筛选可学节点
前置都完成了"]
    Filter --> Path["关键路径分析
最短到达目标"]
    Path --> Rank["难度匹配
根据用户背景"]
    Rank --> Output["推荐节点 + 理由"]
```

### 说人话
推荐下一步时考虑：哪些节点可以学了（前置都完成了）、哪条路径最快到达目标、难度适不适合用户当前水平。

---

## 图5：工程化架构（L2）

```mermaid
flowchart TB
    subgraph API["API层"]
        A1["parse-goal"]
        A2["generate-graph"]
        A3["recommend-next"]
    end
    
    subgraph Service["服务层"]
        S1["意图理解服务"]
        S2["知识拆解服务"]
        S3["学习调度服务"]
    end
    
    subgraph LLM["LLM层"]
        L1["OpenAI Adapter"]
        L2["DeepSeek Adapter"]
        L3["Claude Adapter"]
    end
    
    subgraph Infra["基础设施"]
        F1["Prompt管理
版本化"]
        F2["语义缓存
降成本"]
        F3["降级策略
保可用"]
    end
    
    API --> Service
    Service --> LLM
    Service --> Infra
```

### 说人话
API调用服务，服务调用LLM，基础设施层管Prompt版本、缓存、降级。

---

## 图6：降级策略（L3）

```mermaid
flowchart TD
    Request["用户请求"] --> Primary["主LLM
OpenAI"]
    
    Primary -->|超时>10s| Fallback["备用LLM
DeepSeek"]
    Primary -->|成功| Return["返回结果"]
    
    Fallback -->|失败| Simple["简化规则引擎
关键词匹配"]
    Fallback -->|成功| Return
    
    Simple -->|失败| Error["返回友好错误
请用户重试"]
    Simple -->|成功| Return
```

### 说人话
主LLM超时→切备用LLM→备用也挂了→用简单规则兜底→全挂了→告诉用户稍后再试。

---

## 图7：调用链路时序（L3）

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant R as 后端路由
    participant S as AI服务
    participant C as LLM Client
    participant L as LLM API

    U->>F: 输入学习目标
    F->>R: POST /api/ai/parse-goal
    R->>S: parse_goal_service()
    S->>C: chat(prompt)
    C->>L: HTTP请求
    L-->>C: JSON响应
    C-->>S: 解析结果
    S-->>R: 结构化数据
    R-->>F: {success, data}
    F-->>U: 显示确认弹窗
```

### 说人话
用户输入→前端调后端→后端调AI服务→AI服务调LLM Client→Client调OpenAI/DeepSeek→层层返回→前端显示结果。

---

## 关键设计对照表

| 设计点 | 目的 | 实现方式 |
|--------|------|---------|
| **多LLM支持** | 可切换、可降级 | Adapter模式 |
| **Prompt版本化** | 快速迭代A/B测试 | 文件管理+Jinja2 |
| **语义缓存** | 降成本 | 向量相似度匹配 |
| **JSON Schema** | 输出可预期 | 强制校验LLM输出 |
| **3级降级** | 保可用 | 主LLM→备用→规则→错误 |

---

