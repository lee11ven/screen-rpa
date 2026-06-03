import type { EditorEdge, EditorNode, EditorWorkflow, RuntimeWorkflow, WfNodeType } from '../dsl/types'
import { parseConditionObject } from '../dsl/types'

/** LogicFlow getGraphRawData 形状（避免依赖命名空间导出） */
export interface LfRawNode {
  id: string
  type: string
  x: number
  y: number
  text?: string | { value?: string }
  properties?: Record<string, unknown>
}

export interface LfRawEdge {
  id: string
  type: string
  sourceNodeId: string
  targetNodeId: string
  sourceAnchorId?: string
  targetAnchorId?: string
  text?: string | { value?: string }
  properties?: Record<string, unknown>
}

export interface LfRawGraph {
  nodes: LfRawNode[]
  edges: LfRawEdge[]
}

const BUILTIN_LOGIC_TYPES = new Set<WfNodeType>(['start', 'end', 'if'])

function isCjkChar(ch: string): boolean {
  return /[\u3400-\u9fff]/.test(ch)
}

export function truncateActionNodeCanvasText(name: string): string {
  if (!name) return ''
  let cjkCount = 0
  for (const ch of name) {
    if (isCjkChar(ch)) cjkCount += 1
  }
  if (cjkCount <= 8) return name

  let kept = ''
  let keptCjk = 0
  for (const ch of name) {
    if (isCjkChar(ch)) {
      if (keptCjk >= 8) break
      keptCjk += 1
    }
    kept += ch
  }
  return `${kept}...`
}

function truncateByCjkLimit(name: string, cjkLimit: number): string {
  if (!name) return ''
  let cjkCount = 0
  for (const ch of name) {
    if (isCjkChar(ch)) cjkCount += 1
  }
  if (cjkCount <= cjkLimit) return name

  let kept = ''
  let keptCjk = 0
  for (const ch of name) {
    if (isCjkChar(ch)) {
      if (keptCjk >= cjkLimit) break
      keptCjk += 1
    }
    kept += ch
  }
  return `${kept}...`
}

export function canvasNodeTextForType(type: WfNodeType, name: string): string {
  if (type === 'action') return truncateActionNodeCanvasText(name)
  if (BUILTIN_LOGIC_TYPES.has(type)) return truncateByCjkLimit(name, 2)
  return name
}

function textValue(text: LfRawNode['text'] | LfRawEdge['text']): string {
  if (text == null) return ''
  if (typeof text === 'string') return text
  if (typeof text === 'object' && 'value' in text) return String((text as { value: string }).value ?? '')
  return ''
}

function ifConditionLabel(kind: string): string {
  if (kind === 'sub_image_exists') return '子图存在'
  if (kind === 'sub_image_not_exists') return '子图不存在'
  return '表达式'
}

export function parseWfType(node: LfRawNode): WfNodeType {
  const p = node.properties as { wfType?: WfNodeType } | undefined
  if (p?.wfType) return p.wfType
  const t = node.type
  if (typeof t === 'string' && t.startsWith('wf-')) {
    return t.slice(3) as WfNodeType
  }
  return 'action'
}

export function editorWorkflowToLfData(wf: EditorWorkflow): LfRawGraph {
  const nodeTypeById = new Map(wf.nodes.map((n) => [n.id, n.type]))
  const toEdgeText = (
    condition: EditorEdge['condition'] | undefined,
    fallbackLabel: string | undefined,
    isIfEdge: boolean,
  ) => {
    if (!isIfEdge) return fallbackLabel ?? ''
    if (!condition || typeof condition !== 'object') return fallbackLabel ?? ''
    const kind = String(condition.kind ?? '').trim()
    if (!kind) return fallbackLabel ?? ''
    return ifConditionLabel(kind)
  }
  const nodes: LfRawNode[] = wf.nodes.map((n) => ({
    id: n.id,
    type: `wf-${n.type}`,
    x: n.ui.position.x,
    y: n.ui.position.y,
    text: canvasNodeTextForType(n.type, n.name),
    properties: {
      wfType: n.type,
      node_name: n.name,
      config: { ...n.config },
      timeout_sec: n.timeout_sec,
      on_error: n.on_error,
      retry_policy: n.retry_policy,
    },
  }))
  const edges: LfRawEdge[] = wf.edges.map((e, i) => ({
    ...(nodeTypeById.get(e.from) === 'if'
      ? {
          text: toEdgeText(e.condition, e.label, true),
          properties: {
            condition: e.condition,
          },
        }
      : {
          text: toEdgeText(undefined, e.label, false),
        }),
    id: `edge_${i}_${e.from}_${e.to}`,
    type: 'bezier',
    sourceNodeId: e.from,
    targetNodeId: e.to,
    sourceAnchorId: e.ui?.source_anchor_id,
    targetAnchorId: e.ui?.target_anchor_id,
  }))
  return { nodes, edges }
}

export function lfDataToEditorWorkflow(
  raw: LfRawGraph,
  meta: Pick<EditorWorkflow, 'workflow_id' | 'name' | 'settings' | 'version' | 'meta' | 'input_schema'>,
): EditorWorkflow {
  const nodes: EditorNode[] = raw.nodes.map((n) => {
    const wfType = parseWfType(n)
    const p = (n.properties ?? {}) as {
      node_name?: string
      config?: Record<string, unknown>
      timeout_sec?: number
      on_error?: EditorNode['on_error']
      retry_policy?: EditorNode['retry_policy']
    }
    return {
      id: n.id,
      type: wfType,
      name: String(p.node_name ?? (textValue(n.text) || wfType)),
      config: { ...(p.config ?? {}) },
      timeout_sec: p.timeout_sec,
      on_error: p.on_error,
      retry_policy: p.retry_policy,
      ui: {
        position: { x: n.x, y: n.y },
      },
    }
  })
  const edges: EditorEdge[] = raw.edges.map((e) => {
    const lab = textValue(e.text).trim()
    const props = (e.properties ?? {}) as { condition?: unknown }
    const condition = parseConditionObject(props.condition)
    return {
      from: e.sourceNodeId,
      to: e.targetNodeId,
      label: lab || undefined,
      condition,
      ui: {
        source_anchor_id: e.sourceAnchorId,
        target_anchor_id: e.targetAnchorId,
      },
    }
  })
  return {
    workflow_id: meta.workflow_id,
    name: meta.name,
    version: meta.version,
    meta: meta.meta,
    settings: meta.settings,
    input_schema: meta.input_schema,
    nodes,
    edges,
  }
}

/** 用当前画布节点位置等信息合并进已有 workflow（保留 workflow_id / name / settings） */
export function mergeLfIntoEditor(
  raw: LfRawGraph,
  previous: EditorWorkflow,
): EditorWorkflow {
  return lfDataToEditorWorkflow(raw, {
    workflow_id: previous.workflow_id,
    name: previous.name,
    settings: previous.settings,
    version: previous.version,
    meta: previous.meta,
    input_schema: previous.input_schema,
  })
}

export function runtimeToEditorBase(runtime: RuntimeWorkflow): Pick<
  EditorWorkflow,
  'workflow_id' | 'name' | 'settings' | 'version' | 'meta' | 'input_schema'
> {
  return {
    workflow_id: runtime.workflow_id,
    name: runtime.name,
    settings: runtime.settings,
    version: runtime.version,
    meta: runtime.meta,
    input_schema: runtime.input_schema,
  }
}
