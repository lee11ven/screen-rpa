import LogicFlow, {
  CircleNode,
  CircleNodeModel,
  DiamondNode,
  DiamondNodeModel,
  RectNode,
  RectNodeModel,
} from '@logicflow/core'
import type { WfNodeType } from '../dsl/types'
import { createElement as h } from 'preact/compat'
import { NODE_PRESENT } from '../dsl/node-present'

const RECT_TYPES: WfNodeType[] = [
  'action',
  'wait',
  'subflow',
  'lowcode_function',
  'loop-container',
  'loop_start',
  'continue',
  'break',
]

const PALETTE: Partial<Record<WfNodeType, { fill: string; stroke: string }>> = {
  action: { fill: '#e6f4ff', stroke: '#1677ff' },
  wait: { fill: '#e6fffb', stroke: '#13c2c2' },
  subflow: { fill: '#f9f0ff', stroke: '#722ed1' },
  lowcode_function: { fill: '#fff7e6', stroke: '#d48806' },
  'loop-container': { fill: '#e6fffb', stroke: '#08979c' },
  loop_start: { fill: '#f0fdf4', stroke: '#389e0d' },
  continue: { fill: '#f0f9ff', stroke: '#1677ff' },
  break: { fill: '#fff1f2', stroke: '#cf1322' },
}

const ICON_SCALE = 2
const BASE_ICON_SIZE = 16
const ICON_SIZE = BASE_ICON_SIZE * ICON_SCALE
const SELECTED_DASH_STYLE = {
  stroke: '#8c8c8c',
  strokeDasharray: '4 4',
  strokeWidth: 2,
}

function isOutAnchor(anchorId?: string) {
  return !!anchorId && anchorId.endsWith('_out')
}

function isInAnchor(anchorId?: string) {
  return !!anchorId && anchorId.endsWith('_in')
}

function registerRectWf(lf: LogicFlow, wfType: WfNodeType) {
  const colors = PALETTE[wfType] ?? { fill: '#fafafa', stroke: '#595959' }
  const present = NODE_PRESENT[wfType]
  class M extends RectNodeModel {
    setAttributes() {
      super.setAttributes()
      this.width = 148
      this.height = 60
    }
    getDefaultAnchor() {
      if (wfType === 'loop_start') {
        return [{ id: `${this.id}_out`, x: this.x + this.width / 2, y: this.y }]
      }
      if (wfType === 'continue' || wfType === 'break') {
        return [{ id: `${this.id}_in`, x: this.x - this.width / 2, y: this.y }]
      }
      return [
        { id: `${this.id}_in`, x: this.x - this.width / 2, y: this.y },
        { id: `${this.id}_out`, x: this.x + this.width / 2, y: this.y },
      ]
    }
    isAllowConnectedAsSource(...args: Parameters<RectNodeModel['isAllowConnectedAsSource']>) {
      const sourceAnchor = args[1]
      if (!isOutAnchor(sourceAnchor?.id)) {
        return { isAllPass: false, msg: '起点必须使用出边锚点' }
      }
      return super.isAllowConnectedAsSource(...args)
    }
    isAllowConnectedAsTarget(...args: Parameters<RectNodeModel['isAllowConnectedAsTarget']>) {
      const targetAnchor = args[2]
      if (!isInAnchor(targetAnchor?.id)) {
        return { isAllPass: false, msg: '终点必须使用入边锚点' }
      }
      return super.isAllowConnectedAsTarget(...args)
    }
    getNodeStyle() {
      const st = super.getNodeStyle()
      return this.isSelected ? { ...st, ...colors, ...SELECTED_DASH_STYLE } : { ...st, ...colors }
    }
    getTextStyle() {
      const style = super.getTextStyle()
      return {
        ...style,
        y: this.y + this.height / 2 - 10,
      }
    }
  }
  class V extends RectNode {
    getShape() {
      const shape = super.getShape()
      const model = this.props.model
      const iconY = model.y - model.height / 2 + 8
      return h('g', {}, [
        shape,
        h('svg', { x: model.x - ICON_SIZE / 2, y: iconY, width: ICON_SIZE, height: ICON_SIZE, viewBox: '0 0 16 16' }, [
          h('path', { d: present.icon, fill: '#444' }),
        ]),
      ])
    }
  }
  lf.register({ type: `wf-${wfType}`, view: V, model: M })
}

