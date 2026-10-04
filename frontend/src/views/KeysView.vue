<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { api } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const toast = useToast()
const auth = useAuthStore()

const logs = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const selected = ref<any>(null)

const addresses = ref<any[]>([])
const brigades = ref<any[]>([])
const employees = ref<any[]>([])

const issueDialogVisible = ref(false)
const issueForm = ref({
  key_name: '',
  address_id: null as number | null,
  brigade_id: null as number | null,
  employee_id: null as number | null,
  purpose: '',
})

const addDialogVisible = ref(false)
const addForm = ref({ key_name: '', address_id: null as number | null })

const editDialogVisible = ref(false)
const editForm = ref({ old_name: '', new_name: '', address_id: null as number | null })

const board = computed(() => {
  const map = new Map<string, any[]>()
  for (const log of logs.value) {
    const arr = map.get(log.key_name) || []
    arr.push(log)
    map.set(log.key_name, arr)
  }
  const entries = [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], 'ru'))
  return entries.map(([name, arr], i) => {
    const sorted = [...arr].sort((a, b) => (a.issued_at || '').localeCompare(b.issued_at || ''))
    const current = sorted[sorted.length - 1]
    return {
      num: i + 1,
      key_name: name,
      current,
      is_out: current ? current.is_issued : false,
      address: current?.address || null,
      address_id: current?.address_id ?? null,
      history: [...sorted].reverse(),
    }
  })
})

const stats = computed(() => ({
  total: board.value.length,
  out: board.value.filter((k) => k.is_out).length,
  in: board.value.filter((k) => !k.is_out).length,
}))

const query = computed(() => search.value.trim().toLowerCase())
const hasQuery = computed(() => query.value.length > 0)

function matches(k: any) {
  if (!hasQuery.value) return true
  return (
    k.key_name.toLowerCase().includes(query.value) ||
    (k.address || '').toLowerCase().includes(query.value) ||
    String(k.num).includes(query.value) ||
    pad(k.num) === query.value
  )
}

const matchCount = computed(() => board.value.filter(matches).length)

const selectedOpen = computed({
  get: () => selected.value !== null,
  set: (v: boolean) => { if (!v) selected.value = null },
})

function pad(n: number) { return String(n).padStart(2, '0') }

function tileClass(k: any) {
  const status = k.is_out
    ? 'border-amber-400 bg-amber-50 text-amber-900 hover:bg-amber-100'
    : 'border-emerald-300 bg-emerald-50 text-emerald-900 hover:bg-emerald-100'
  const focus = hasQuery.value
    ? matches(k) ? 'ring-4 ring-blue-400 opacity-100' : 'opacity-25'
    : ''
  return `${status} ${focus}`
}

function formatDateTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadAll() {
  loading.value = true
  try {
    const [k, a, b, e] = await Promise.all([
      api.get('/keys'), api.get('/refs/addresses'), api.get('/refs/brigades'), api.get('/refs/employees'),
    ])
    logs.value = k.data; addresses.value = a.data; brigades.value = b.data; employees.value = e.data
  } finally { loading.value = false }
}

async function refresh() {
  await loadAll()
  if (selected.value) selected.value = board.value.find((b) => b.key_name === selected.value.key_name) || null
}

function openAddDialog() { addForm.value = { key_name: '', address_id: null }; addDialogVisible.value = true }

