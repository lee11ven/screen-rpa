<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import RunLogTable from '../components/run/RunLogTable.vue'
import RunNodeTimeline from '../components/run/RunNodeTimeline.vue'
import RunStatusCard from '../components/run/RunStatusCard.vue'
import { useWorkflowRunStore } from '../stores/workflow-run.store'

const props = defineProps<{ runId: string }>()
const router = useRouter()
const runStore = useWorkflowRunStore()

async function onTerminateRun() {
  if (runStore.status?.status !== 'RUNNING' || runStore.terminating) return
  try {
    await ElMessageBox.confirm(
      '确认要终止当前正在执行的任务吗？终止后当前运行将进入 CANCELLED 状态。',
      '终止确认',
      {
        type: 'warning',
        confirmButtonText: '确认终止',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  await runStore.terminateRun()
  ElMessage.success('已提交终止请求')
}

onMounted(() => {
  void runStore.initRunDetail(props.runId)
})

onUnmounted(() => {
  runStore.dispose()
})
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
            
          <el-button text @click="router.push({ name: 'workflow-list' })">
            <el-icon size="16" style="margin-right: 4px;"><ArrowLeft /></el-icon>
            列表
          </el-button>
          
          <el-button v-if="runStore.polling" size="small" @click="runStore.refresh()">刷新</el-button>
          <el-button
            v-if="runStore.status?.status === 'RUNNING'"
            size="small"
            type="danger"
            :loading="runStore.terminating"
            @click="onTerminateRun"
          >
            终止运行
          </el-button>
          
          
          <span class="muted">{{ runId }}</span>
          
          <div class="card-title">
            运行详情
          </div>
        </div>
      </template>
      <RunStatusCard :status="runStore.status" />
      <RunNodeTimeline
        :status="runStore.status"
        :node-name-map="runStore.nodeNameMap"
        :node-type-map="runStore.nodeTypeMap"
        :graph-node-order="runStore.graphNodeOrder"
      />
      <RunLogTable
        :logs="runStore.logs"
        :node-name-map="runStore.nodeNameMap"
        :has-more="runStore.nextCursor != null"
        @load-more="runStore.fetchMoreLogs"
      />
    </el-card>
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.card-title {
  margin-left: auto;
  font-size: 16px;
  font-weight: 600;
}
.muted {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
