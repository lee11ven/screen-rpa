import type { EditorWorkflow, RuntimeWorkflow } from './types'
import { EDITOR_UI_META_KEY } from './defaults'

/** Editor -> Runtime：移除 ui，浅拷贝节点 */
export function compileToRuntime(editor: EditorWorkflow): RuntimeWorkflow {
  const nodes = editor.nodes.map(({ ui: _ui, ...rest }) => ({ ...rest }))
  const edges = editor.edges.map((e) => ({
    from: e.from,
    to: e.to,
    label: e.label,
    condition: e.condition,
  }))
  const nodePositions: Record<string, { x: number; y: number }> = {}
  for (const n of editor.nodes) {
    nodePositions[n.id] = {
      x: n.ui.position.x,
      y: n.ui.position.y,
    }
  }
  const edgeAnchors = editor.edges.map((e, index) => ({
    index,
    source_anchor_id: e.ui?.source_anchor_id,
    target_anchor_id: e.ui?.target_anchor_id,
  }))
  const nextMeta = { ...(editor.meta ?? {}) } as Record<string, unknown>
  nextMeta[EDITOR_UI_META_KEY] = {
    node_positions: nodePositions,
    edge_anchors: edgeAnchors,
  }
  return {
    workflow_id: editor.workflow_id,
    name: editor.name,
    version: editor.version,
    meta: nextMeta,
    settings: { ...editor.settings },
    input_schema: editor.input_schema,
    nodes,
    edges,
  }
}
