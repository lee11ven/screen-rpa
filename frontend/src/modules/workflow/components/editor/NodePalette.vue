<script setup lang="ts">
import { computed } from 'vue'
import type { WfNodeType } from '../../dsl/types'
import { NODE_PRESENT } from '../../dsl/node-present'

const emit = defineEmits<{ add: [type: WfNodeType] }>()

const props = withDefaults(
  defineProps<{
    /** 主流程画布 / 循环体子图 */
    variant?: 'main' | 'loop-inner'
  }>(),
  { variant: 'main' },
)

const DRAG_TYPE = 'application/x-wf-node-type'

type PaletteItem = {
  type: WfNodeType
}

const groupsMain: { title: string; items: PaletteItem[] }[] = [
  {
    title: '内置逻辑',
    items: [{ type: 'start' }, { type: 'end' }, { type: 'if' }, { type: 'loop-container' }],
  },
  {
    title: '执行节点',
    items: [{ type: 'action' }, { type: 'wait' }, { type: 'subflow' }, { type: 'lowcode_function' }],
  },
]

const groupsLoopInner: { title: string; items: PaletteItem[] }[] = [
  {
    title: '循环控制',
    items: [{ type: 'continue' }, { type: 'break' }],
  },
  {
    title: '分支',
    items: [{ type: 'if' }],
  },
  {
    title: '执行节点',
    items: [{ type: 'action' }, { type: 'wait' }, { type: 'subflow' }, { type: 'lowcode_function' }],
  },
]

const groups = computed(() => (props.variant === 'loop-inner' ? groupsLoopInner : groupsMain))

function onDragStart(e: DragEvent, type: WfNodeType) {
  if (!e.dataTransfer) return
  e.dataTransfer.effectAllowed = 'copy'
  e.dataTransfer.setData(DRAG_TYPE, type)
}
</script>

<template>
  <div class="palette">
    <div v-for="g in groups" :key="g.title" class="group">
      <div class="group-title">{{ g.title }}</div>
      <div class="item-list">
        <button
          v-for="it in g.items"
          :key="it.type"
          class="node-item"
          type="button"
          draggable="true"
          @click="emit('add', it.type)"
          @dragstart="onDragStart($event, it.type)"
        >
          <span class="node-icon" :style="{ backgroundColor: NODE_PRESENT[it.type].tint }">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path :d="NODE_PRESENT[it.type].icon" />
            </svg>
          </span>
          <span class="node-name">{{ NODE_PRESENT[it.type].label }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.palette {
  width: 240px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}
.group {
  margin-bottom: 10px;
}
.group-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.item-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.18s ease;
}
.node-item:hover {
  border-color: var(--el-color-primary-light-5);
  transform: translateY(-1px);
}
.node-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.node-icon svg {
  width: 14px;
  height: 14px;
  fill: #444;
}
.node-name {
  font-size: 12px;
}
</style>
