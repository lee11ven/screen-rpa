<script setup lang="ts">
import { ref, watch } from 'vue'

defineOptions({ name: 'TypedDynamicForm' })
const MAX_DEPTH = 5

type ValueType = 'string' | 'number' | 'boolean' | 'object' | 'array'

interface ObjectFieldItem {
  id: string
  key: string
  type: ValueType
  value: unknown
}

interface ArrayFieldItem {
  id: string
  type: ValueType
  value: unknown
}

const props = withDefaults(
  defineProps<{
    modelValue: unknown
    mode?: 'object' | 'array'
    depth?: number
  }>(),
  {
    mode: 'object',
    depth: 0,
  },
)

const emit = defineEmits<{
  'update:modelValue': [unknown]
}>()

function canNest(): boolean {
  return props.depth < MAX_DEPTH - 1
}

function makeId() {
  return `f_${Math.random().toString(36).slice(2, 9)}`
}

function detectType(v: unknown): ValueType {
  if (Array.isArray(v)) return 'array'
  if (v !== null && typeof v === 'object') return 'object'
  if (typeof v === 'number') return 'number'
  if (typeof v === 'boolean') return 'boolean'
  return 'string'
}

function defaultValueForType(type: ValueType): unknown {
  switch (type) {
    case 'number':
      return 0
    case 'boolean':
      return false
    case 'object':
      return {}
    case 'array':
      return []
    default:
      return ''
  }
}

function normalizeByType(type: ValueType, raw: unknown): unknown {
  switch (type) {
    case 'string':
      return String(raw ?? '')
    case 'number': {
      const n = Number(raw)
      return Number.isFinite(n) ? n : 0
    }
    case 'boolean':
      return Boolean(raw)
    case 'object':
      return raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {}
    case 'array':
      return Array.isArray(raw) ? raw : []
    default:
      return raw
  }
}

function emitObject(items: ObjectFieldItem[]) {
  const out: Record<string, unknown> = {}
  for (const item of items) {
    const key = item.key.trim()
    out[key] = normalizeByType(item.type, item.value)
  }
  emit('update:modelValue', out)
}

function emitArray(items: ArrayFieldItem[]) {
  const out = items.map((item) => normalizeByType(item.type, item.value))
  emit('update:modelValue', out)
}

const objectItems = ref<ObjectFieldItem[]>([])
const arrayItems = ref<ArrayFieldItem[]>([])

function syncObjectItemsFromModel(v: unknown) {
  if (props.mode !== 'object') return
  const obj = v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
  const oldByKey = new Map(objectItems.value.map((x) => [x.key, x]))
  objectItems.value = Object.entries(obj).map(([key, value]) => {
    const old = oldByKey.get(key)
    return {
      id: old?.id ?? makeId(),
      key,
      type: detectType(value),
      value,
    }
  })
}

function syncArrayItemsFromModel(v: unknown) {
  if (props.mode !== 'array') return
  const arr = Array.isArray(v) ? v : []
  arrayItems.value = arr.map((value, idx) => ({
    id: arrayItems.value[idx]?.id ?? makeId(),
    type: detectType(value),
    value,
  }))
}

watch(
  () => props.modelValue,
  (v) => {
    syncObjectItemsFromModel(v)
    syncArrayItemsFromModel(v)
  },
  { immediate: true, deep: true },
)

function addObjectField() {
  const used = new Set(objectItems.value.map((x) => x.key.trim()).filter(Boolean))
  let idx = used.size + 1
  let nextKey = `field_${idx}`
  while (used.has(nextKey)) {
    idx += 1
    nextKey = `field_${idx}`
  }
  const next = [...objectItems.value, { id: makeId(), key: nextKey, type: 'string' as ValueType, value: '' }]
  objectItems.value = next
  emitObject(next)
}

function removeObjectField(id: string) {
  const next = objectItems.value.filter((x) => x.id !== id)
  objectItems.value = next
  emitObject(next)
}

function updateObjectField(id: string, patch: Partial<ObjectFieldItem>) {
  const next = objectItems.value.map((x) => {
    if (x.id !== id) return x
    const merged = { ...x, ...patch }
    if (!canNest() && (merged.type === 'object' || merged.type === 'array')) {
      merged.type = 'string'
    }
    if (patch.type) merged.value = defaultValueForType(patch.type)
    if (!canNest() && (patch.type === 'object' || patch.type === 'array')) {
      merged.value = ''
    }
    return merged
  })
  objectItems.value = next
  emitObject(next)
}

function addArrayField() {
  const next = [...arrayItems.value, { id: makeId(), type: 'string' as ValueType, value: '' }]
  arrayItems.value = next
  emitArray(next)
}

function removeArrayField(id: string) {
  const next = arrayItems.value.filter((x) => x.id !== id)
  arrayItems.value = next
  emitArray(next)
}

function updateArrayField(id: string, patch: Partial<ArrayFieldItem>) {
  const next = arrayItems.value.map((x) => {
    if (x.id !== id) return x
    const merged = { ...x, ...patch }
    if (!canNest() && (merged.type === 'object' || merged.type === 'array')) {
      merged.type = 'string'
    }
    if (patch.type) merged.value = defaultValueForType(patch.type)
    if (!canNest() && (patch.type === 'object' || patch.type === 'array')) {
      merged.value = ''
    }
    return merged
  })
  arrayItems.value = next
  emitArray(next)
}

function onObjectKeyChange(id: string, v: unknown) {
  updateObjectField(id, { key: String(v ?? '') })
}

function onObjectTypeChange(id: string, v: unknown) {
  updateObjectField(id, { type: v as ValueType })
}

function onObjectStringChange(id: string, v: unknown) {
  updateObjectField(id, { value: String(v ?? '') })
}

