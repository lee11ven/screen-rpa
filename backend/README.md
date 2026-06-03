# Screen RPA — Workflow Backend

## Run API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

## Run Worker

```bash
cd backend
python -m app.worker
```

## System Operation CLI

```bash
cd backend
python -m bin.index --function screenshot --params "{}"
python -m bin.index --event mouse --function move --params "{\"x\": 300, \"y\": 300, \"move_duration\": 200}"
```

- `--params` is a JSON object string.
- Time-related params are in milliseconds.
- The workflow runtime action adapter now uses the same `bin` modules through `app.orchestration_adapters.system_actions`.

## 节点动作映射表（前端参数 -> 应用层处理 -> bin调用）

执行链路统一为：`WorkflowRunService.execute_run_sync` -> `RuntimeExecutor._exec_action` -> `run_system_action` -> `bin.execute_event(...)`。

### 1) 鼠标类动作

| 前端 action_key | 前端关键参数 | 应用层处理（`app.orchestration_adapters.system_actions`） | bin 调用 |
| --- | --- | --- | --- |
| `system.mouse_move` | `x`,`y`,`duration_ms`,`relative`,`pre_template_path`,`pre_threshold`,`pre_use_center_xy` | `relative=true` 时先读当前鼠标坐标再做偏移；若配置前置模板且 `pre_use_center_xy=true`，会先模板匹配并覆盖 `x/y` | `execute_event("mouse","move",{"x","y","move_duration"})` |
| `system.mouse_click` | `x`,`y`,`button`,`clicks`,`interval_ms`,`pre_*` | 根据 `button/clicks` 选择 `subclick/dbclick/rclick`；前置定位可覆盖 `x/y` | `execute_event("mouse","subclick/dbclick/rclick",{...})` |
| `system.mouse_drag` | `start_x`,`start_y`,`end_x`,`end_y`,`duration_ms`,`button`,`jitter_px`,`pre_start_*`,`pre_end_*` | 起点/终点可分别由模板定位覆盖（需对应 `pre_*_use_center_xy=true`）；`jitter_px` 会对终点随机扰动 | `execute_event("mouse","drag",{"start_x","start_y","end_x","end_y","duration","button"})` |
| `system.mouse_scroll` | `delta`,`x`,`y`,`pre_*` | 统一转为数值；若前置模板启用中心点覆盖，则覆盖 `x/y`；约定 `delta > 0` 向下滚、`delta < 0` 向上滚 | `execute_event("mouse","scroll",{"amount","x","y"})` |
| `system.mouse_smartclick` | `anchor_sub`,`target_sub`,`logical_dx`,`logical_dy`,`smart_timeout`,`smart_step_px` | 循环：截图 -> 模板匹配（优先 target，再 anchor）-> 命中后按逻辑偏移点击；未命中则滚动重试直到超时 | 组合调用：`screenshot` + `getxy.match` + `mouse.scroll` + `mouse.subclick` |

> 说明：前置/图像定位若未提供 `page_path/pre_page_path`，应用层会自动截图后再匹配。

### 2) 键盘类动作

| 前端 action_key | 前端关键参数 | 应用层处理 | bin 调用 |
| --- | --- | --- | --- |
| `system.keyboard_type_text` | `text_source`,`text`,`text_var_key`,`interval_ms`,`use_clipboard` | `text_source=global_var` 时使用 `text_var_key` 作为文本来源；其余直接用 `text` | `execute_event("keyboard","type",{"text","interval","use_clipboard"})` |
| `system.keyboard_press_key` | `key`,`hold_ms` | 当前映射为单次按键；`hold_ms` 映射到 `interval` 参数 | `execute_event("keyboard","press",{"key","presses":1,"interval"})` |
| `system.keyboard_hotkey` | `keys`,`hold_ms`,`post_delay_ms`,`disable_failsafe` | `hold_ms` 映射为执行前 delay；执行后按 `post_delay_ms` 额外 sleep；默认临时关闭 pyautogui fail-safe | `execute_event("keyboard","hotkey",{"keys","delay","disable_failsafe"})` |
| `system.keyboard_hotkey_physical` | `keys`,`modifier_down_gap_ms`,`main_key_hold_ms`,`release_gap_ms`,`post_delay_ms`,`disable_failsafe` | 修饰键按下 -> 主键按下/抬起 -> 修饰键逆序抬起；执行后按 `post_delay_ms` 额外 sleep；默认临时关闭 pyautogui fail-safe | `execute_event("keyboard","hotkey_physical",{...})` |

### 3) 图像类动作

