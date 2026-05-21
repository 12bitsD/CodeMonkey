# ConceptTree 上线标准与全方位检测报告

- 生成时间：2026-05-17 00:00 +08:00
- 工作区：`C:\Users\Victor\Desktop\CodeMonkey666\CodeMonkey\ConceptTree`
- 检测范围：核心功能、稳定性、Supabase 交互、构建、静态质量、安全基础、观测能力、E2E 环境
- 总体结论：**暂不建议直接上线；核心功能和稳定性门禁通过，但依赖安全与浏览器 E2E 门禁仍未满足。**

## 参考标准

本次验收参考当前主流上线网站/应用的公开标准：

1. **用户体验性能：Google Core Web Vitals**
   - LCP：75 分位应不超过 2.5s。
   - INP：75 分位应不超过 200ms。
   - CLS：75 分位应不超过 0.1。
   - 来源：https://web.dev/articles/vitals

2. **可访问性：W3C WCAG 2.2**
   - 目标采用 WCAG 2.2 AA 作为上线最低标准。
   - 来源：https://www.w3.org/TR/WCAG22/

3. **应用安全：OWASP ASVS / OWASP Secure Headers**
   - ASVS 用于定义 Web 应用安全控制测试基线。
   - Secure Headers 用于校验 CSP、X-Frame-Options、X-Content-Type-Options、Referrer-Policy 等响应头。
   - 来源：https://owasp.org/www-project-application-security-verification-standard/
   - 来源：https://owasp.org/www-project-secure-headers/

4. **可靠性：Google SRE SLI/SLO 方法**
   - 用户面系统应关注 availability、latency、error rate、throughput。
   - 使用可量化 SLI/SLO 和错误预算来判断发布风险。
   - 来源：https://sre.google/sre-book/service-level-objectives/

## 本项目上线验收标准

### P0 必须通过

- 默认稳定性门禁通过。
- Supabase smoke 通过，覆盖真实数据库读写、幂等、防重复、推荐 fallback、计划管理。
- 生产构建通过。
- 静态 lint 通过。
- 核心后端健康检查、安全响应头、错误结构化、metrics 通过。
- 不存在用户请求路径 runtime DDL。
- 不存在 high/critical 级依赖漏洞。

### P1 上线前必须补齐

- Playwright 浏览器 E2E 至少通过核心主流程。
- WCAG 2.2 AA 自动化扫描接入。
- Core Web Vitals / Lighthouse lab 检测接入。
- 高风险依赖升级后回归测试。

## 检测结果汇总

| 项目 | 标准 | 结果 | 说明 |
|---|---|---:|---|
| 默认稳定性门禁 | 必须通过 | PASS | 前端关键单测、后端 no-db 稳定性、syntax smoke、生产构建全部通过 |
| Supabase DB smoke | 必须通过 | PASS | 真实 Supabase smoke 第一次通过，用时约 62s |
| 前端 lint | 必须通过 | PASS | 已修复 `vite.config.js` 未使用参数 |
| 后端专项稳定性 | 必须通过 | PASS | 23 个稳定性/幂等/日期/LLM 快失败用例通过 |
| 安全响应头 | 必须通过 | PASS | CSP、X-Frame-Options、X-Content-Type-Options、Referrer-Policy 已覆盖 |
| 运行路径 DDL | 必须不存在 | PASS | `rg "ALTER TABLE" backend\routers backend\services` 无结果 |
| 生产构建产物 | 必须可构建 | PASS | JS 约 299KB，CSS 约 52KB |
| Playwright E2E | 上线前必须通过 | BLOCKED | 本机缺少 Playwright Chromium，浏览器运行时下载被网络中断 |
| 依赖安全审计 | high/critical 必须为 0 | FAIL | `npm audit` 发现 5 个 high、4 个 moderate |
| Core Web Vitals | LCP/INP/CLS 达标 | NOT VERIFIED | 缺浏览器运行时，无法跑 Lighthouse/Playwright lab |
| WCAG 2.2 AA | 自动化扫描通过 | NOT VERIFIED | 当前未接 axe/playwright 可访问性扫描 |

## 执行命令与结果

### 默认稳定性门禁

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1
```

结果：PASS

覆盖：
- 前端关键单测：笔记保存兜底、plan/graph cache、API recoverable 错误、今日推荐缓存、AI SSE signal、提醒、graph utilities、chat panel、resource search、note formatting。
- 后端 no-db 稳定性：LLM fast fail、重试、节点日期校验、note node id 兼容、幂等 helper、chat stream fallback、DB timeout 和 recoverable error。
- backend syntax smoke。
- frontend production build。

### Supabase smoke

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -SkipBuild -IncludeDbIntegration
```

