<template>
  <section class="page" data-module="disease-detail">
    <header class="page-head">
      <div>
        <h2>病害详情</h2>
        <p class="page-desc">详情页只展示后端返回的本条数据，不做任何修改；从这里返回列表不会改动任何处置方案。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

    <article v-if="entry" class="detail-card">
      <div class="detail-title-row">
        <h3>{{ entry.病害编号 }}</h3>
        <span class="status-tag" :class="statusClass(entry.病害状态)">{{ entry.病害状态 }}</span>
      </div>
      <p v-if="entry.病害状态 === CLOSED" class="readonly-note">
        该病害已闭合，可查看但不能再改动；如需复核处置方案请联系管理员。
      </p>

      <dl class="detail-grid">
        <div v-for="field in fields" :key="field" class="detail-item">
          <dt>{{ field }}</dt>
          <dd>
            <template v-if="field === '严重等级'">
              <span :class="severityClass(entry[field])">{{ entry[field] || '—' }}</span>
            </template>
            <template v-else>{{ entry[field] || '—' }}</template>
          </dd>
        </div>
      </dl>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type DiseaseRow = Record<string, string> & { id: number }

const CLOSED = '已闭合'
const fields = ['病害编号', '所属设施', '病害类型', '严重等级', '发现时间', '所在位置', '处置方案', '病害状态']

const route = useRoute()
const router = useRouter()

const entry = ref<DiseaseRow | null>(null)
const errorMessage = ref('')

function statusClass(status: string) {
  if (status === '待处置') return 'tag-pending'
  if (status === '处置中') return 'tag-processing'
  if (status === CLOSED) return 'tag-closed'
  return ''
}

function severityClass(level: string) {
  if (level === '严重') return 'sev-high'
  if (level === '中等') return 'sev-mid'
  if (level === '轻微') return 'sev-low'
  return ''
}

function goBack() {
  void router.push({ name: 'disease' })
}

async function load() {
  errorMessage.value = ''
  const id = String(route.params.id ?? '')
  try {
    const response = await request(`/api/disease/${id}`)
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { detail?: string } | null
      throw new Error(payload?.detail || '病害明细读取失败')
    }
    // 详情页直接使用按编号取回的独立记录，列表/弹窗里的任何临时状态都带不进来。
    entry.value = (await response.json()) as DiseaseRow
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '病害明细读取失败'
  }
}

onMounted(load)
</script>

<style scoped>
.detail-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px 20px;
}
.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.detail-title-row h3 {
  margin: 0;
  font-size: 16px;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;
  margin: 16px 0 0;
}
.detail-item dt {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 2px;
}
.detail-item dd {
  margin: 0;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
