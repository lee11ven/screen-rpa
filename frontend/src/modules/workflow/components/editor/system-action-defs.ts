/** 系统动作定义与参数归一化（主画布与循环子图编辑器共用） */
export type ActionParamInputType = 'string' | 'number' | 'boolean' | 'string_array'
export interface ActionParamDef {
  key: string
  label: string
  type: ActionParamInputType
  min?: number
  placeholder?: string
}
export interface ActionDef {
  key: string
  label: string
  description: string
  params: ActionParamDef[]
  defaults: Record<string, unknown>
}
export interface ActionParamGroup {
  key: string
  label: string
  params: ActionParamDef[]
}

export const SYSTEM_ACTIONS: ActionDef[] = [
  {
    key: 'system.mouse_move',
    label: '鼠标移动',
    description: '移动鼠标到目标坐标',
    params: [
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
      { key: 'x', label: 'X', type: 'number' },
      { key: 'y', label: 'Y', type: 'number' },
      { key: 'duration_ms', label: '移动耗时(ms)', type: 'number', min: 0 },
      { key: 'relative', label: '相对移动', type: 'boolean' },
    ],
    defaults: {
      x: 0,
      y: 0,
      duration_ms: 200,
      relative: false,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.mouse_click',
    label: '鼠标点击',
    description: '在坐标点击（单/双/多击）',
    params: [
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
      { key: 'x', label: 'X', type: 'number' },
      { key: 'y', label: 'Y', type: 'number' },
      { key: 'button', label: '按钮', type: 'string', placeholder: 'left/right/middle' },
      { key: 'clicks', label: '点击次数', type: 'number', min: 1 },
      { key: 'interval_ms', label: '点击间隔(ms)', type: 'number', min: 0 },
    ],
    defaults: {
      x: 0,
      y: 0,
      button: 'left',
      clicks: 1,
      interval_ms: 0,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.mouse_drag',
    label: '鼠标拖拽',
    description: '按住拖拽到目标点',
    params: [
      { key: 'pre_start_template_path', label: '前置起点图像模板路径(对应起点X/Y)', type: 'string' },
      { key: 'pre_start_threshold', label: '前置起点匹配阈值', type: 'number', min: 0 },
      { key: 'pre_start_use_center_xy', label: '起点使用前置定位中心点(x,y)', type: 'boolean' },
      { key: 'start_x', label: '起点X', type: 'number' },
      { key: 'start_y', label: '起点Y', type: 'number' },
      { key: 'pre_end_template_path', label: '前置终点图像模板路径(对应终点X/Y)', type: 'string' },
      { key: 'pre_end_threshold', label: '前置终点匹配阈值', type: 'number', min: 0 },
      { key: 'pre_end_use_center_xy', label: '终点使用前置定位中心点(x,y)', type: 'boolean' },
      { key: 'end_x', label: '终点X', type: 'number' },
      { key: 'end_y', label: '终点Y', type: 'number' },
      { key: 'duration_ms', label: '时长(ms)', type: 'number', min: 0 },
      { key: 'jitter_px', label: '抖动值(px)', type: 'number', min: 0 },
      { key: 'button', label: '按钮', type: 'string', placeholder: 'left/right/middle' },
    ],
    defaults: {
      pre_start_template_path: '',
      pre_start_threshold: 0.85,
      pre_start_use_center_xy: false,
      pre_end_template_path: '',
      pre_end_threshold: 0.85,
      pre_end_use_center_xy: false,
      start_x: 0,
      start_y: 0,
      end_x: 100,
      end_y: 100,
      duration_ms: 500,
      jitter_px: 0,
      button: 'left',
    },
  },
  {
    key: 'system.mouse_scroll',
    label: '鼠标滚轮',
    description: '按坐标滚动滚轮',
    params: [
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
      { key: 'delta', label: '滚动量', type: 'number' },
      { key: 'x', label: 'X(可选)', type: 'number' },
      { key: 'y', label: 'Y(可选)', type: 'number' },
    ],
    defaults: {
      delta: 3,
      x: 0,
      y: 0,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.keyboard_type_text',
    label: '键盘输入文本',
    description: '输入文本内容',
    params: [
      { key: 'text_source', label: '文本来源', type: 'string', placeholder: 'literal/global_var' },
      { key: 'text', label: '文本', type: 'string' },
      { key: 'text_var_key', label: '全局变量Key', type: 'string', placeholder: 'ctx.user_name' },
      { key: 'interval_ms', label: '字间隔(ms)', type: 'number', min: 0 },
      { key: 'use_clipboard', label: '使用剪贴板', type: 'boolean' },
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
    ],
    defaults: {
      text_source: 'literal',
      text: '',
      text_var_key: '',
      interval_ms: 50,
      use_clipboard: true,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.keyboard_press_key',
    label: '键盘按键',
    description: '单按键输入',
    params: [
      { key: 'key', label: '按键', type: 'string', placeholder: 'enter/tab/esc...' },
      { key: 'hold_ms', label: '按住时长(ms)', type: 'number', min: 0 },
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
    ],
    defaults: {
      key: 'enter',
      hold_ms: 0,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.keyboard_hotkey',
    label: '组合快捷键',
    description: '按顺序触发快捷键',
    params: [
      { key: 'keys', label: '按键序列', type: 'string_array', placeholder: 'ctrl,shift,s' },
      { key: 'hold_ms', label: '主键按住(ms)', type: 'number', min: 0 },
      { key: 'post_delay_ms', label: '执行后等待(ms)', type: 'number', min: 0 },
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
    ],
    defaults: {
      keys: ['ctrl', 'c'],
      hold_ms: 0,
      post_delay_ms: 0,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.keyboard_hotkey_physical',
    label: '组合快捷键(物理按键)',
    description: '按下修饰键后触发主键并逆序释放，适合远程桌面场景',
    params: [
      { key: 'keys', label: '按键序列', type: 'string_array', placeholder: 'win,r' },
      { key: 'modifier_down_gap_ms', label: '修饰键按下间隔(ms)', type: 'number', min: 0 },
      { key: 'main_key_hold_ms', label: '主键按住时长(ms)', type: 'number', min: 0 },
      { key: 'release_gap_ms', label: '释放间隔(ms)', type: 'number', min: 0 },
      { key: 'post_delay_ms', label: '执行后等待(ms)', type: 'number', min: 0 },
      { key: 'disable_failsafe', label: '禁用PyAutoGUI fail-safe', type: 'boolean' },
      { key: 'pre_template_path', label: '前置图像模板路径', type: 'string' },
      { key: 'pre_threshold', label: '前置匹配阈值', type: 'number', min: 0 },
      { key: 'pre_use_center_xy', label: '使用前置定位中心点(x,y)', type: 'boolean' },
    ],
    defaults: {
      keys: ['win', 'r'],
      modifier_down_gap_ms: 30,
      main_key_hold_ms: 50,
      release_gap_ms: 20,
      post_delay_ms: 0,
      disable_failsafe: true,
      pre_template_path: '',
      pre_threshold: 0.85,
      pre_use_center_xy: false,
    },
  },
  {
    key: 'system.image_locate_center',
    label: '图像定位中心点',
    description: '模板匹配并返回中心坐标',
    params: [
      { key: 'template_path', label: '模板路径', type: 'string' },
      { key: 'threshold', label: '阈值', type: 'number', min: 0 },
      { key: 'multi_scale', label: '多尺度匹配', type: 'boolean' },
    ],
    defaults: { template_path: '', threshold: 0.85, multi_scale: false },
  },
  {
    key: 'system.image_click_center',
    label: '图像定位后点击',
    description: '定位中心点后执行点击',
    params: [
      { key: 'template_path', label: '模板路径', type: 'string' },
      { key: 'threshold', label: '阈值', type: 'number', min: 0 },
      { key: 'button', label: '按钮', type: 'string', placeholder: 'left/right/middle' },
      { key: 'clicks', label: '点击次数', type: 'number', min: 1 },
    ],
    defaults: { template_path: '', threshold: 0.85, button: 'left', clicks: 1 },
  },
  {
    key: 'system.window_find',
    label: '查找窗口',
    description: '按标题/类名/进程查找窗口',
    params: [
      { key: 'title', label: '窗口标题', type: 'string' },
      { key: 'class_name', label: '类名', type: 'string' },
      { key: 'process_name', label: '进程名', type: 'string' },
      { key: 'timeout_ms', label: '超时(ms)', type: 'number', min: 0 },
    ],
    defaults: { title: '', class_name: '', process_name: '', timeout_ms: 2000 },
  },
  {
    key: 'system.window_activate',
    label: '激活窗口',
    description: '激活并置前窗口',
    params: [
      { key: 'hwnd', label: '窗口句柄(hwnd)', type: 'number', min: 0 },
      { key: 'title', label: '窗口标题(可选)', type: 'string' },
    ],
    defaults: { hwnd: 0, title: '' },
  },
  {
    key: 'system.clipboard_set_text',
    label: '写入剪贴板文本',
    description: '设置系统剪贴板文本内容',
    params: [{ key: 'text', label: '文本', type: 'string' }],
    defaults: { text: '' },
  },
  {
    key: 'system.clipboard_get_text',
    label: '读取剪贴板文本',
    description: '读取系统剪贴板文本',
    params: [],
    defaults: {},
  },
  {
    key: 'system.exec_command',
    label: '执行系统命令',
    description: '执行命令并返回输出',
    params: [
      { key: 'command', label: '命令', type: 'string' },
      { key: 'shell', label: 'Shell', type: 'string', placeholder: 'cmd/powershell' },
      { key: 'timeout_ms', label: '超时(ms)', type: 'number', min: 0 },
      { key: 'encoding', label: '编码', type: 'string', placeholder: 'utf-8/gbk' },
    ],
    defaults: { command: '', shell: 'powershell', timeout_ms: 5000, encoding: 'utf-8' },
  },
  {
    key: 'system.ocr_check_text',
    label: 'OCR文本校验',
    description: '截图后OCR识别，并校验是否包含目标文本（如订单号）',
    params: [
      { key: 'expected_text', label: '目标文本', type: 'string' },
      { key: 'page_path', label: '页面截图路径(可选)', type: 'string' },
      { key: 'contains', label: '包含匹配', type: 'boolean' },
      { key: 'ignore_case', label: '忽略大小写', type: 'boolean' },
      { key: 'ignore_spaces', label: '忽略空白字符', type: 'boolean' },
      { key: 'min_confidence', label: '最小置信度', type: 'number', min: 0 },
    ],
    defaults: {
      expected_text: '',
      page_path: '',
      contains: true,
      ignore_case: false,
      ignore_spaces: true,
      min_confidence: 0.5,
    },
  },
  {
    key: 'system.mouse_smartclick',
    label: '智能滚动点击(多滚动条)',
    description: '锚点+逻辑偏移+滚动条策略定位后点击',
    params: [
      { key: 'anchor_sub', label: '锚点模板', type: 'string' },
      { key: 'target_sub', label: '目标模板', type: 'string' },
      { key: 'logical_dx', label: '逻辑偏移dx', type: 'number' },
      { key: 'logical_dy', label: '逻辑偏移dy', type: 'number' },
      { key: 'smart_timeout', label: '总超时(ms)', type: 'number', min: 0 },
      { key: 'smart_step_px', label: '滚动步长(px)', type: 'number', min: 1 },
    ],
    defaults: { anchor_sub: '', target_sub: '', logical_dx: 0, logical_dy: 0, smart_timeout: 6000, smart_step_px: 120 },
  },
]
export const ACTION_DEF_MAP = new Map(SYSTEM_ACTIONS.map((a) => [a.key, a]))
export const PRE_LOCATE_XY_ACTIONS = new Set<string>([
  'system.mouse_move',
  'system.mouse_click',
  'system.mouse_scroll',
])

function toStringArrayInput(v: unknown): string {
  if (Array.isArray(v)) return v.map((x) => String(x)).join(',')
  return String(v ?? '')
}

export function mergeActionParams(actionKey: string, rawParams: unknown): Record<string, unknown> {
  const def = ACTION_DEF_MAP.get(actionKey)
  if (!def) return (rawParams as Record<string, unknown>) ?? {}
  const base = { ...def.defaults }
  const src = (rawParams as Record<string, unknown>) ?? {}
  for (const p of def.params) {
    if (src[p.key] !== undefined) {
      base[p.key] = p.type === 'string_array' ? toStringArrayInput(src[p.key]) : src[p.key]
    }
  }
  return base
}

export function normalizeActionParams(actionKey: string, params: Record<string, unknown>): Record<string, unknown> {
  const def = ACTION_DEF_MAP.get(actionKey)
  if (!def) return { ...params }
  const out: Record<string, unknown> = {}
  for (const p of def.params) {
    const v = params[p.key]
    if (v === '' || v === undefined || v === null) continue
    if (p.type === 'string_array') {
      out[p.key] = String(v)
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
    } else {
      out[p.key] = v
    }
  }
  const preTemplatePath = String(out.pre_template_path ?? '').trim()
  if (preTemplatePath && PRE_LOCATE_XY_ACTIONS.has(actionKey)) {
    delete out.x
    delete out.y
  }
  if (actionKey === 'system.mouse_drag') {
    const preStartTemplatePath = String(out.pre_start_template_path ?? '').trim()
    const preEndTemplatePath = String(out.pre_end_template_path ?? '').trim()
    const preStartUseCenterXy = Boolean(out.pre_start_use_center_xy)
    const preEndUseCenterXy = Boolean(out.pre_end_use_center_xy)
    if (preStartTemplatePath && preStartUseCenterXy) {
      delete out.start_x
      delete out.start_y
    }
    if (preEndTemplatePath && preEndUseCenterXy) {
      delete out.end_x
      delete out.end_y
    }
  }
  if (actionKey === 'system.keyboard_type_text') {
    const textSource = String(out.text_source ?? 'literal')
    if (textSource === 'global_var') {
      delete out.text
    } else {
      delete out.text_var_key
    }
  }
  return out
}

export function shouldDisableActionParamInput(
  form: { action_key: string; action_params: Record<string, unknown> },
  paramKey: string,
): boolean {
  if (form.action_key === 'system.keyboard_type_text') {
    const textSource = String(form.action_params.text_source ?? 'literal')
    if (paramKey === 'text') return textSource === 'global_var'
    if (paramKey === 'text_var_key') return textSource !== 'global_var'
  }
  if (form.action_key === 'system.mouse_drag') {
    const preStartTemplatePath = String(form.action_params.pre_start_template_path ?? '').trim()
    const preEndTemplatePath = String(form.action_params.pre_end_template_path ?? '').trim()
    const preStartUseCenterXy = Boolean(form.action_params.pre_start_use_center_xy)
    const preEndUseCenterXy = Boolean(form.action_params.pre_end_use_center_xy)
    if ((paramKey === 'start_x' || paramKey === 'start_y') && preStartTemplatePath && preStartUseCenterXy) return true
    if ((paramKey === 'end_x' || paramKey === 'end_y') && preEndTemplatePath && preEndUseCenterXy) return true
    return false
  }

  if (paramKey !== 'x' && paramKey !== 'y') return false
  if (!PRE_LOCATE_XY_ACTIONS.has(form.action_key)) return false
  const preUseCenterXy = Boolean(form.action_params.pre_use_center_xy)
  if (preUseCenterXy) return true
  const preTemplatePath = String(form.action_params.pre_template_path ?? '').trim()
  return preTemplatePath.length > 0
}
