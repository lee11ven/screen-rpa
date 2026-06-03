# Screen RPA Frontend

基于 `Vue 3 + TypeScript + Vite + Element Plus` 的工作流编排前端，用于工作流编辑、版本管理、运行监控与系统配置。

## 功能概览

- 工作流列表与基础管理
- 可视化编辑器（LogicFlow）
- 版本记录与发布相关流程
- 运行详情与日志查看
- 全局对象配置、队列管理、系统配置

## 技术栈

- `Vue 3`（`<script setup>`）
- `TypeScript`
- `Vite`
- `Pinia`
- `Vue Router`
- `Element Plus`
- `Axios`
- `Vitest`

## 环境要求

- `Node.js` 18+
- `npm` 9+

## 快速开始

1. 安装依赖

```bash
npm install
```

2. 启动开发环境

```bash
npm run dev
```

默认访问地址：`http://127.0.0.1:5173`

> 本地开发时，前端会将 `/api` 代理到 `http://127.0.0.1:8000`，请确保后端服务已启动。

## 常用命令

- 启动开发服务器：`npm run dev`
- 生产构建：`npm run build`
- 本地预览构建产物：`npm run preview`
- 运行单测：`npm run test`
- 监听模式运行单测：`npm run test:watch`

## 目录结构

```text
frontend/
  public/                    # 静态资源
  src/
    api/                     # HTTP 请求封装
    assets/                  # 资源文件
    layouts/                 # 布局组件
    modules/workflow/        # 工作流核心模块
      components/            # 页面级与复用组件
      dsl/                   # DSL 定义、编译与校验
      logicflow/             # LogicFlow 适配与节点注册
      pages/                 # 业务页面
      services/              # 业务 API 调用
      stores/                # Pinia 状态管理
    router/                  # 路由配置
    config.ts                # 轮询、自动保存等前端常量
```

## 前后端联调说明

- API 基础路径统一使用 `/api`
- 响应结构采用统一信封格式（`success/code/message/data`）
- 前端会在网络或业务错误时统一弹出错误提示

## 相关说明

- TypeScript 路径别名：
  - `@/*` -> `src/*`
  - `@contracts/*` -> `../contracts/*`
- 测试框架使用 `Vitest`，运行环境为 `jsdom`