function registerCircleWf(lf: LogicFlow, wfType: 'start' | 'end') {
  const colors =
    wfType === 'start'
      ? { fill: '#d9f7be', stroke: '#389e0d' }
      : { fill: '#ffccc7', stroke: '#cf1322' }
  const present = NODE_PRESENT[wfType]
  class M extends CircleNodeModel {
    setAttributes() {
      super.setAttributes()
      this.r = 30
    }
    getDefaultAnchor() {
      if (wfType === 'start') {
        return [{ id: `${this.id}_out`, x: this.x + this.r, y: this.y }]
      }
      return [{ id: `${this.id}_in`, x: this.x - this.r, y: this.y }]
    }
    isAllowConnectedAsSource(...args: Parameters<CircleNodeModel['isAllowConnectedAsSource']>) {
      const sourceAnchor = args[1]
      if (!isOutAnchor(sourceAnchor?.id)) {
        return { isAllPass: false, msg: '起点必须使用出边锚点' }
      }
      return super.isAllowConnectedAsSource(...args)
    }
    isAllowConnectedAsTarget(...args: Parameters<CircleNodeModel['isAllowConnectedAsTarget']>) {
      const targetAnchor = args[2]
      if (!isInAnchor(targetAnchor?.id)) {
        return { isAllPass: false, msg: '终点必须使用入边锚点' }
      }
      return super.isAllowConnectedAsTarget(...args)
    }
    getNodeStyle() {
      const st = super.getNodeStyle()
      return this.isSelected ? { ...st, ...colors, ...SELECTED_DASH_STYLE } : { ...st, ...colors }
    }
    getTextStyle() {
      const style = super.getTextStyle()
      return {
        ...style,
        y: this.y + this.r - 16,
      }
    }
  }
  class V extends CircleNode {
    getShape() {
      const shape = super.getShape()
      const model = this.props.model
      const iconY = model.y - model.r + 10
      const iconPathTransform = wfType === 'start' ? 'translate(-3, 0)' : undefined
      return h('g', {}, [
        shape,
        h('svg', { x: model.x - ICON_SIZE / 2, y: iconY, width: ICON_SIZE, height: ICON_SIZE, viewBox: '0 0 16 16' }, [
          h('path', { d: present.icon, fill: '#444', transform: iconPathTransform }),
        ]),
      ])
    }
  }
  lf.register({ type: `wf-${wfType}`, view: V, model: M })
}

function registerIf(lf: LogicFlow) {
  const colors = { fill: '#fff1b8', stroke: '#d4b106' }
  const present = NODE_PRESENT.if
  class M extends DiamondNodeModel {
    setAttributes() {
      super.setAttributes()
      this.rx = 72
      this.ry = 30
    }
    getDefaultAnchor() {
      return [
        { id: `${this.id}_in`, x: this.x - this.rx, y: this.y },
        { id: `${this.id}_out`, x: this.x + this.rx, y: this.y },
      ]
    }
    isAllowConnectedAsSource(...args: Parameters<DiamondNodeModel['isAllowConnectedAsSource']>) {
      const sourceAnchor = args[1]
      if (!isOutAnchor(sourceAnchor?.id)) {
        return { isAllPass: false, msg: '起点必须使用出边锚点' }
      }
      return super.isAllowConnectedAsSource(...args)
    }
    isAllowConnectedAsTarget(...args: Parameters<DiamondNodeModel['isAllowConnectedAsTarget']>) {
      const targetAnchor = args[2]
      if (!isInAnchor(targetAnchor?.id)) {
        return { isAllPass: false, msg: '终点必须使用入边锚点' }
      }
      return super.isAllowConnectedAsTarget(...args)
    }
    getNodeStyle() {
      const st = super.getNodeStyle()
      return this.isSelected ? { ...st, ...colors, ...SELECTED_DASH_STYLE } : { ...st, ...colors }
    }
    getTextStyle() {
      const style = super.getTextStyle()
      return {
        ...style,
        y: this.y + this.ry - 16,
      }
    }
  }
  class V extends DiamondNode {
    getShape() {
      const shape = super.getShape()
      const model = this.props.model
      const iconY = model.y - model.ry + 10
      return h('g', {}, [
        shape,
        h('svg', { x: model.x - ICON_SIZE / 2, y: iconY, width: ICON_SIZE, height: ICON_SIZE, viewBox: '0 0 16 16' }, [
          h('path', { d: present.icon, fill: '#444' }),
        ]),
      ])
    }
  }
  lf.register({ type: 'wf-if', view: V, model: M })
}

export function registerWorkflowNodes(lf: LogicFlow) {
  for (const t of RECT_TYPES) registerRectWf(lf, t)
  registerCircleWf(lf, 'start')
  registerCircleWf(lf, 'end')
  registerIf(lf)
}

export function lfTypeFor(runtimeType: WfNodeType): string {
  return `wf-${runtimeType}`
}
