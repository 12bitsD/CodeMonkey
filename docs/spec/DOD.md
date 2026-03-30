# Definition of Done (完成标准)

## 功能开发

- [ ] **测试覆盖**: 新增功能有对应的单元测试
- [ ] **API 契约**: 请求/响应格式符合 `contract.md`
- [ ] **错误处理**: 错误码符合 `后端-通用规范.md` 规范
- [ ] **数据验证**: Pydantic validation 通过
- [ ] **边界 case**: 空值、越界、重复等已处理

## 代码质量

- [ ] **命名**: 函数/变量命名清晰，符合项目约定
- [ ] **注释**: 复杂逻辑有解释
- [ ] **无硬编码**: 配置在环境变量或 config
- [ ] **无裸 except**: 捕获具体异常

## 后端专属

- [ ] **数据库**: 使用 `?` 占位符 (非 `%s` 或 f-string)
- [ ] **认证**: 使用 `get_current_user_id` 而非硬编码 user_id
- [ ] **业务逻辑**: 路由函数仅做校验，业务逻辑在 `services/`
- [ ] **响应格式**: 统一 `{success, data/error}` 结构

## 前端专属

- [ ] **API 调用**: 统一经由 `services/api.js`
- [ ] **状态管理**: 业务数据在 AppContext，UI 状态用 useState
- [ ] **错误提示**: 使用 Toast 而非 alert/console.error
- [ ] **edges 映射**: 使用 `mapEdgesFromBackend/mapEdgesToBackend`

## 文档更新

- [ ] Epic spec 已更新 (如有必要)
- [ ] API 契约已更新 (如有必要)
- [ ] 类型定义已同步 (models.py)

## DoD 检查清单

完成任何功能后，逐项确认:

```
□ 测试通过 (pytest / vitest / playwright)
□ API 契约测试通过 (test_api_contract.py)
□ 代码符合编码约束 (CLAUDE.md)
□ 文档已更新
□ 无新增 lint 错误
□ 功能可正常使用
```

## 提交前检查

```bash
# 后端
cd backend && python -m pytest -q

# 前端
cd frontend && npm run test:unit
npm run lint
```
