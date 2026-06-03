import type { EditorWorkflow, RuntimeWorkflow, WfNodeType } from './types'

/** 与 compiler 中一致：画布节点坐标、边锚点等编辑器专用元数据 */
export const EDITOR_UI_META_KEY = '__editor_ui__'

export const DEFAULT_SETTINGS = {
  default_timeout_sec: 60,
  max_retries: 0,
  max_loop_iterations: 1000,
} as const

export function defaultNodeConfig(type: WfNodeType): Record<string, unknown> {
  switch (type) {
    case 'action':
      return {
        action_key: 'system.mouse_click',
        params: { x: 0, y: 0, button: 'left', clicks: 1, interval_ms: 0 },
        timeout_ms: 3000,
        poll_interval_ms: 150,
        retry_times: 1,
        retry_interval_ms: 200,
        post_delay_ms: 120,
        jitter_ms: 30,
        success_condition: { kind: 'none', params: {} },
      }
    case 'wait':
      return {
        timeout_ms: 5000,
        poll_interval_ms: 150,
        condition: { kind: 'image_exists', params: { template_path: '', threshold: 0.85 } },
      }
    case 'if':
      return {}
    case 'subflow':
      return { workflow_id: '', input_mapping: {}, output_mapping: {} }
    case 'lowcode_function':
      return {
        code_body: "return {'ok': True, 'data': {}}",
        timeout_ms: 3000,
        retry_times: 0,
        enabled: true,
      }
    case 'loop-container':
      return {
        loopId: `loop_${Math.random().toString(36).slice(2, 8)}`,
        maxIterations: 100,
        subGraph: {
          nodes: [
            { id: 'loop_start_1', type: 'loop_start', name: '循环开始', config: {} },
            { id: 'loop_continue_1', type: 'continue', name: '继续下一轮', config: { sleep_ms: 200 } },
          ],
          edges: [{ from: 'loop_start_1', to: 'loop_continue_1' }],
        },
      }
    case 'loop_start':
      return {}
    case 'continue':
      return { sleep_ms: 200 }
    case 'break':
      return {}
    default:
      return {}
  }
}

export function layoutPosition(index: number): { x: number; y: number } {
  const col = index % 4
  const row = Math.floor(index / 4)
  return { x: 140 + col * 200, y: 100 + row * 140 }
}

/** 将纯 Runtime 草稿转为可编辑模型（补齐 ui） */
export function editorFromRuntime(runtime: RuntimeWorkflow): EditorWorkflow {
  const meta = (runtime.meta ?? {}) as Record<string, unknown>
  const uiMeta = (meta[EDITOR_UI_META_KEY] ?? {}) as {
    node_positions?: Record<string, { x?: number; y?: number }>
    edge_anchors?: { index?: number; source_anchor_id?: string; target_anchor_id?: string }[]
  }
  const nodePositions = uiMeta.node_positions ?? {}
  const edgeAnchors = Array.isArray(uiMeta.edge_anchors) ? uiMeta.edge_anchors : []
  const nodes = runtime.nodes.map((n, i) => ({
    ...n,
    ui: {
      position:
        typeof nodePositions[n.id]?.x === 'number' && typeof nodePositions[n.id]?.y === 'number'
          ? { x: Number(nodePositions[n.id]!.x), y: Number(nodePositions[n.id]!.y) }
          : layoutPosition(i),
    },
  }))
  return {
    workflow_id: runtime.workflow_id,
    name: runtime.name,
    version: runtime.version,
    meta: runtime.meta,
    settings: runtime.settings,
    input_schema: runtime.input_schema,
    nodes,
    edges: runtime.edges.map((e, index) => ({
      ...e,
      ui: {
        source_anchor_id:
          typeof edgeAnchors[index]?.source_anchor_id === 'string' && edgeAnchors[index]?.source_anchor_id
            ? edgeAnchors[index]!.source_anchor_id
            : undefined,
        target_anchor_id:
          typeof edgeAnchors[index]?.target_anchor_id === 'string' && edgeAnchors[index]?.target_anchor_id
            ? edgeAnchors[index]!.target_anchor_id
            : undefined,
      },
    })),
  }
}
