<script setup lang="ts">
import type { RunStatusData } from '../../services/workflow.api'

defineProps<{
  status: RunStatusData | null
}>()

function tagType(status: string) {
  if (status === 'SUCCESS') return 'success'
  if (status === 'FAILED') return 'danger'
  if (status === 'RUNNING'|| status === 'QUEUED') return 'primary'
  if (status === 'SKIPPED') return 'info'
  if (status === 'TIMEOUT' || status === 'CANCELLED') return 'warning'
  return 'info'
}
</script>

<template>
  <el-card v-if="status" shadow="never">
    <template #header>运行概览</template>
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="run_id">{{ status.run_id }}</el-descriptions-item>
      <el-descriptions-item label="workflow">{{ status.workflow_id }}</el-descriptions-item>
      <el-descriptions-item label="版本">{{ status.workflow_version }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="tagType(status.status)">{{ status.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="开始">{{ status.started_at ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="结束">{{ status.finished_at ?? '-' }}</el-descriptions-item>
      <el-descriptions-item v-if="status.error_message" label="错误" :span="2">
        {{ status.error_message }}
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>
