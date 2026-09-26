<template>
  <section class="page" data-module="disease">
    <header class="page-head">
      <div>
        <h2>病害记录管理</h2>
        <p class="page-desc">围绕病害编号、所属设施、病害类型、严重等级做登记、处置与闭合；等级、方案与状态分开保存，互不串用。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记病害</button>
        <button class="btn" type="button" @click="exportRows">导出病害记录清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in statCards" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>病害编号</span>
        <input v-model="filters.keyword" placeholder="按病害编号检索" />
      </label>
      <label class="filter-item">
        <span>病害状态</span>
        <select v-model="filters.status">
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
        <tr v-for="row in rows" :key="row.id">
          <td>
            <button class="link" type="button" @click="openDetail(row)">{{ row.病害编号 }}</button>
          </td>
          <td>{{ row.所属设施 || '—' }}</td>
          <td>{{ row.病害类型 || '—' }}</td>
          <td><span :class="severityClass(row.严重等级)">{{ row.严重等级 || '—' }}</span></td>
          <td>{{ row.发现时间 || '—' }}</td>
          <td>{{ row.所在位置 || '—' }}</td>
          <td class="plan-cell" :title="row.处置方案">{{ row.处置方案 || '—' }}</td>
          <td><span class="status-tag" :class="statusClass(row.病害状态)">{{ row.病害状态 || '—' }}</span></td>
          <td class="row-actions">
            <template v-if="row.病害状态 === CLOSED">
              <button class="link" type="button" @click="openDetail(row)">查看详情</button>
            </template>
            <template v-else>
              <button class="link" type="button" @click="openDetail(row)">详情</button>
              <button class="link" type="button" @click="openDispose(row)">实施处置</button>
              <button class="link" type="button" @click="closeRow(row)">闭合</button>
            </template>
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
      <span v-if="successMessage" class="success-text">{{ successMessage }}</span>
    </footer>

    <!-- 登记病害 -->
    <div v-if="createVisible" class="modal-mask" @click.self="closeCreate">
      <div class="modal">
        <div class="modal-head">
          <h3>登记病害</h3>
          <button class="modal-close" type="button" @click="closeCreate">×</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <label class="form-field">
              <span>病害编号<i class="req">*</i></span>
              <input v-model="createForm.病害编号" placeholder="如 DISE-0006" />
            </label>
            <label class="form-field">
              <span>所属设施<i class="req">*</i></span>
              <input v-model="createForm.所属设施" placeholder="如 振兴路 K3+200 沥青路面" />
            </label>
            <label class="form-field">
              <span>病害类型<i class="req">*</i></span>
              <input v-model="createForm.病害类型" placeholder="如 坑槽、裂缝" />
            </label>
            <label class="form-field">
              <span>严重等级<i class="req">*</i></span>
              <select v-model="createForm.严重等级">
                <option value="" disabled>请选择严重等级</option>
                <option v-for="level in severityLevels" :key="level" :value="level">{{ level }}</option>
              </select>
            </label>
            <label class="form-field">
              <span>发现时间</span>
              <input v-model="createForm.发现时间" type="date" />
            </label>
            <label class="form-field">
              <span>所在位置</span>
              <input v-model="createForm.所在位置" placeholder="如 振兴路 K3+200 行车道" />
            </label>
          </div>
          <p v-if="createError" class="form-error">{{ createError }}</p>
        </div>
        <div class="modal-foot">
          <button class="btn" type="button" :disabled="submitting" @click="closeCreate">取消</button>
          <button class="btn primary" type="button" :disabled="submitting" @click="submitCreate">登记</button>
        </div>
      </div>
    </div>

    <!-- 实施处置：表单内容每次打开都按当前病害编号重新拉取，绝不沿用上一条的数据 -->
    <div v-if="disposeVisible" class="modal-mask" @click.self="closeDispose">
      <div class="modal">
        <div class="modal-head">
          <h3>实施处置 · {{ disposeForm.病害编号 }}</h3>
          <button class="modal-close" type="button" @click="closeDispose">×</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <label class="form-field">
              <span>病害编号</span>
              <input :value="disposeForm.病害编号" readonly />
            </label>
            <label class="form-field">
              <span>当前状态</span>
              <input :value="disposeForm.病害状态" readonly />
            </label>
            <label class="form-field span-2">
              <span>严重等级<i class="req">*</i>（只改本病害，不影响其他编号）</span>
              <select v-model="disposeForm.严重等级">
                <option v-for="level in severityLevels" :key="level" :value="level">{{ level }}</option>
              </select>
            </label>
            <label class="form-field span-2">
              <span>所在位置（闭合前必须填写）</span>
              <input v-model="disposeForm.所在位置" placeholder="如 振兴路 K3+200 行车道" />
            </label>
            <label class="form-field span-2">
              <span>处置方案<i class="req">*</i>（保存到本病害编号，不被其他记录覆盖）</span>
              <textarea v-model="disposeForm.处置方案" placeholder="描述维修措施、责任班组、工期等"></textarea>
            </label>
          </div>
          <p v-if="disposeError" class="form-error">{{ disposeError }}</p>
        </div>
        <div class="modal-foot">
          <button class="btn" type="button" :disabled="submitting" @click="closeDispose">取消</button>
          <button class="btn primary" type="button" :disabled="submitting" @click="submitDispose">实施处置</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { request } from '@/api/client'

