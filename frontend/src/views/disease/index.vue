<template>
  <section class="page" data-module="disease">
    <header class="page-head">
      <div>
        <h2>病害记录管理</h2>
        <p class="page-desc">围绕病害编号做登记、定级、实施处置与闭合；严重等级、处置方案、病害状态分开保存，只落在各自编号下。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记病害</button>
        <button class="btn" type="button" @click="exportRows">导出病害记录清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>病害编号</span>
        <input v-model="keyword" placeholder="按病害编号检索" />
      </label>
      <label class="filter-item">
        <span>病害状态</span>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">详情</button>
            <button v-if="!isClosed(row)" class="link" type="button" @click="openDisposal(row)">实施处置</button>
            <button v-if="row['病害状态'] === '处置中'" class="link" type="button" @click="closeEntry(row)">闭合</button>
            <span v-if="isClosed(row)" class="muted-text">已闭合·仅查看</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无病害记录数据，可先登记病害</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条病害记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <!-- 详情弹窗：按 id 实时拉取，与列表、处置弹窗保持同一结论 -->
    <div v-if="detailEntry" class="dialog-mask" @click.self="closeDetail">
      <div class="dialog">
        <h3 class="dialog-title">病害详情 · {{ detailEntry['病害编号'] }}</h3>
        <dl class="detail-grid">
          <template v-for="column in columns" :key="column">
            <dt>{{ column }}</dt>
            <dd>{{ detailEntry[column] || '—' }}</dd>
          </template>
        </dl>
        <p v-if="isClosed(detailEntry)" class="muted-text">该病害已闭合，仅供查看，不能再修改等级、方案或状态。</p>
        <div class="dialog-actions">
          <button v-if="!isClosed(detailEntry)" class="btn primary" type="button" @click="openDisposal(detailEntry)">实施处置</button>
          <button v-if="detailEntry['病害状态'] === '处置中'" class="btn" type="button" @click="closeEntry(detailEntry)">闭合</button>
          <button class="btn ghost" type="button" @click="closeDetail">返回列表</button>
        </div>
      </div>
    </div>

    <!-- 处置弹窗：严重等级与处置方案只保存到当前病害编号 -->
    <div v-if="disposalTarget" class="dialog-mask" @click.self="cancelDisposal">
      <form class="dialog" @submit.prevent="submitDisposal">
        <h3 class="dialog-title">实施处置 · {{ disposalTarget['病害编号'] }}</h3>
        <label class="form-item">
          <span>严重等级</span>
          <select v-model="disposalForm.severity" required>
            <option value="" disabled>请选择严重等级</option>
            <option v-for="level in severityLevels" :key="level" :value="level">{{ level }}</option>
          </select>
        </label>
        <label class="form-item">
          <span>所在位置（为空将无法闭合，可在此补录）</span>
          <input v-model="disposalForm.location" placeholder="如 K3+850 左幅行车道" />
        </label>
        <label class="form-item">
          <span>处置方案</span>
          <textarea v-model="disposalForm.plan" rows="4" placeholder="填写该条病害编号下的处置方案"></textarea>
        </label>
        <p v-if="disposalError" class="error-text">{{ disposalError }}</p>
        <div class="dialog-actions">
          <button class="btn primary" type="submit" :disabled="saving">保存并实施处置</button>
          <button class="btn ghost" type="button" @click="cancelDisposal">取消</button>
        </div>
      </form>
    </div>

    <!-- 登记弹窗 -->
    <div v-if="createOpen" class="dialog-mask" @click.self="cancelCreate">
      <form class="dialog" @submit.prevent="submitCreate">
        <h3 class="dialog-title">登记病害</h3>
        <label v-for="field in createFields" :key="field.name" class="form-item">
          <span>{{ field.name }}<em v-if="field.required" class="required-mark">*</em></span>
          <input
            v-model="createForm[field.name]"
            :placeholder="field.required ? `必填，请输入${field.name}` : `选填，请输入${field.name}`"
          />
        </label>
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <div class="dialog-actions">
          <button class="btn primary" type="submit" :disabled="saving">保存登记</button>
          <button class="btn ghost" type="button" @click="cancelCreate">取消</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/disease'
const columns = ["病害编号", "所属设施", "病害类型", "严重等级", "发现时间", "所在位置", "处置方案", "病害状态"]
const statuses = ["待处置", "处置中", "已闭合"]
const severityLevels = ["轻微", "一般", "严重"]
const CLOSED_STATUS = '已闭合'

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref('')
const statusFilter = ref('')
const stats = ref([
  { label: '待处置病害', value: 0 },
  { label: '处置中病害', value: 0 },
  { label: '已闭合病害', value: 0 },
])