async function submitAdd() {
  if (!addForm.value.key_name) { toast.add({ severity: 'warn', summary: 'Укажите название ключа', life: 3000 }); return }
  try {
    await api.post('/keys', { ...addForm.value, to_storage: true })
    toast.add({ severity: 'success', summary: 'Ключ добавлен в ключницу', life: 3000 })
    addDialogVisible.value = false; await refresh()
  } catch (e: any) { toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось добавить', life: 4000 }) }
}

function openEditDialog() {
  if (!selected.value) return
  editForm.value = { old_name: selected.value.key_name, new_name: selected.value.key_name, address_id: selected.value.address_id }
  editDialogVisible.value = true
}

async function submitEdit() {
  if (!editForm.value.new_name) { toast.add({ severity: 'warn', summary: 'Укажите название', life: 3000 }); return }
  try {
    await api.put('/keys/edit', editForm.value)
    toast.add({ severity: 'success', summary: 'Ключ обновлён', life: 3000 })
    editDialogVisible.value = false; selected.value = null; await refresh()
  } catch (e: any) { toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось сохранить', life: 4000 }) }
}

function openIssueDialog(prefillName = '') {
  issueForm.value = { key_name: prefillName, address_id: null, brigade_id: null, employee_id: null, purpose: '' }
  issueDialogVisible.value = true
}

async function submitIssue() {
  if (!issueForm.value.key_name) { toast.add({ severity: 'warn', summary: 'Укажите название ключа', life: 3000 }); return }
  try {
    await api.post('/keys', issueForm.value)
    toast.add({ severity: 'success', summary: 'Ключ выдан', life: 3000 })
    issueDialogVisible.value = false; await refresh()
  } catch (e: any) { toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось выдать', life: 4000 }) }
}

async function returnKey(k: any) {
  try {
    await api.post(`/keys/${k.current.id}/return`)
    toast.add({ severity: 'success', summary: 'Ключ возвращён', life: 3000 }); await refresh()
  } catch (e: any) { toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось вернуть', life: 4000 }) }
}

onMounted(loadAll)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-neutral-900">Ключница</h1>
        <p class="text-sm text-neutral-500 mt-1">Всего: {{ stats.total }} · На руках: {{ stats.out }} · В ключнице: {{ stats.in }}</p>
      </div>
      <div v-if="auth.isDispatcher" class="flex gap-2">
        <Button label="Добавить ключ" icon="pi pi-plus" severity="secondary" outlined @click="openAddDialog" />
        <Button label="Выдать ключ" icon="pi pi-key" @click="openIssueDialog()" />
      </div>
    </div>

    <div class="bg-white rounded-lg border border-slate-200 p-4 mb-5">
      <div class="flex items-center gap-4">
        <span class="p-input-icon-left flex-1 max-w-lg">
          <i class="pi pi-search" />
          <InputText v-model="search" placeholder="Адрес, название или номер ключа..." class="w-full" />
        </span>
        <span v-if="hasQuery" class="text-sm text-neutral-600">Найдено: <b>{{ matchCount }}</b></span>
      </div>
      <div class="flex items-center gap-5 mt-3 text-xs text-neutral-600">
        <span class="flex items-center gap-2"><span class="w-3 h-3 rounded bg-emerald-300"></span> В ключнице</span>
        <span class="flex items-center gap-2"><span class="w-3 h-3 rounded bg-amber-400"></span> На руках</span>
        <span class="flex items-center gap-2"><span class="w-3 h-3 rounded ring-2 ring-blue-400 bg-white"></span> Совпадение</span>
      </div>
    </div>

    <div v-if="loading" class="text-neutral-500">Загрузка...</div>

    <div v-else-if="board.length" class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2 sm:gap-3">
      <button v-for="k in board" :key="k.key_name" class="aspect-square rounded-xl border-2 flex flex-col items-center justify-center gap-1 transition" :class="tileClass(k)" @click="selected = k">
        <span class="text-xl sm:text-2xl font-bold">{{ pad(k.num) }}</span>
        <i class="pi pi-key text-sm opacity-70"></i>
        <span class="text-[10px] font-medium">{{ k.is_out ? 'на руках' : 'в ключнице' }}</span>
      </button>
    </div>

    <div v-else class="bg-white border border-dashed border-slate-300 rounded-lg p-10 text-center text-neutral-500">
      Ключей пока нет.
    </div>

    <!-- Панель деталей -->
    <Drawer v-model:visible="selectedOpen" position="right" :style="{ width: '380px' }" :header="selected ? `Ключ ${pad(selected.num)}` : ''">
      <div v-if="selected" class="space-y-5 text-neutral-800">
        <div>
          <div class="text-sm text-neutral-500 mb-1">Название</div>
          <div class="font-semibold text-neutral-900">{{ selected.key_name }}</div>
        </div>
        <div>
          <Tag v-if="selected.is_out" value="На руках" severity="warn" />
          <Tag v-else value="В ключнице" severity="success" />
        </div>
        <div>
          <div class="text-sm text-neutral-500 mb-1">Адрес</div>
          <div class="text-sm text-neutral-900">{{ selected.address || '—' }}</div>
        </div>
        <div class="grid grid-cols-1 gap-3 text-sm">
          <div><div class="text-neutral-500 mb-1">Бригада</div><div class="text-neutral-900">{{ selected.current?.brigade || '—' }}</div></div>
          <div><div class="text-neutral-500 mb-1">Кто взял</div><div class="text-neutral-900">{{ selected.current?.employee || '—' }}</div></div>
          <div><div class="text-neutral-500 mb-1">Цель</div><div class="text-neutral-900">{{ selected.current?.purpose || '—' }}</div></div>
          <div><div class="text-neutral-500 mb-1">Выдан</div><div class="text-neutral-900">{{ formatDateTime(selected.current?.issued_at) }}</div></div>
        </div>
        <div>
          <div class="text-sm font-medium text-neutral-700 mb-2">История</div>
          <div class="space-y-2">
            <div v-for="h in selected.history" :key="h.id" class="bg-neutral-100 rounded-md p-2 text-xs">
              <div class="flex justify-between text-neutral-600">
                <span>{{ formatDateTime(h.issued_at) }}</span>
                <span>{{ h.returned_at ? 'возвращён ' + formatDateTime(h.returned_at) : 'на руках' }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="auth.isDispatcher" class="flex gap-2 pt-2">
          <Button label="Редактировать" icon="pi pi-pencil" severity="secondary" outlined class="flex-1" @click="openEditDialog" />
        </div>
        <div class="flex gap-2">
          <Button v-if="selected.is_out" label="Вернуть ключ" icon="pi pi-undo" class="flex-1" @click="returnKey(selected)" />
          <Button v-else-if="auth.isDispatcher" label="Выдать" icon="pi pi-key" class="flex-1" @click="openIssueDialog(selected.key_name)" />
        </div>
      </div>
    </Drawer>

    <!-- Диалог редактирования -->
    <Dialog v-model:visible="editDialogVisible" header="Редактировать ключ" modal :style="{ width: '440px' }">
      <div class="space-y-4">
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Название *</label><InputText v-model="editForm.new_name" class="w-full" /></div>
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Адрес</label><Select v-model="editForm.address_id" :options="addresses" option-label="full_address" option-value="id" placeholder="Не указан" class="w-full" filter /></div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="editDialogVisible = false" />
        <Button label="Сохранить" icon="pi pi-check" @click="submitEdit" />
      </template>
    </Dialog>

    <!-- Диалог добавления -->
    <Dialog v-model:visible="addDialogVisible" header="Добавить ключ в ключницу" modal :style="{ width: '440px' }">
      <div class="space-y-4">
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Название *</label><InputText v-model="addForm.key_name" class="w-full" placeholder="Чердак — Гагарина 5" /></div>
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Адрес</label><Select v-model="addForm.address_id" :options="addresses" option-label="full_address" option-value="id" placeholder="Не указан" class="w-full" filter /></div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="addDialogVisible = false" />
        <Button label="Добавить" icon="pi pi-check" @click="submitAdd" />
      </template>
    </Dialog>

    <!-- Диалог выдачи -->
    <Dialog v-model:visible="issueDialogVisible" header="Выдача ключа" modal :style="{ width: '520px' }">
      <div class="space-y-4">
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Название *</label><InputText v-model="issueForm.key_name" class="w-full" placeholder="Чердак — Ленина 10" /></div>
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Адрес</label><Select v-model="issueForm.address_id" :options="addresses" option-label="full_address" option-value="id" placeholder="Не указан" class="w-full" filter /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Бригада</label><Select v-model="issueForm.brigade_id" :options="brigades" option-label="name" option-value="id" placeholder="—" class="w-full" /></div>
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Сотрудник</label><Select v-model="issueForm.employee_id" :options="employees" option-label="full_name" option-value="id" placeholder="—" class="w-full" filter /></div>
        </div>
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Цель</label><InputText v-model="issueForm.purpose" class="w-full" placeholder="Ремонт магистрали" /></div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="issueDialogVisible = false" />
        <Button label="Выдать" icon="pi pi-check" @click="submitIssue" />
      </template>
    </Dialog>
  </div>
</template>
