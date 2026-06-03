import { describe, expect, it } from 'vitest'
import { DEFAULT_SETTINGS } from './defaults'
import { normalizeLoopSubGraphEditorWorkflow, subGraphPayloadToEditor } from './loop-subgraph-model'
import type { EditorWorkflow } from './types'

function emptyEditor(): EditorWorkflow {
  return subGraphPayloadToEditor({ nodes: [], edges: [] }, { ...DEFAULT_SETTINGS }, undefined)
}

describe('normalizeLoopSubGraphEditorWorkflow', () => {
  it('补全缺失的 loop_start', () => {
    const wf = emptyEditor()
    expect(wf.nodes.some((n) => n.type === 'loop_start')).toBe(false)
    const next = normalizeLoopSubGraphEditorWorkflow(wf)
    expect(next.nodes.filter((n) => n.type === 'loop_start')).toHaveLength(1)
  })

  it('仅保留一个 loop_start 并去掉相关边', () => {
    const base = normalizeLoopSubGraphEditorWorkflow(emptyEditor())
    const a = base.nodes.find((n) => n.type === 'loop_start')!
    const dupId = 'loop_start_dup'
    const wf: EditorWorkflow = {
      ...base,
      nodes: [
        ...base.nodes,
        {
          id: dupId,
          type: 'loop_start',
          name: 'x',
          config: {},
          ui: { position: { x: 1, y: 1 } },
        },
      ],
      edges: [...base.edges, { from: a.id, to: dupId }],
    }
    const next = normalizeLoopSubGraphEditorWorkflow(wf)
    expect(next.nodes.filter((n) => n.type === 'loop_start')).toHaveLength(1)
    expect(next.nodes.some((n) => n.id === dupId)).toBe(false)
    expect(next.edges.some((e) => e.from === a.id && e.to === dupId)).toBe(false)
  })
})