const detailEntry = ref<Row | null>(null)
const disposalTarget = ref<Row | null>(null)
const disposalForm = ref({ severity: '', location: '', plan: '' })
const disposalError = ref('')
const createOpen = ref(false)
const createForm = ref<Record<string, string>>({})
const createError = ref('')
const saving = ref(false)

const createFields = [
  { name: '病害编号', required: true },
  { name: '所属设施', required: true },
  { name: '病害类型', required: true },
  { name: '发现时间', required: false },
  { name: '所在位置', required: false },
]

function isClosed(row: Row) {
  return row['病害状态'] === CLOSED_STATUS
}

function extractError(payload: { message?: string; detail?: string } | null, fallback: string) {
  return payload?.message || payload?.detail || fallback
}

async function fetchEntry(id: string | number | null): Promise<Row> {
  const response = await request(`${ENDPOINT}/${id}`)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(extractError(payload, '病害详情读取失败'))
  }
  return payload as Row
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  try {
    detailEntry.value = await fetchEntry(row.id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '病害详情读取失败'
  }
}

function closeDetail() {
  detailEntry.value = null
}

async function openDisposal(row: Row) {
  errorMessage.value = ''
  disposalError.value = ''
  try {
    // 每次按 id 重新拉取，表单只装当前编号自己的等级与方案，不带入上一条的值
    const entry = await fetchEntry(row.id)
    disposalForm.value = {
      severity: String(entry['严重等级'] ?? ''),
      location: String(entry['所在位置'] ?? ''),
      plan: String(entry['处置方案'] ?? ''),
    }
    disposalTarget.value = entry
    detailEntry.value = null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '处置信息读取失败'
  }
}

function cancelDisposal() {
  disposalTarget.value = null
  disposalForm.value = { severity: '', location: '', plan: '' }
  disposalError.value = ''
}

async function submitDisposal() {
  const target = disposalTarget.value
  if (!target || saving.value) return
  disposalError.value = ''
  saving.value = true
  try {
    const response = await request(`${ENDPOINT}/${target.id}/disposal`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          严重等级: disposalForm.value.severity,
          处置方案: disposalForm.value.plan,
          所在位置: disposalForm.value.location,
        },
      }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(extractError(payload, '实施处置未生效，请稍后重试'))
    }
    applyEntry(payload.entry as Row)
    cancelDisposal()
    await loadStats()
  } catch (error) {
    disposalError.value = error instanceof Error ? error.message : '实施处置失败'
  } finally {
    saving.value = false
  }
}

async function closeEntry(row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/close`, { method: 'POST' })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(extractError(payload, '闭合未生效，请稍后重试'))
    }
    applyEntry(payload.entry as Row)
    await loadStats()
  } catch (error) {
    // 后端拦下的原因（如所在位置为空不允许闭合）直接展示
    errorMessage.value = error instanceof Error ? error.message : '闭合失败'
  }
}

function applyEntry(entry: Row) {
  // 只按 id 回写对应行，其他编号的等级与方案不受影响
  const index = rows.value.findIndex((row) => String(row.id) === String(entry.id))
  if (index >= 0) {
    rows.value.splice(index, 1, entry)
  }
  if (detailEntry.value && String(detailEntry.value.id) === String(entry.id)) {
    detailEntry.value = entry
  }
}

function openCreate() {
  createError.value = ''
  createForm.value = {}
  createOpen.value = true
}

function cancelCreate() {
  createOpen.value = false
  createForm.value = {}
  createError.value = ''
}

async function submitCreate() {
  if (saving.value) return
  createError.value = ''
  saving.value = true
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createForm.value }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(extractError(payload, '病害登记未生效'))
    }
    cancelCreate()
    await reload()
    await loadStats()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '病害登记失败'
  } finally {
    saving.value = false
  }
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (keyword.value.trim()) query.set('keyword', keyword.value.trim())
  if (statusFilter.value) query.set('status', statusFilter.value)
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(extractError(payload, '病害列表读取失败'))
    }
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '病害记录列表读取失败'
  }
}

async function loadStats() {
  try {
    const response = await request(`${ENDPOINT}?size=200`)
    if (!response.ok) return
    const payload = await response.json()
    const items: Row[] = payload.items ?? []
    const countOf = (status: string) => items.filter((row) => row['病害状态'] === status).length
    stats.value = [
      { label: '待处置病害', value: countOf('待处置') },
      { label: '处置中病害', value: countOf('处置中') },
      { label: '已闭合病害', value: countOf('已闭合') },
    ]
  } catch {
    // 统计卡片读取失败不阻断列表使用
  }
}

onMounted(() => {
  void reload()
  void loadStats()
})
</script>
