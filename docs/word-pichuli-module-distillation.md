# Word Pichuli 功能模块蒸馏与落地方案

## 项目画像
`word_pichuli` 是一个 Windows Word 批处理工具箱，前端为 Vue 3 + Vite，后端为 Spring Boot 3 + Java 17，桌面壳层为 Electron，另有 Python 辅助脚本。核心流程很清晰：选择工具 -> 上传 DOCX -> 校验 -> 配置参数 -> 异步处理 -> 下载结果。

## 可复用模块
- 批量上传与文件校验：`client/src/utils/wordFileValidation.js`，适合复用到 AI-Interview 的文件入口校验。
- 分步任务体验：`BaseToolComponent.vue`、`StepUpload.vue`、`StepProgress.vue`、`StepResult.vue`，适合异步导出/生成流程。
- 进度与结果管理：`useProcessing.js`、`useSmoothProgress.js`、`batchResults.js`，适合任务中心、失败重试和下载态。
- Word 处理引擎经验：`word-batch-service`、`word-batch-processor`，可作为后续文档处理参考。
- Electron 文件选择/保存：只适合桌面端，不作为 Web 首版依赖。

## AI-Interview 落地
首版先做“面试报告 / 学习笔记 DOCX 导出”，后端放在 `ai-interview-backend/app/services/client/`，路由放在 `ai-interview-backend/app/api/client/v1/`，前端入口放在 `ai-interview-frontend/src/api/` 和 `src/views/`。不新增数据库表，不引入 Celery，导出先走同步生成 + 浏览器下载。

## 执行顺序
1. 新增 DOCX 生成服务。
2. 接入面试报告、单篇笔记、笔记本、全部笔记导出。
3. 前端补 Word 下载按钮。
4. 补单元测试和构建检查。

## 暂缓迁移
Electron 窗口壳层、Java 批处理全套、系统级 Office/桌面依赖暂不迁移。原因是它们和 AI-Interview 的 Web 架构不一致，首版收益低，维护成本高。