结果：PASS

覆盖：
- 手动/AI 笔记保存幂等。
- 节点状态重复点击不会重复写 learning session。
- AI 推荐失败后本地 fallback。
- 计划管理字段真实数据库更新。

### 静态质量

```powershell
npm run lint
```

结果：PASS

处理记录：
- 修复 `frontend/vite.config.js` 中 `proxyRes, req` 的未使用参数，改为只接收 `proxyRes`。

### 安全依赖审计

```powershell
npm audit --audit-level=high --json
```

结果：FAIL

检测到：
- high：5
- moderate：4
- critical：0

主要风险：
- `vite`：dev server/path traversal/arbitrary file read 相关告警。
- `rollup`：path traversal/arbitrary file write 相关告警。
- `flatted`：DoS / prototype pollution。
- `minimatch`、`picomatch`：ReDoS。
- `postcss`：CSS stringify XSS。

建议：
- 建立独立依赖升级分支。
- 优先升级 Vite、Vitest、Rollup、PostCSS、picomatch/minimatch 链。
- 升级后运行默认稳定性门禁、Supabase smoke、构建、E2E。

### 浏览器 E2E

```powershell
npm run test:e2e -- --reporter=list
```

结果：BLOCKED

阻塞原因：
- Playwright Chromium 缺失：
  `Executable doesn't exist at ... chromium_headless_shell-1208 ...`
- 执行 `npx playwright install chromium` 时网络 TLS 连接被中断，浏览器无法下载。

这不是业务代码失败，但属于上线验收环境未满足。

## 核心功能覆盖面

已通过自动化覆盖：

- 首页目标解析失败恢复。
- 计划列表缓存兜底。
- 图谱缓存兜底。
- 今日推荐缓存。
- AI 请求取消/去重 registry。
- AI SSE explain/chat 基础稳定性。
- 节点截止日期校验。
- 节点状态保存失败 rollback。
- 笔记保存失败不清空页面状态。
- Supabase 短超时、结构化错误码、连接池异常处理。
- 幂等 key：笔记重复保存、节点状态重复点击。
- `/health`、`/health/db`、`/health/metrics`。
- 安全响应头。

未完成自动化覆盖：

- 真实浏览器主流程。
- 真实用户交互下连续点击、刷新中断、节点切换 E2E。
- 移动端响应式布局截图验收。
- WCAG 自动化扫描。
- Lighthouse/Core Web Vitals lab 检测。

## 检测出的主要问题

### 1. 依赖安全未达上线标准

`npm audit` 存在 high 级漏洞。即使部分漏洞主要影响 dev server，也不建议在上线报告里忽略，因为当前依赖链包含 Vite/Rollup/PostCSS 等构建关键组件。

优先级：P0

建议修复：
- 升级 Vite/Vitest 到安全版本。
- 重新生成 lockfile。
- 跑完整稳定性门禁。
- 再跑一次 `npm audit --audit-level=high`，要求 high/critical 为 0。

### 2. Playwright E2E 环境不可用

浏览器运行时缺失且下载失败，导致无法验证真实浏览器核心主流程。

优先级：P0

建议修复：
- 在可访问 Playwright CDN 的网络环境执行：
  `npx playwright install chromium`
- 或配置内部镜像：
  `PLAYWRIGHT_DOWNLOAD_HOST`
- 将 `npm run test:e2e` 接入发布前 CI。

### 3. 性能和可访问性缺少自动化门禁

当前生产构建通过，但缺少 Lighthouse/Core Web Vitals 和 WCAG 自动化证据。

优先级：P1

建议修复：
- 接入 Lighthouse CI 或 Playwright + Lighthouse。
- 接入 `@axe-core/playwright`。
- 至少覆盖首页、图谱页、我的学习页。

## 上线建议

当前状态建议判定为：

**Beta / 内测可继续；正式上线暂缓。**

原因：
- 核心功能稳定性：通过。
- Supabase 交互稳定性：通过 smoke。
- 后端错误隔离和观测：通过。
- 静态质量：通过。
- 依赖安全：未通过。
- 浏览器 E2E：环境阻塞，未通过。
- Web Vitals / WCAG：未验证。

## 下一步修复清单

1. 修复 `npm audit` high 漏洞。
2. 安装/配置 Playwright Chromium，跑通 `npm run test:e2e`。
3. 新增 `@axe-core/playwright` 可访问性 smoke。
4. 新增 Lighthouse CI，至少记录 LCP/CLS/TBT，线上再接真实 INP。
5. 将完整 release gate 固化为：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -IncludeDbIntegration
npm run lint
npm audit --audit-level=high
npm run test:e2e
```

