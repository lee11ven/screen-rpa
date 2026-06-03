<script setup lang="ts">
import { useWorkflowEditorStore } from '../../stores/workflow-editor.store'

const store = useWorkflowEditorStore()
</script>

<template>
  <div class="panel">
    <div class="head">校验结果</div>
    <el-empty v-if="store.allIssues.length === 0" description="暂无问题" />
    <el-scrollbar v-else max-height="360px">
      <ul class="list">
        <li
          v-for="(it, i) in store.allIssues"
          :key="i"
          class="item"
          @click="store.focusIssue(it)"
        >
          <span v-if="it.node_id" class="nid">{{ it.node_id }}</span>
          <span class="msg">{{ it.message }}</span>
          <span class="path">{{ it.path }}</span>
        </li>
      </ul>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.panel {
  width: 280px;
  padding: 8px;
  background: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}
.head {
  font-weight: 600;
  margin-bottom: 8px;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.item {
  cursor: pointer;
  padding: 6px 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
}
.item:hover {
  background: var(--el-fill-color-light);
}
.nid {
  display: block;
  color: var(--el-color-primary);
  font-weight: 500;
}
.msg {
  color: var(--el-text-color-primary);
}
.path {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
</style>
