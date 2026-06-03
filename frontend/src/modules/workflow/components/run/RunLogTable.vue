<script setup lang="ts">
import type { RunLogsData } from '../../services/workflow.api'

defineProps<{
  logs: RunLogsData['items']
  nodeNameMap: Record<string, string>
  hasMore: boolean
}>()

const emit = defineEmits<{ loadMore: [] }>()
</script>

<template>
  <el-card shadow="never" class="mt">
    <template #header>日志</template>
    <el-table :data="logs" size="small" stripe max-height="420">
      <el-table-column prop="created_at" label="时间" width="220" />
      <el-table-column prop="level" label="级别" width="80" />
      <el-table-column label="节点" width="180">
        <template #default="{ row }">
          <span>{{ row.node_id ? nodeNameMap[row.node_id] || row.node_id : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="消息" />
    </el-table>
    <div v-if="hasMore" class="more">
      <el-button text type="primary" @click="emit('loadMore')">加载更多</el-button>
    </div>
  </el-card>
</template>

<style scoped>
.mt {
  margin-top: 12px;
}
.more {
  margin-top: 8px;
  text-align: center;
}
</style>