function onObjectNumberChange(id: string, v: unknown) {
  updateObjectField(id, { value: Number(v ?? 0) })
}

function onObjectBooleanChange(id: string, v: unknown) {
  updateObjectField(id, { value: Boolean(v) })
}

function onArrayTypeChange(id: string, v: unknown) {
  updateArrayField(id, { type: v as ValueType })
}

function onArrayStringChange(id: string, v: unknown) {
  updateArrayField(id, { value: String(v ?? '') })
}

function onArrayNumberChange(id: string, v: unknown) {
  updateArrayField(id, { value: Number(v ?? 0) })
}

function onArrayBooleanChange(id: string, v: unknown) {
  updateArrayField(id, { value: Boolean(v) })
}
</script>

<template>
  <div class="typed-form" :class="`depth-${depth}`">
    <template v-if="mode === 'object'">
      <div class="typed-form-head">
        <span class="typed-form-head-title">Object</span>
        <span class="typed-form-head-sub">层级 {{ depth + 1 }}</span>
      </div>
      <div v-for="item in objectItems" :key="item.id" class="typed-form-row">
        <el-input
          class="key-input"
          :model-value="item.key"
          placeholder="键名"
          @update:model-value="onObjectKeyChange(item.id, $event)"
        />
        <el-select
          class="type-select"
          :model-value="item.type"
          @update:model-value="onObjectTypeChange(item.id, $event)"
        >
          <el-option label="string" value="string" />
          <el-option label="number" value="number" />
          <el-option label="boolean" value="boolean" />
          <el-option label="object" value="object" :disabled="!canNest()" />
          <el-option label="array" value="array" :disabled="!canNest()" />
        </el-select>
        <div class="value-wrap">
          <el-input
            v-if="item.type === 'string'"
            :model-value="String(item.value ?? '')"
            placeholder="字符串值"
            @update:model-value="onObjectStringChange(item.id, $event)"
          />
          <el-input-number
            v-else-if="item.type === 'number'"
            :model-value="Number(item.value ?? 0)"
            @update:model-value="onObjectNumberChange(item.id, $event)"
          />
          <el-switch
            v-else-if="item.type === 'boolean'"
            :model-value="Boolean(item.value)"
            @update:model-value="onObjectBooleanChange(item.id, $event)"
          />
          <TypedDynamicForm
            v-else-if="item.type === 'object'"
            :model-value="item.value"
            mode="object"
            :depth="depth + 1"
            @update:model-value="(v) => updateObjectField(item.id, { value: v })"
          />
          <TypedDynamicForm
            v-else
            :model-value="item.value"
            mode="array"
            :depth="depth + 1"
            @update:model-value="(v) => updateObjectField(item.id, { value: v })"
          />
        </div>
        <el-button text type="danger" @click="removeObjectField(item.id)">删除</el-button>
      </div>
      <el-button size="small" class="add-btn" @click="addObjectField">添加字段</el-button>
    </template>

    <template v-else>
      <div class="typed-form-head">
        <span class="typed-form-head-title">Array</span>
        <span class="typed-form-head-sub">层级 {{ depth + 1 }}</span>
      </div>
      <div v-for="item in arrayItems" :key="item.id" class="typed-form-row array-row">
        <el-select
          class="type-select"
          :model-value="item.type"
          @update:model-value="onArrayTypeChange(item.id, $event)"
        >
          <el-option label="string" value="string" />
          <el-option label="number" value="number" />
          <el-option label="boolean" value="boolean" />
          <el-option label="object" value="object" :disabled="!canNest()" />
          <el-option label="array" value="array" :disabled="!canNest()" />
        </el-select>
        <div class="value-wrap">
          <el-input
            v-if="item.type === 'string'"
            :model-value="String(item.value ?? '')"
            placeholder="字符串值"
            @update:model-value="onArrayStringChange(item.id, $event)"
          />
          <el-input-number
            v-else-if="item.type === 'number'"
            :model-value="Number(item.value ?? 0)"
            @update:model-value="onArrayNumberChange(item.id, $event)"
          />
          <el-switch
            v-else-if="item.type === 'boolean'"
            :model-value="Boolean(item.value)"
            @update:model-value="onArrayBooleanChange(item.id, $event)"
          />
          <TypedDynamicForm
            v-else-if="item.type === 'object'"
            :model-value="item.value"
            mode="object"
            :depth="depth + 1"
            @update:model-value="(v) => updateArrayField(item.id, { value: v })"
          />
          <TypedDynamicForm
            v-else
            :model-value="item.value"
            mode="array"
            :depth="depth + 1"
            @update:model-value="(v) => updateArrayField(item.id, { value: v })"
          />
        </div>
        <el-button text type="danger" @click="removeArrayField(item.id)">删除</el-button>
      </div>
      <el-button size="small" class="add-btn" @click="addArrayField">添加元素</el-button>
    </template>
  </div>
</template>

<style scoped>
.typed-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
}

.typed-form-row {
  display: grid;
  grid-template-columns: 120px 110px minmax(0, 1fr) 56px;
  gap: 8px;
  align-items: start;
}

.typed-form-row.array-row {
  grid-template-columns: 110px minmax(0, 1fr) 56px;
}

.value-wrap {
  min-width: 0;
}

.typed-form-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}

.typed-form-head-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.typed-form-head-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.add-btn {
  justify-self: start;
}

.depth-0 {
  margin-top: 2px;
  background: #f6f8ff;
}

.depth-1 {
  background: #f4fbf7;
  border-color: #d7efe1;
}

.depth-2 {
  background: #fff9f2;
  border-color: #f3e3c9;
}

.depth-3 {
  background: #f8f8f8;
  border-color: #e4e4e4;
}

.typed-form[class*='depth-'] .typed-form-row {
  padding: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}
</style>
