<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import { api } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const toast = useToast()
const auth = useAuthStore()

const brigades = ref<any[]>([])
const loading = ref(false)
const employees = ref<any[]>([])

const addDialogVisible = ref(false)
const addForm = ref({
  name: '',
  description: '',
  lead_employee_id: null as number | null,
})

const confirmDialogVisible = ref(false)
const disbandingBrigade = ref<any>(null)

async function loadAll() {
  loading.value = true
  try {
    const [b, e] = await Promise.all([
      api.get('/brigades'),
      api.get('/refs/employees'),
    ])
    brigades.value = b.data
    employees.value = e.data
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  addForm.value = { name: '', description: '', lead_employee_id: null }
  addDialogVisible.value = true
}

async function submitAdd() {
  if (!addForm.value.name) {
    toast.add({ severity: 'warn', summary: 'Укажите название бригады', life: 3000 })
    return
  }
  try {
    await api.post('/brigades', addForm.value)
    toast.add({ severity: 'success', summary: 'Бригада создана', life: 3000 })
    addDialogVisible.value = false
    await loadAll()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось создать', life: 4000 })
  }
}

function openDisbandDialog(brigade: any) {
  disbandingBrigade.value = brigade
  confirmDialogVisible.value = true
}

async function submitDisband() {
  if (!disbandingBrigade.value) return
  try {
    await api.delete(`/brigades/${disbandingBrigade.value.id}`)
    toast.add({ severity: 'success', summary: 'Бригада расформирована', life: 3000 })
    confirmDialogVisible.value = false
    disbandingBrigade.value = null
    await loadAll()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось расформировать', life: 4000 })
  }
}

onMounted(loadAll)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-neutral-900">Бригады</h1>
        <p class="text-sm text-neutral-500 mt-1">Состав бригад и выданный инвентарь</p>
      </div>
      <Button v-if="auth.isDispatcher" label="Создать бригаду" icon="pi pi-plus" @click="openAddDialog" />
    </div>

    <div v-if="loading" class="text-neutral-500">Загрузка...</div>

    <div v-else class="grid grid-cols-1 gap-5">
      <div v-for="brigade in brigades" :key="brigade.id" class="bg-white border border-slate-200 rounded-lg p-6">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">{{ brigade.name }}</h2>
            <p class="text-sm text-neutral-500">
              Старший: {{ brigade.lead_employee || 'не назначен' }}
              · Сотрудников: {{ brigade.members_count }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Tag value="Активна" severity="success" />
            <Button
              v-if="auth.isDispatcher"
              label="Расформировать"
              icon="pi pi-trash"
              severity="danger"
              outlined
              size="small"
              @click="openDisbandDialog(brigade)"
            />
          </div>
        </div>

        <h3 class="text-sm font-medium text-neutral-700 mb-3">Инвентарь бригады</h3>
        <DataTable :value="brigade.inventory" size="small" striped-rows>
          <Column field="name" header="Наименование" />
          <Column field="category" header="Категория" style="width: 150px" />
          <Column field="quantity" header="Количество" style="width: 120px" class="text-right" />
          <Column field="unit" header="Ед." style="width: 60px" />
        </DataTable>
      </div>
    </div>

    <Dialog v-model:visible="addDialogVisible" header="Новая бригада" modal :style="{ width: '480px' }">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Название *</label>
          <InputText v-model="addForm.name" class="w-full" placeholder="Например: Бригада №3" />
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Старший бригады</label>
          <Select v-model="addForm.lead_employee_id" :options="employees" option-label="full_name" option-value="id" placeholder="Не назначен" class="w-full" filter />
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Описание</label>
          <Textarea v-model="addForm.description" rows="2" class="w-full" placeholder="Зона обслуживания, примечания..." />
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="addDialogVisible = false" />
        <Button label="Создать" icon="pi pi-check" @click="submitAdd" />
      </template>
    </Dialog>

    <!-- Диалог подтверждения расформирования -->
    <Dialog v-model:visible="confirmDialogVisible" header="Расформировать бригаду" modal :style="{ width: '420px' }">
      <div class="flex items-start gap-3">
        <i class="pi pi-exclamation-triangle text-2xl text-red-500 mt-1"></i>
        <div>
          <p class="text-neutral-900 font-medium">Вы уверены?</p>
          <p class="text-sm text-neutral-600 mt-1">
            Бригада <b>{{ disbandingBrigade?.name }}</b> будет удалена вместе с её инвентарём.
            Это действие нельзя отменить.
          </p>
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="confirmDialogVisible = false" />
        <Button label="Расформировать" icon="pi pi-trash" severity="danger" @click="submitDisband" />
      </template>
    </Dialog>
  </div>
</template>
