<script setup lang="ts">
import { computed } from 'vue'
import type { RunStatusData } from '../../services/workflow.api'

const props = defineProps<{
  status: RunStatusData | null
  nodeNameMap: Record<string, string>
  nodeTypeMap: Record<string, string>
  /** 与 DSL 中从 start 沿边顺序一致；有值时时间线不按时戳重排，避免轮询时跳动 */
  graphNodeOrder: string[] | null
}>()

function toTime(value: string | null | undefined) {
  if (!value) return Number.POSITIVE_INFINITY
  const normalized = value.includes(' ') ? value.replace(' ', 'T') : value
  const ms = Date.parse(normalized)
  return Number.isNaN(ms) ? Number.POSITIVE_INFINITY : ms
}

function pinStartAndEnd(nodes: RunStatusData['nodes']) {
  const starts: RunStatusData['nodes'] = []
  const middles: RunStatusData['nodes'] = []
  const ends: RunStatusData['nodes'] = []
  for (const n of nodes) {
    const nodeType = props.nodeTypeMap[n.node_id]
    if (nodeType === 'start') {
      starts.push(n)
      continue
    }
    if (nodeType === 'end') {
      ends.push(n)
      continue
    }
    middles.push(n)
  }
  return [...starts, ...middles, ...ends]
}

const sortedNodes = computed(() => {
  if (!props.status) return []
  const byId = new Map(props.status.nodes.map((n) => [n.node_id, n]))
  const order = props.graphNodeOrder
  if (order?.length) {
    const out: RunStatusData['nodes'] = []
    const used = new Set<string>()
    for (const id of order) {
      const n = byId.get(id)
      if (n) {
        out.push(n)
        used.add(n.node_id)
      }
    }
    for (const n of props.status.nodes) {
      if (!used.has(n.node_id)) {
        out.push(n)
      }
    }
    return pinStartAndEnd(out)
  }
  const byTime = [...props.status.nodes].sort((a, b) => {
    const aStart = toTime(a.started_at)
    const bStart = toTime(b.started_at)
    if (aStart !== bStart) return aStart - bStart

    const aFinish = toTime(a.finished_at)
    const bFinish = toTime(b.finished_at)
    return aFinish - bFinish
  })
  return pinStartAndEnd(byTime)
})

function tagType(st: string) {
  if (st === 'SUCCESS') return 'success'
  if (st === 'FAILED' || st === 'TIMEOUT') return 'danger'
  if (st === 'RUNNING') return 'primary'
  if (st === 'SKIPPED') return 'info'
  return ''
}

function formatNodeName(node: RunStatusData['nodes'][number]) {
  const fromStatus = (node.node_name ?? '').trim()
  if (fromStatus) return fromStatus
  return props.nodeNameMap[node.node_id] || node.node_id
}
</script>

<template>
  <el-card v-if="status" shadow="never" class="mt">
    <template #header>节点时间线</template>
    <el-timeline>
      <el-timeline-item
        v-for="n in sortedNodes"
        :key="n.node_id"
        :type="tagType(n.status)"
        :timestamp="`${n.started_at ?? ''} → ${n.finished_at ?? ''}`"
        placement="top"
      >
        <div class="row">
          <strong>{{ formatNodeName(n) }}</strong>
          <el-tag size="small" :type="tagType(n.status)">{{ n.status }}</el-tag>
        </div>
        <div v-if="n.error_code" class="err">{{ n.error_code }}</div>
      </el-timeline-item>
    </el-timeline>
  </el-card>
</template>

<style scoped>
.mt {
  margin-top: 12px;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.err {
  font-size: 12px;
  color: var(--el-color-danger);
  margin-top: 4px;
}
</style>
