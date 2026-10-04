<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import { api } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const toast = useToast()
const auth = useAuthStore()

const items = ref<any[]>([])
const loading = ref(false)

const addDialogVisible = ref(false)
const addForm = ref({
  name: '',
  category: 'tool',
  unit: 'piece',
  initial_quantity: 0,
  min_quantity: 0,
})

const categoryOptions = [
  { label: 'Инструмент', value: 'tool' },
  { label: 'Расходник', value: 'consumable' },
  { label: 'Оптический кабель', value: 'optical_cable' },
  { label: 'Витая пара (UTP)', value: 'utp_cable' },
  { label: 'Роутер', value: 'router' },
  { label: 'Коммутатор', value: 'switch' },
]

const unitOptions = [
  { label: 'Штуки', value: 'piece' },
  { label: 'Метры', value: 'meter' },
]

async function loadItems() {
  loading.value = true
  try {
    const { data } = await api.get('/warehouse')
    items.value = data
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  addForm.value = { name: '', category: 'tool', unit: 'piece', initial_quantity: 0, min_quantity: 0 }
  addDialogVisible.value = true
}

async function submitAdd() {
  if (!addForm.value.name) {
    toast.add({ severity: 'warn', summary: 'Заполните поле', detail: 'Укажите название', life: 3000 })
    return
  }
  try {
    await api.post('/warehouse', addForm.value)
    toast.add({ severity: 'success', summary: 'Позиция добавлена', life: 3000 })
    addDialogVisible.value = false
    await loadItems()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось добавить', life: 4000 })
  }
}

onMounted(loadItems)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-neutral-900">Центральный склад</h1>
        <p class="text-sm text-neutral-500 mt-1">Остатки оборудования и материалов</p>
      </div>
      <Button v-if="auth.isDispatcher" label="Добавить позицию" icon="pi pi-plus" @click="openAddDialog" />
    </div>

    <div class="bg-white rounded-lg border border-slate-200 overflow-x-auto">
      <DataTable :value="items" :loading="loading" striped-rows paginator :rows="15">
        <Column field="name" header="Наименование" />
        <Column field="category" header="Категория" style="width: 180px">
          <template #body="{ data }">
            {{ categoryOptions.find(o => o.value === data.category)?.label || data.category }}
          </template>
        </Column>
        <Column field="quantity" header="Остаток" style="width: 120px" class="text-right" />
        <Column field="min_quantity" header="Минимум" style="width: 120px" class="text-right" />
        <Column field="unit" header="Ед." style="width: 80px">
          <template #body="{ data }">
            {{ unitOptions.find(o => o.value === data.unit)?.label || data.unit }}
          </template>
        </Column>
        <Column header="Статус" style="width: 150px">
          <template #body="{ data }">
            <Tag v-if="data.is_low" value="Низкий остаток" severity="danger" />
            <Tag v-else value="В норме" severity="success" />
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog v-model:visible="addDialogVisible" header="Новая позиция склада" modal :style="{ width: '480px' }">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Название *</label>
          <InputText v-model="addForm.name" class="w-full" placeholder="Например: Лестница приставная 5м" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5">Категория</label>
            <Select v-model="addForm.category" :options="categoryOptions" option-label="label" option-value="value" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5">Единица измерения</label>
            <Select v-model="addForm.unit" :options="unitOptions" option-label="label" option-value="value" class="w-full" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5">Начальное количество</label>
            <InputNumber v-model="addForm.initial_quantity" :min="0" :max-fraction-digits="2" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5">Минимальный остаток</label>
            <InputNumber v-model="addForm.min_quantity" :min="0" :max-fraction-digits="2" class="w-full" />
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="addDialogVisible = false" />
        <Button label="Добавить" icon="pi pi-check" @click="submitAdd" />
      </template>
    </Dialog>
  </div>
</template>
