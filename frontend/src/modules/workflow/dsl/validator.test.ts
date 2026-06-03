import { describe, expect, it } from 'vitest'
import { validateEditorWorkflow, validateGraphStructure } from './validator'
import type { RuntimeWorkflow } from './types'

function minimal(wf: Partial<RuntimeWorkflow>): RuntimeWorkflow {
  return {
    workflow_id: 'w',
    name: 'n',
    settings: { default_timeout_sec: 1, max_retries: 0, max_loop_iterations: 10 },
    nodes: wf.nodes ?? [],
    edges: wf.edges ?? [],
    ...wf,
  }
}

describe('validateGraphStructure', () => {
  it('requires single start', () => {
    const issues = validateGraphStructure(
      minimal({
        nodes: [
          { id: 's1', type: 'start', name: 'a', config: {} },
          { id: 's2', type: 'start', name: 'b', config: {} },
          { id: 'e', type: 'end', name: 'e', config: {} },
        ],
        edges: [],
      }),
    )
    expect(issues.some((i) => i.message.includes('start'))).toBe(true)
  })

  it('accepts minimal linear graph', () => {
    const issues = validateGraphStructure(
      minimal({
        nodes: [
          { id: 's', type: 'start', name: 's', config: {} },
          { id: 'x', type: 'action', name: 'x', config: {} },
          { id: 'e', type: 'end', name: 'e', config: {} },
        ],
        edges: [
          { from: 's', to: 'x' },
          { from: 'x', to: 'e' },
        ],
      }),
    )
    expect(issues).toEqual([])
  })
})

describe('validateEditorWorkflow', () => {
  it('validates lowcode_function required fields', () => {
    const issues = validateEditorWorkflow({
      workflow_id: 'w',
      name: 'n',
      settings: { default_timeout_sec: 1, max_retries: 0, max_loop_iterations: 10 },
      nodes: [
        { id: 's', type: 'start', name: 's', config: {}, ui: { position: { x: 0, y: 0 } } },
        {
          id: 'l',
          type: 'lowcode_function',
          name: 'low',
          config: { code_body: '', timeout_ms: -1, retry_times: -1 },
          ui: { position: { x: 1, y: 1 } },
        },
        { id: 'e', type: 'end', name: 'e', config: {}, ui: { position: { x: 2, y: 2 } } },
      ],
      edges: [
        { from: 's', to: 'l' },
        { from: 'l', to: 'e' },
      ],
    })
    expect(issues.some((i) => i.message.includes('code_body'))).toBe(true)
    expect(issues.some((i) => i.message.includes('timeout_ms'))).toBe(true)
    expect(issues.some((i) => i.message.includes('retry_times'))).toBe(true)
  })

  it('rejects inner-only nodes on top-level', () => {
    const issues = validateEditorWorkflow({
      workflow_id: 'w',
      name: 'n',
      settings: { default_timeout_sec: 1, max_retries: 0, max_loop_iterations: 10 },
      nodes: [
        { id: 's', type: 'start', name: 's', config: {}, ui: { position: { x: 0, y: 0 } } },
        { id: 'c1', type: 'continue', name: 'c', config: { sleep_ms: 0 }, ui: { position: { x: 1, y: 1 } } },
        { id: 'e', type: 'end', name: 'e', config: {}, ui: { position: { x: 2, y: 2 } } },
      ],
      edges: [
        { from: 's', to: 'c1' },
        { from: 'c1', to: 'e' },
      ],
    })
    expect(issues.some((i) => i.message.includes('只能在 loop-container.subGraph'))).toBe(true)
  })

  it('accepts loop-container with valid subGraph', () => {
    const issues = validateEditorWorkflow({
      workflow_id: 'w',
      name: 'n',
      settings: { default_timeout_sec: 1, max_retries: 0, max_loop_iterations: 10 },
      nodes: [
        { id: 's', type: 'start', name: 's', config: {}, ui: { position: { x: 0, y: 0 } } },
        {
          id: 'lp',
          type: 'loop-container',
          name: 'loop',
          config: {
            loopId: 'loop_1',
            maxIterations: 5,
            subGraph: {
              nodes: [
                { id: 'ls', type: 'loop_start', name: 'ls', config: {} },
                { id: 'ct', type: 'continue', name: 'ct', config: { sleep_ms: 0 } },
              ],
              edges: [{ from: 'ls', to: 'ct' }],
            },
          },
          ui: { position: { x: 1, y: 1 } },
        },
        { id: 'e', type: 'end', name: 'e', config: {}, ui: { position: { x: 2, y: 2 } } },
      ],
      edges: [
        { from: 's', to: 'lp' },
        { from: 'lp', to: 'e' },
      ],
    })
    expect(issues).toEqual([])
  })
})