| 前端 action_key | 前端关键参数 | 应用层处理 | bin 调用 |
| --- | --- | --- | --- |
| `system.image_locate_center` | `template_path`,`threshold`,`multi_scale` | 目前使用单尺度匹配；返回中心坐标/置信度 | `execute_event("getxy","match",{"page","sub","threshold"})` |
| `system.image_click_center` | `template_path`,`threshold`,`button`,`clicks` | 先定位中心点，再按定位结果点击 | `getxy.match` -> `mouse.subclick` |

> 当前 `bin.getxy` 暂不支持多尺度参数，`multi_scale` 暂未下沉到底层能力。

### 4) 窗口/剪贴板/命令动作

| 前端 action_key | 前端关键参数 | 应用层处理 | bin 调用 |
| --- | --- | --- | --- |
| `system.window_find` | `title`,`class_name`,`process_name`,`timeout_ms` | 下发 `title/process_name/class_name`；若 `timeout_ms>0` 会按 `poll_interval_ms` 轮询查找直到超时 | `execute_event("process","window_find",{"title","process_name","class_name"})` |
| `system.window_activate` | `hwnd`,`title` | 直接透传并由底层按句柄或标题激活 | `execute_event("process","window_activate",params)` |
| `system.clipboard_set_text` | `text` | 直接映射写剪贴板 | `execute_event("clipboard","set_text",{"text"})` |
| `system.clipboard_get_text` | 无 | 直接读取剪贴板文本 | `execute_event("clipboard","get_text",{})` |
| `system.exec_command` | `command`,`shell`,`timeout_ms`,`encoding` | 直接透传系统命令执行参数 | `execute_event("exec","run",params)` |

### 联调与排障建议

- 先独立验证底层：在 `backend` 目录用 `python -m bin.index ...` 逐个验证 `mouse/keyboard/getxy/process` 是否可用。
- 再验证应用层：构造最小 workflow，仅含单 action 节点，观察 `WorkflowRunLog` 与 `WorkflowRunNode` 状态变化。
- 图像相关问题优先检查：模板路径是否可读、阈值是否过高、截图分辨率与缩放比例是否变化。
- `window_find` 已支持适配层轮询超时，`class_name` 会透传到底层（当前底层若未使用该字段，不影响主流程）。

## Env

- `DATABASE_PATH` — SQLite file (default: `../data/rpa.db` from cwd, or `./data/rpa.db` under repo when started from repo root)
- `WORKER_ID` — worker identity (default: `worker-1`)
- `QUEUE_LEASE_SEC` — message lease time seconds (default: `60`)
- `QUEUE_MAX_RETRY` — max retry attempts (default: `3`)
- `QUEUE_RETRY_BACKOFF_SEC` — retry backoff base seconds (default: `5`)
- `RECOVERY_SCAN_INTERVAL_SEC` — expired lease scan interval seconds (default: `15`)

## Workflow Runtime State & Error Code (简版)

### 运行状态机

- `WorkflowRun.status`: `CREATED -> QUEUED -> RUNNING -> SUCCESS|FAILED|CANCELLED|TIMEOUT`
- `WorkflowRunNode.status`: `PENDING -> RUNNING -> SUCCESS|FAILED|SKIPPED|TIMEOUT`
- `TaskQueueRecord.queue_status`: `ENQUEUED -> DEQUEUED -> DONE` 或 `ENQUEUED|DEQUEUED -> RETRY_WAIT -> DEQUEUED`，最终可到 `DEAD`
- 终态不可逆：`SUCCESS/FAILED/CANCELLED/TIMEOUT` 写入后不再回退。

### 错误处理语义（节点级）

- `on_error=fail`: 立即失败并中断流程
- `on_error=retry`: 在 `retry_policy.max_retries`（或全局 `settings.max_retries`）范围内重试
- `on_error=skip`: 该节点标记 `SKIPPED`，继续后继边
- `on_error=to_node`: 跳转 `config.to_node`（或 `label=error` 的出边）
- `timeout_sec`: 节点执行超时判定，超时按 `on_error` 路径处理

### 幂等与恢复

- 入队幂等：`POST /workflow/{workflow_id}/run` 支持 `idempotency_key`，重复提交返回同一 `run_id`
- 消费幂等：worker 按 `run_id + message_id` 领取，重复消息不会重复执行
- 崩溃补偿：`DEQUEUED` 且 `lease_until` 过期任务会被扫描并重投；超过重试阈值进入 `DEAD`

### API 错误码（当前实现）

- `4001`: 发布校验失败（DSL/图结构/业务校验）
- `4002`: 运行创建失败（如流程不存在、未发布版本等）
- `4040`: run 不存在（状态/日志/取消）
- `4041`: version 不存在
- `5000`: 未处理异常（全局异常处理）

## Tests

From repository root:

```bash
pip install -r backend/requirements.txt
pytest tests -q
```