type DiseaseRow = {
  id: number
  病害编号: string
  所属设施: string
  病害类型: string
  严重等级: string
  发现时间: string
  所在位置: string
  处置方案: string
  病害状态: string
}

const ENDPOINT = '/api/disease'
const PENDING = '待处置'
const PROCESSING = '处置中'
const CLOSED = '已闭合'

const columns = ['病害编号', '所属设施', '病害类型', '严重等级', '发现时间', '所在位置', '处置方案', '病害状态']
const statuses = [PENDING, PROCESSING, CLOSED]
const severityLevels = ['轻微', '中等', '严重']

const router = useRouter()

const rows = ref<DiseaseRow[]>([])
const total = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
const filters = reactive({ keyword: '', status: '' })
const statCounts = ref<Record<string, number>>({ [PENDING]: 0, [PROCESSING]: 0, [CLOSED]: 0 })
const statCards = ref([
  { label: '待处置病害', value: 0 },
  { label: '处置中病害', value: 0 },
  { label: '已闭合病害', value: 0 },
])

const submitting = ref(false)

const createVisible = ref(false)
const createError = ref('')
const emptyCreateForm = () => ({
  病害编号: '',
  所属设施: '',
  病害类型: '',
  严重等级: '',
  发现时间: new Date().toISOString().slice(0, 10),
  所在位置: '',
})
const createForm = reactive(emptyCreateForm())

const disposeVisible = ref(false)
const disposeError = ref('')
const disposeForm = reactive<DiseaseRow & { id: number }>({
  id: 0,
  病害编号: '',
  所属设施: '',
  病害类型: '',
  严重等级: '',
  发现时间: '',
  所在位置: '',
  处置方案: '',
  病害状态: '',
})

function statusClass(status: string) {
  if (status === PENDING) return 'tag-pending'
  if (status === PROCESSING) return 'tag-processing'
  if (status === CLOSED) return 'tag-closed'
  return ''
}

function severityClass(level: string) {
  if (level === '严重') return 'sev-high'
  if (level === '中等') return 'sev-mid'
  if (level === '轻微') return 'sev-low'
  return ''
}

function flashSuccess(text: string) {
  successMessage.value = text
  window.setTimeout(() => {
    if (successMessage.value === text) successMessage.value = ''
  }, 3000)
}

