<p align="right">
  <a href="README.en.md">English</a>
</p>

<div align="center">
  <img src="frontend/public/logo.png" width="96" alt="Screen RPA Logo" />
</div>

<h1 align="center">🤖 Screen RPA</h1>

<p align="center">
  一个面向 Windows 的可视化自动化流程平台，聚焦流程编排与 PC 端自动化落地。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/Vue-3.x-42b883.svg" alt="Vue" />
  <img src="https://img.shields.io/badge/FastAPI-Workflow%20API-009688.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Platform-Windows-informational.svg" alt="Platform" />
  <img src="https://camo.githubusercontent.com/5ae27c047f5dbaa8d2909bb07be446ec791f9daf429e322106ffb7bba35a4b7e/68747470733a2f2f696d672e736869656c64732e696f2f62616467652fe58d8fe8aeae2d4147504c2d2d332e30253230253242253230e59586e4b89ae68e88e69d832d677265656e2e737667" alt="协议 AGPL-3.0 + 商业授权" />
</p>

## 📖 项目简介

Screen RPA 通过可视化拖拽方式搭建自动化流程，支持从流程设计、版本发布到任务执行和运行观测的完整闭环。  
适用于桌面场景中高频、重复、可标准化的操作任务，例如数据录入、规则化点击、批量处理和流程编排执行。

## 🚀 当前版本进展

### ✅ 已完成

- 流程编排
- PC 端自动化

### 🧩 补充待开发

- 网页数据爬取
- 手机端自动化

## ✨ 核心能力

### 1) 🔁 流程编排能力（已完成）

- 可视化编辑：基于画布拖拽节点搭建流程
- 节点类型覆盖：`start`、`end`、`action`、`wait`、`if`、`subflow`、`loop-container`、`continue`、`break`、`lowcode_function`
- 错误策略：`fail`、`retry`、`skip`、`to_node`
- 契约校验：基于 `contracts/workflow-runtime.schema.json` 提前发现结构问题

### 2) 🖥️ PC 端自动化（已完成）

- 鼠标动作：移动、点击、拖拽、滚动、智能点击
- 键盘动作：文本输入、按键、组合键、物理热键
- 图像能力：模板匹配、定位中心、图像点击
- 系统能力：窗口查找/激活、剪贴板读写、命令执行

### 3) ⚙️ 执行引擎与队列

- 支持直连运行和队列异步执行两种模式
- 基于 `idempotency_key` 避免重复提交导致重复执行
- 内置重试退避、租约恢复和死信路径，提升任务稳定性

### 4) 📊 运行观测

- 运行总览：状态、节点结果、错误信息
- 节点日志：按节点查看上下文与执行过程
- 运行控制：支持取消运行及时止损
- 队列跟踪：观察任务入队、消费、重试、完成全链路

## 🎯 能做什么

- 搭建可发布、可回溯的桌面自动化流程
- 实现跨节点条件判断、循环控制与子流程复用
- 处理批量录入、批量回填、规则化系统操作
- 通过低代码函数节点补充业务逻辑

## 🗂️ 项目结构

```text
screen-rpa/
  backend/                 # FastAPI + SQLite + 执行引擎 + Worker
  frontend/                # Vue3 + Vite + Element Plus 管理台
  contracts/               # 工作流 Runtime JSON Schema 与示例
  tests/                   # API / 引擎 / system actions / 契约测试
  packaging/               # PyInstaller / Inno Setup 打包脚本
  data/                    # 本地数据库与运行数据
```

## 🚀 快速开始（开发模式）

### 🧱 环境要求

- Windows（推荐）
- Python 3.10+
- Node.js 18+
- npm 9+

### 方式 A：⚡ 一键启动前后端与 Worker

```bash
dev.bat
```

将同时启动：

- 后端 API（`uvicorn`）
- Worker（`python -m app.worker`）
- 前端开发服务（`npm run dev`）

### 方式 B：🛠️ 手动启动

1) 启动后端 API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

2) 启动 Worker（异步/队列执行需要）

```bash
cd backend
python -m app.worker
```

3) 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 健康检查：`http://127.0.0.1:8000/health`

## 🔌 API 与协议

- API 前缀：`/api/workflow`
- 统一响应：`success / code / message / data`
- 协议版本：`GET /api/workflow/meta/protocol`
- DSL 契约：`contracts/workflow-runtime.schema.json`
- 示例：`contracts/examples/minimal-runtime.json`

## ✅ 测试与质量保障

```bash
pip install -r backend/requirements.txt
pytest tests -q
```

当前测试覆盖 API、契约校验、执行器与系统动作核心链路，便于持续集成快速回归。

## 📦 打包为桌面应用

```bash
build.bat
```

默认输出目录：`dist/ScreenRPA/`，可进一步通过 `packaging/installer.iss` 生成安装包。

## 🧪 常用后端环境变量

- `DATABASE_PATH`：SQLite 文件路径（默认 `../data/rpa.db`）
- `WORKER_ID`：Worker 标识（默认 `worker-1`）
- `QUEUE_LEASE_SEC`：消息租约秒数（默认 `60`）
- `QUEUE_MAX_RETRY`：最大重试次数（默认 `3`）
- `QUEUE_RETRY_BACKOFF_SEC`：重试退避基数秒（默认 `5`）
- `RECOVERY_SCAN_INTERVAL_SEC`：过期租约扫描间隔秒（默认 `15`）

## 🛣️ Roadmap

- [ ] 网页数据爬取能力（浏览器采集、元素提取、下载链路）
- [ ] 手机端自动化能力（设备连接、触摸操作、识别点击）
- [ ] 更丰富的开箱即用动作节点
- [ ] 更完善的运行指标与报表能力

---

如果你正在寻找一个“可视化 + 可发布 + 可观测”的自动化流程引擎，`Screen RPA` 可以作为一个务实的落地起点。欢迎提交 Issue / PR 共建。
