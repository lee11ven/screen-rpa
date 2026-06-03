import type { WfNodeType } from './types'

export interface NodePresent {
  label: string
  icon: string
  tint: string
}

export const NODE_PRESENT: Record<WfNodeType, NodePresent> = {
  start: { label: '开始', icon: 'M8 4v8l6-4z', tint: '#ecfdf3' },
  end: { label: '结束', icon: 'M5 5h6v6H5z', tint: '#fff1f2' },
  if: { label: '条件', icon: 'M8 3l5 5-5 5-5-5z', tint: '#fff8e6' },
  action: { label: '动作', icon: 'M4 4h8v8H4z', tint: '#eff6ff' },
  wait: { label: '等待', icon: 'M8 3a5 5 0 100 10A5 5 0 008 3zm.5 2v3.2l2.2 1.3-.7 1.2L7 8.9V5h1.5z', tint: '#e6fffb' },
  subflow: { label: '子流程', icon: 'M4 5h8v2H4zm0 4h6v2H4z', tint: '#f5f3ff' },
  lowcode_function: { label: '低代码函数', icon: 'M3 4h10v2H3zm0 3h10v2H3zm0 3h6v2H3z', tint: '#fff7e6' },
  'loop-container': { label: '循环体', icon: 'M8 2.5a5.5 5.5 0 014.8 2.8l1.2-.1-1.8 3-3-1.8 1.2-.1A4.2 4.2 0 108 12.2v1.3A5.5 5.5 0 018 2.5zm0 11a5.5 5.5 0 01-4.8-2.8l-1.2.1 1.8-3 3 1.8-1.2.1A4.2 4.2 0 108 3.8V2.5a5.5 5.5 0 010 11z', tint: '#ecfeff' },
  loop_start: { label: '循环开始', icon: 'M8 4v8l6-4z', tint: '#f0fdf4' },
  continue: { label: '继续', icon: 'M8 2.5a5.5 5.5 0 00-5.2 3.7H1.5l2.4 2.9 2.4-2.9H4.4A4 4 0 118 12v1.5a5.5 5.5 0 100-11z', tint: '#f0f9ff' },
  break: { label: '跳出', icon: 'M4 4h8v8H4zm2 2v4h4V6z', tint: '#fff1f2' },
}

