# backend/bin

`backend/bin` 是系统操作命令层，支持：

- CLI：`python -m bin.index --event ... --function ... --params ...`
- Python：`from bin import execute_event`

## 使用前提

在仓库根目录执行：

```powershell
cd .\backend
```

## 统一约定

- 输出均为单行 JSON：
  - 成功：`{"success": true, "code": "OK", "message": "...", "data": {...}}`
  - 失败：`{"success": false, "code": "SYSxxxx", "message": "...", "data": {...}}`
- 时间参数单位统一为毫秒（ms）。
- `--params` 推荐用 PowerShell 单引号包裹，避免转义问题。
- 当前 `--params` 同时支持标准 JSON 和单引号风格对象（例如 `"{'x': 1}"`）。

## 通用命令格式

```powershell
python -m bin.index --event <event> --function <function> --params '<json-object>'
```

无 `--event` 时，走截图能力。

## 可直接复制执行示例

### screenshot

- 全屏截图（默认输出到当前目录）

```powershell
python -m bin.index --function screenshot --params '{}'
```

- 指定路径 + 区域截图

```powershell
python -m bin.index --function screenshot --params '{"output":"D:/works/screen-rpa/tmp/shot.png","region":[100,120,800,500]}'
```

### mouse

- move

```powershell
python -m bin.index --event mouse --function move --params '{"x":300,"y":200,"move_duration":200}'
```

- subclick

```powershell
python -m bin.index --event mouse --function subclick --params '{"x":300,"y":200,"button":"left","clicks":1,"interval":0}'
```

- dbclick

```powershell
python -m bin.index --event mouse --function dbclick --params '{"x":300,"y":200}'
```

- rclick

```powershell
python -m bin.index --event mouse --function rclick --params '{"x":300,"y":200}'
```

- drag

```powershell
python -m bin.index --event mouse --function drag --params '{"start_x":300,"start_y":200,"end_x":500,"end_y":300,"duration":500,"button":"left"}'
```

- scroll

```powershell
python -m bin.index --event mouse --function scroll --params '{"amount":-5,"x":500,"y":500}'
```

- position

```powershell
python -m bin.index --event mouse --function position --params '{}'
```

### keyboard

- listkeys

```powershell
python -m bin.index --event keyboard --function listkeys --params '{}'
```

- press

```powershell
python -m bin.index --event keyboard --function press --params '{"key":"enter","presses":1,"interval":0}'
```

- hotkey（数组写法）

```powershell
python -m bin.index --event keyboard --function hotkey --params '{"keys":["ctrl","c"],"delay":200}'
```

- hotkey（逗号字符串写法）

```powershell
python -m bin.index --event keyboard --function hotkey --params '{"keys":"ctrl,shift,s","delay":200}'
```

- type（剪贴板粘贴输入）

```powershell
python -m bin.index --event keyboard --function type --params '{"text":"hello","use_clipboard":true,"interval":0}'
```

- type（逐字输入）

```powershell
python -m bin.index --event keyboard --function type --params '{"text":"hello","use_clipboard":false,"interval":50}'
```

### process

- pid

```powershell
python -m bin.index --event process --function pid --params '{"process_name":"notepad.exe"}'
```

- kill

```powershell
python -m bin.index --event process --function kill --params '{"pid":1234}'
```

- activate_process_window

```powershell
python -m bin.index --event process --function activate_process_window --params '{"pid":1234}'
```

- window_find（按标题）

```powershell
python -m bin.index --event process --function window_find --params '{"title":"记事本"}'
```

- window_find（按进程名）

```powershell
python -m bin.index --event process --function window_find --params '{"process_name":"notepad.exe"}'
```

- window_activate（按 hwnd）

```powershell
python -m bin.index --event process --function window_activate --params '{"hwnd":123456}'
```

- window_activate（按标题）

```powershell
python -m bin.index --event process --function window_activate --params '{"title":"记事本"}'
```

### clipboard

- set_text

```powershell
python -m bin.index --event clipboard --function set_text --params '{"text":"hello clipboard"}'
```

- get_text

```powershell
python -m bin.index --event clipboard --function get_text --params '{}'
```

### exec

- PowerShell 命令

```powershell
python -m bin.index --event exec --function run --params '{"command":"Get-Date","shell":"powershell","timeout_ms":5000,"encoding":"utf-8"}'
```

- cmd 命令

```powershell
python -m bin.index --event exec --function run --params '{"command":"echo hello","shell":"cmd","timeout_ms":5000,"encoding":"utf-8"}'
```

### getxy

> 请先准备两张本地图片：`page`（大图）和 `sub`（模板图）。

```powershell
python -m bin.index --event getxy --function match --params '{"page":"D:/works/screen-rpa/tmp/page.png","sub":"D:/works/screen-rpa/tmp/sub.png","threshold":0.85}'
```

### ocr

> OCR 依赖默认不随主包安装；生产环境请使用 `pip install .[ocr]` 安装可选依赖。

- recognize（返回 OCR 原始行结果）

```powershell
python -m bin.index --event ocr --function recognize --params '{"page":"D:/works/screen-rpa/tmp/page.png","min_confidence":0.5}'
```

- locate_text（按文本匹配并返回 found/box/center/confidence）

```powershell
python -m bin.index --event ocr --function locate_text --params '{"page":"D:/works/screen-rpa/tmp/page.png","text":"提交","contains":true,"min_confidence":0.5}'
```

## Python 调用示例

```python
from bin import execute_event

resp = execute_event("mouse", "move", {"x": 400, "y": 300, "move_duration": 150})
if not resp["success"]:
    raise RuntimeError(resp["message"])
```

## 常见错误

- 错误：`python -m .\backend\bin\index.py ...`
  - 原因：`-m` 后必须是模块名，不能是路径。
  - 正确：在 `backend` 目录执行 `python -m bin.index ...`

- 错误：`unrecognized arguments: text...`
  - 原因：PowerShell 把 `--params` 拆成多个参数。
  - 正确：`--params` 用单引号包整段 JSON。

