import { describe, expect, it } from 'vitest'
import { compileToRuntime } from './compiler'
import type { EditorWorkflow } from './types'

const sample: EditorWorkflow = {
  workflow_id: 'wf_t',
  name: 't',
  settings: { default_timeout_sec: 1, max_retries: 0, max_loop_iterations: 10 },
  nodes: [
    {
      id: 'a',
      type: 'start',
      name: 's',
      config: {},
      ui: { position: { x: 1, y: 2 } },
    },
    {
      id: 'b',
      type: 'end',
      name: 'e',
      config: {},
      ui: { position: { x: 3, y: 4 } },
    },
  ],
  edges: [{ from: 'a', to: 'b' }],
}

describe('compileToRuntime', () => {
  it('strips ui from nodes', () => {
    const rt = compileToRuntime(sample)
    expect(rt.nodes[0]).not.toHaveProperty('ui')
    expect(rt.nodes[0]?.id).toBe('a')
  })

  it('keeps loop-container subGraph config', () => {
    const editor: EditorWorkflow = {
      ...sample,
      nodes: [
        sample.nodes[0]!,
        {
          id: 'lp',
          type: 'loop-container',
          name: 'loop',
          config: {
            loopId: 'loop_1',
            maxIterations: 5,
            subGraph: {
              nodes: [{ id: 'ls', type: 'loop_start', name: 'loop_start', config: {} }],
              edges: [],
            },
          },
          ui: { position: { x: 20, y: 30 } },
        },
        sample.nodes[1]!,
      ],
      edges: [
        { from: 'a', to: 'lp' },
        { from: 'lp', to: 'b' },
      ],
    }
    const rt = compileToRuntime(editor)
    expect((rt.nodes[1]!.config as Record<string, unknown>).subGraph).toBeTruthy()
  })
})
