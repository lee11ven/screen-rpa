export type WfNodeType =
  | 'start'
  | 'end'
  | 'action'
  | 'wait'
  | 'if'
  | 'subflow'
  | 'lowcode_function'
  | 'loop-container'
  | 'loop_start'
  | 'continue'
  | 'break'

export type OnErrorPolicy = 'fail' | 'retry' | 'skip' | 'to_node'

export interface RetryPolicy {
  max_retries: number
  interval_ms: number
  backoff: 'fixed' | 'exponential'
}

export interface WorkflowSettings {
  default_timeout_sec: number
  max_retries: number
  max_loop_iterations: number
}

export interface RuntimeNode {
  id: string
  type: WfNodeType
  name: string
  config: Record<string, unknown>
  timeout_sec?: number
  on_error?: OnErrorPolicy
  retry_policy?: RetryPolicy
}

export type ConditionKind =
  | 'none'
  | 'expression'
  | 'image_exists'
  | 'image_not_exists'
  | 'window_active'
  | 'clipboard_changed'
  | 'sub_image_exists'
  | 'sub_image_not_exists'

export interface ConditionObject {
  kind: ConditionKind
  params?: Record<string, unknown>
}

const CONDITION_KIND_VALUES = [
  'none',
  'expression',
  'image_exists',
  'image_not_exists',
  'window_active',
  'clipboard_changed',
  'sub_image_exists',
  'sub_image_not_exists',
] as const satisfies readonly ConditionKind[]

const CONDITION_KIND_SET = new Set<string>(CONDITION_KIND_VALUES)

function isConditionKind(s: string): s is ConditionKind {
  return CONDITION_KIND_SET.has(s)
}

/** 从 LogicFlow / 持久化 JSON 等未知结构解析边条件 */
export function parseConditionObject(value: unknown): ConditionObject | undefined {
  if (!value || typeof value !== 'object') return undefined
  const o = value as Record<string, unknown>
  const kindRaw = o.kind
  if (typeof kindRaw !== 'string' || !isConditionKind(kindRaw)) return undefined
  const out: ConditionObject = { kind: kindRaw }
  const params = o.params
  if (params !== undefined) {
    if (typeof params === 'object' && params !== null && !Array.isArray(params)) {
      out.params = params as Record<string, unknown>
    }
  }
  return out
}

export interface RuntimeEdge {
  from: string
  to: string
  label?: string
  condition?: ConditionObject
}

export interface EdgeUi {
  source_anchor_id?: string
  target_anchor_id?: string
}

export interface RuntimeWorkflow {
  workflow_id: string
  name: string
  version?: number
  meta?: Record<string, unknown>
  settings: WorkflowSettings
  input_schema?: Record<string, unknown>
  nodes: RuntimeNode[]
  edges: RuntimeEdge[]
}

export interface NodeUi {
  position: { x: number; y: number }
  size?: { w: number; h: number }
  color?: string
}

export interface EditorNode extends RuntimeNode {
  ui: NodeUi
}

export interface EditorEdge extends RuntimeEdge {
  ui?: EdgeUi
}

export interface EditorWorkflow {
  workflow_id: string
  name: string
  version?: number
  meta?: Record<string, unknown>
  settings: WorkflowSettings
  input_schema?: Record<string, unknown>
  nodes: EditorNode[]
  edges: EditorEdge[]
}

export interface ValidateIssue {
  path: string
  message: string
  node_id?: string
}
