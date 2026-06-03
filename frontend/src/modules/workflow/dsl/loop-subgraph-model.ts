import type { EditorNode, EditorWorkflow, RuntimeEdge, RuntimeNode, RuntimeWorkflow, WorkflowSettings } from './types'
import { compileToRuntime } from './compiler'
import { EDITOR_UI_META_KEY, defaultNodeConfig, editorFromRuntime } from './defaults'

/**
 * 循环体子图编辑态：保证画布数据中有且仅有一个 `loop_start`，
 * 去掉多余的 `loop_start` 及其关联边，缺失时补一个默认节点。
 */
export function normalizeLoopSubGraphEditorWorkflow(wf: EditorWorkflow): EditorWorkflow {
  const starts = wf.nodes.filter((n) => n.type === 'loop_start')
  let nodes = wf.nodes
  let edges = wf.edges
  let changed = false

  if (starts.length > 1) {
    const dropIds = new Set(starts.slice(1).map((s) => s.id))
    nodes = wf.nodes.filter((n) => !dropIds.has(n.id))
    edges = wf.edges.filter((e) => !dropIds.has(e.from) && !dropIds.has(e.to))
    changed = true
  }

  if (!nodes.some((n) => n.type === 'loop_start')) {
    const id = `loop_start_${Math.random().toString(36).slice(2, 9)}`
    const loopStart: EditorNode = {
      id,
      type: 'loop_start',
      name: '循环开始',
      config: defaultNodeConfig('loop_start'),
      ui: { position: { x: 220, y: 200 } },
    }
    nodes = [loopStart, ...nodes]
    changed = true
  }

  return changed ? { ...wf, nodes, edges } : wf
}

/** 将 loop-container.config 中的子图与可选的编辑器 UI 元数据转为可编辑 workflow */
export function subGraphPayloadToEditor(
  subGraph: { nodes: RuntimeNode[]; edges: RuntimeEdge[] },
  settings: WorkflowSettings,
  subGraphEditorUi: Record<string, unknown> | undefined,
): EditorWorkflow {
  const meta =
    subGraphEditorUi && typeof subGraphEditorUi === 'object'
      ? { [EDITOR_UI_META_KEY]: subGraphEditorUi }
      : {}
  const rt: RuntimeWorkflow = {
    workflow_id: '__loop_subgraph_editor__',
    name: '循环体内流程',
    settings: { ...settings },
    nodes: subGraph.nodes.map((n) => ({ ...n })),
    edges: subGraph.edges.map((e) => ({ ...e })),
    meta,
  }
  return editorFromRuntime(rt)
}

/** 将子图编辑器中的模型写回 loop-container.config（runtime 节点边 + 坐标锚点） */
export function editorToLoopSubGraphPayload(wf: EditorWorkflow): {
  subGraph: { nodes: RuntimeNode[]; edges: RuntimeEdge[] }
  subGraph_editor_ui: Record<string, unknown> | undefined
} {
  const rt = compileToRuntime(wf)
  const rawMeta = (rt.meta ?? {}) as Record<string, unknown>
  const ui = rawMeta[EDITOR_UI_META_KEY]
  return {
    subGraph: { nodes: rt.nodes, edges: rt.edges },
    subGraph_editor_ui:
      typeof ui === 'object' && ui !== null && !Array.isArray(ui) ? (ui as Record<string, unknown>) : undefined,
  }
}