async function readError(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as { detail?: string; message?: string }
    return payload.message || payload.detail || fallback
  } catch {
    return fallback
  }
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (filters.keyword.trim()) params.set('keyword', filters.keyword.trim())
  if (filters.status) params.set('status', filters.status)
  try {
    const [listResponse, statsResponse] = await Promise.all([
      request(`${ENDPOINT}?${params.toString()}`),
      request(`${ENDPOINT}/stats`),
    ])
    if (!listResponse.ok) throw new Error(await readError(listResponse, '病害列表读取失败'))
    if (!statsResponse.ok) throw new Error(await readError(statsResponse, '病害统计读取失败'))
    const payload = (await listResponse.json()) as { items?: DiseaseRow[]; total?: number }
    const stats = (await statsResponse.json()) as Record<string, number>
    rows.value = (payload.items ?? []) as DiseaseRow[]
    total.value = payload.total ?? rows.value.length
    statCounts.value = stats
    statCards.value = [
      { label: '待处置病害', value: stats[PENDING] ?? 0 },
      { label: '处置中病害', value: stats[PROCESSING] ?? 0 },
      { label: '已闭合病害', value: stats[CLOSED] ?? 0 },
    ]
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '病害记录列表读取失败'
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openDetail(row: DiseaseRow) {
  void router.push({ name: 'disease-detail', params: { id: String(row.id) } })
}

function openCreate() {
  createError.value = ''
  Object.assign(createForm, emptyCreateForm())
  createVisible.value = true
}

function closeCreate() {
  createVisible.value = false
}

async function submitCreate() {
  createError.value = ''
  submitting.value = true
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...createForm } }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) {
      createError.value = payload.message || '病害登记未生效，请稍后重试'
      return
    }
    createVisible.value = false
    await reload()
    flashSuccess('病害已登记')
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '病害登记失败'
  } finally {
    submitting.value = false
  }
}

async function openDispose(row: DiseaseRow) {
  disposeError.value = ''
  if (row.病害状态 === CLOSED) {
    errorMessage.value = '该病害已闭合，只可查看，不能再改动'
    return
  }
  // 每次打开都用接口重新取本条记录，杜绝弹窗里残留上一条病害的等级/方案。
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) throw new Error(await readError(response, '病害明细读取失败'))
    const detail = (await response.json()) as DiseaseRow
    if (detail.病害状态 === CLOSED) {
      errorMessage.value = '该病害已闭合，只可查看，不能再改动'
      await reload()
      return
    }
    Object.assign(disposeForm, detail)
    disposeVisible.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '病害明细读取失败'
  }
}

function closeDispose() {
  disposeVisible.value = false
}

async function submitDispose() {
  disposeError.value = ''
  submitting.value = true
  try {
    const response = await request(`${ENDPOINT}/${disposeForm.id}/dispose`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          严重等级: disposeForm.严重等级,
          所在位置: disposeForm.所在位置,
          处置方案: disposeForm.处置方案,
        },
      }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) {
      disposeError.value = payload.message || '处置未生效，请稍后重试'
      return
    }
    disposeVisible.value = false
    await reload()
    flashSuccess('处置已实施，方案已保存到本病害记录')
  } catch (error) {
    disposeError.value = error instanceof Error ? error.message : '实施处置失败'
  } finally {
    submitting.value = false
  }
}

async function closeRow(row: DiseaseRow) {
  errorMessage.value = ''
  if (row.病害状态 === CLOSED) {
    errorMessage.value = '该病害已闭合，只可查看，不能再改动'
    return
  }
  if (!row.所在位置?.trim()) {
    // 先在前端把原因讲清楚，后端还会再兜底校验一次。
    errorMessage.value = '所在位置为空，不允许闭合；请先在「实施处置」里补全病害所在位置'
    return
  }
  if (!window.confirm(`确认闭合病害 ${row.病害编号}？闭合后将不可再修改。`)) return
  try {
    const response = await request(`${ENDPOINT}/${row.id}/close`, { method: 'POST' })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) {
      errorMessage.value = payload.message || '闭合未生效，请稍后重试'
      return
    }
    await reload()
    flashSuccess(payload.message || '病害已闭合')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '病害闭合失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.plan-cell {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
