<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import * as workflowApi from '../services/workflow.api'

const router = useRouter()
const state = reactive({
  loading: false,
  queueStatus: '',
  workflowId: '',
  runId: '',
  limit: 100,
  items: [] as workflowApi.QueueListItem[],
})

async function load() {
  state.loading = true
  try {
    const r = await workflowApi.listQueueRecords({
      queue_status: state.queueStatus || undefined,
      workflow_id: state.workflowId || undefined,
      run_id: state.runId || undefined,
      limit: state.limit,
    })
    state.items = r.items
  } finally {
    state.loading = false
  }
}

onMounted(load)

function openRunDetail(runId: string) {
  void router.push({ name: 'workflow-run', params: { runId } })
}
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">运行队列</div>
      </template>
      <div class="bar">
        <el-select v-model="state.queueStatus" clearable placeholder="队列状态" style="width: 180px">
          <el-option label="ENQUEUED" value="ENQUEUED" />
          <el-option label="DEQUEUED" value="DEQUEUED" />
          <el-option label="RETRY_WAIT" value="RETRY_WAIT" />
          <el-option label="DONE" value="DONE" />
          <el-option label="DEAD" value="DEAD" />
        </el-select>
        <el-input v-model="state.workflowId" placeholder="workflow_id" clearable style="width: 220px" />
        <el-input v-model="state.runId" placeholder="run_id" clearable style="width: 220px" />
        <el-input-number v-model="state.limit" :min="1" :max="500" />
        <el-button type="primary" @click="load">查询</el-button>
      </div>

      <el-table v-loading="state.loading" border :data="state.items" max-height="680" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="queue_status" label="队列状态" width="120" />
        <el-table-column prop="workflow_name" label="流程名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="workflow_id" label="Workflow ID" min-width="160" show-overflow-tooltip />
        <el-table-column prop="run_id" label="Run ID" min-width="180" show-overflow-tooltip />
        <el-table-column prop="run_status" label="运行状态" width="100" />
        <el-table-column prop="retry_count" label="重试次数" width="90" />
        <el-table-column prop="message_id" label="Message ID" min-width="220" show-overflow-tooltip />
        <el-table-column prop="available_at" label="可执行时间" min-width="160" show-overflow-tooltip />
        <el-table-column prop="dequeued_at" label="出队时间" min-width="160" show-overflow-tooltip />
        <el-table-column prop="done_at" label="完成时间" min-width="160" show-overflow-tooltip />
        <el-table-column prop="dead_at" label="死亡时间" min-width="160" show-overflow-tooltip />
        <el-table-column prop="fail_reason" label="失败原因" min-width="200" show-overflow-tooltip />
        <el-table-column prop="updated_at" label="更新时间" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openRunDetail(row.run_id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}

.bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

:deep(.el-table .cell) {
  white-space: nowrap;
}
</style>
