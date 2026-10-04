<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import { api } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const toast = useToast()
const auth = useAuthStore()

const tickets = ref<any[]>([])
const loading = ref(false)
const search = ref('')

const filterStatus = ref<string | null>(null)
const filterBrigade = ref<number | null>(null)
const filterDateFrom = ref<Date | null>(null)
const filterDateTo = ref<Date | null>(null)

const statusOptions = [
  { label: 'Все статусы', value: null },
  { label: 'Новая', value: 'new' },
  { label: 'Назначена', value: 'assigned' },
  { label: 'В работе', value: 'in_progress' },
  { label: 'Выполнена', value: 'done' },
  { label: 'Отменена', value: 'cancelled' },
]

const clients = ref<any[]>([])
const addresses = ref<any[]>([])
const brigades = ref<any[]>([])
const workTypes = ref<any[]>([])

const createDialogVisible = ref(false)
const createForm = ref({
  client_id: null as number | null,
  address_id: null as number | null,
  brigade_id: null as number | null,
  work_type_id: null as number | null,
  description: '',
  is_new_connection: false,
})

const newClientDialogVisible = ref(false)
const newClientForm = ref({
  last_name: '', first_name: '', middle_name: '', phone: '',
  city: '', street: '', house: '', apartment: '', entrance: '', comment: '',
})

const assignDialogVisible = ref(false)
const assignTicket = ref<any>(null)
const assignForm = ref({ brigade_id: null as number | null })

const closeDialogVisible = ref(false)
const closingTicket = ref<any>(null)
const closeForm = ref({
  cable_used_meters: 0,
  dispatcher_comment: '',
  fault_party: 'provider',
  cause_description: '',
})

const faultPartyOptions = [
  { label: 'Клиент', value: 'client' },
  { label: 'Провайдер', value: 'provider' },
  { label: 'Третьи лица', value: 'third_party' },
  { label: 'Погода', value: 'weather' },
  { label: 'Неизвестно', value: 'unknown' },
]

const statusLabels: Record<string, { text: string; severity: string }> = {
  new: { text: 'Новая', severity: 'info' },
  assigned: { text: 'Назначена', severity: 'warn' },
  in_progress: { text: 'В работе', severity: 'warn' },
  done: { text: 'Выполнено', severity: 'success' },
  cancelled: { text: 'Отменена', severity: 'danger' },
}

const filteredTickets = computed(() => {
  let result = tickets.value
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter((t) => t.number?.toLowerCase().includes(q))
  }
  if (filterStatus.value) {
    result = result.filter((t) => t.status === filterStatus.value)
  }
  if (filterBrigade.value) {
    result = result.filter((t) => t.brigade?.id === filterBrigade.value || t.brigade_id === filterBrigade.value)
  }
  if (filterDateFrom.value) {
    const from = filterDateFrom.value.getTime()
    result = result.filter((t) => t.created_at && new Date(t.created_at).getTime() >= from)
  }
  if (filterDateTo.value) {
    const to = new Date(filterDateTo.value)
    to.setHours(23, 59, 59, 999)
    result = result.filter((t) => t.created_at && new Date(t.created_at).getTime() <= to.getTime())
  }
  return result
})

function resetFilters() {
  search.value = ''
  filterStatus.value = null
  filterBrigade.value = null
  filterDateFrom.value = null
  filterDateTo.value = null
}

async function loadRefs() {
  const [c, a, b, w] = await Promise.all([
    api.get('/refs/clients'),
    api.get('/refs/addresses'),
    api.get('/refs/brigades'),
    api.get('/refs/work-types'),
  ])
  clients.value = c.data
  addresses.value = a.data
  brigades.value = b.data
  workTypes.value = w.data
}

async function loadTickets() {
  loading.value = true
  try {
    const { data } = await api.get('/tickets', { params: { limit: 200 } })
    tickets.value = data.items
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: 'Не удалось загрузить заявки', life: 3000 })
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createForm.value = { client_id: null, address_id: null, brigade_id: null, work_type_id: null, description: '', is_new_connection: false }
  createDialogVisible.value = true
}

watch(() => createForm.value.client_id, (clientId) => {
  if (clientId) {
    const selected = clients.value.find((c) => c.id === clientId)
    if (selected?.last_address_id) {
      createForm.value.address_id = selected.last_address_id
      createForm.value.is_new_connection = false
    } else {
      createForm.value.address_id = null
      createForm.value.is_new_connection = true
    }
  } else {
    createForm.value.address_id = null
    createForm.value.is_new_connection = false
  }
})

function openNewClientDialog() {
  newClientForm.value = { last_name: '', first_name: '', middle_name: '', phone: '', city: '', street: '', house: '', apartment: '', entrance: '', comment: '' }
  newClientDialogVisible.value = true
}

async function submitNewClient() {
  if (!newClientForm.value.last_name || !newClientForm.value.first_name) {
    toast.add({ severity: 'warn', summary: 'Заполните поля', detail: 'ФИО обязательно', life: 3000 }); return
  }
  if (!newClientForm.value.street || !newClientForm.value.house) {
    toast.add({ severity: 'warn', summary: 'Заполните адрес', detail: 'Улица и дом обязательны', life: 3000 }); return
  }
  try {
    const { data } = await api.post('/refs/clients', {
      last_name: newClientForm.value.last_name,
      first_name: newClientForm.value.first_name,
      middle_name: newClientForm.value.middle_name || null,
      phone: newClientForm.value.phone || null,
      address: {
        city: newClientForm.value.city || null,
        street: newClientForm.value.street,
        house: newClientForm.value.house,
        entrance: newClientForm.value.entrance || null,
        apartment: newClientForm.value.apartment || null,
        comment: newClientForm.value.comment || null,
      },
    })
    clients.value.unshift(data)
    createForm.value.client_id = data.id
    createForm.value.address_id = data.last_address_id
    createForm.value.is_new_connection = true
    newClientDialogVisible.value = false
    toast.add({ severity: 'success', summary: 'Клиент создан', life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось создать клиента', life: 4000 })
  }
}

async function submitCreate() {
  if (!createForm.value.client_id || !createForm.value.address_id) {
    toast.add({ severity: 'warn', summary: 'Заполните поля', detail: 'Клиент и адрес обязательны', life: 3000 }); return
  }
  try {
    await api.post('/tickets', {
      client_id: createForm.value.client_id,
      address_id: createForm.value.address_id,
      brigade_id: createForm.value.brigade_id,
      work_type_id: createForm.value.work_type_id,
      description: createForm.value.description,
    })
    toast.add({ severity: 'success', summary: 'Заявка создана', life: 3000 })
    createDialogVisible.value = false
    await loadTickets(); await loadRefs()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось создать', life: 4000 })
  }
}

function openAssign(ticket: any) {
  assignTicket.value = ticket
  assignForm.value = { brigade_id: null }
  assignDialogVisible.value = true
}

async function submitAssign() {
  if (!assignForm.value.brigade_id) {
    toast.add({ severity: 'warn', summary: 'Выберите бригаду', life: 3000 }); return
  }
  try {
    await api.post(`/tickets/${assignTicket.value.id}/assign`, { brigade_id: assignForm.value.brigade_id })
    toast.add({ severity: 'success', summary: 'Бригада назначена', life: 3000 })
    assignDialogVisible.value = false
    await loadTickets()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось назначить', life: 4000 })
  }
}

async function acceptTicket(t: any) {
  try {
    await api.post(`/tickets/${t.id}/accept`)
    toast.add({ severity: 'success', summary: 'Заявка принята в работу', life: 3000 })
    await loadTickets()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось принять', life: 4000 })
  }
}

function openCloseDialog(ticket: any) {
  closingTicket.value = ticket
  closeForm.value = { cable_used_meters: 0, dispatcher_comment: '', fault_party: 'provider', cause_description: '' }
  closeDialogVisible.value = true
}

async function submitClose() {
  if (!closingTicket.value) return
  try {
    await api.post(`/tickets/${closingTicket.value.id}/close`, closeForm.value)
    toast.add({ severity: 'success', summary: 'Отчёт принят', detail: 'Кабель списан с бригады', life: 3000 })
    closeDialogVisible.value = false
    await loadTickets()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || 'Не удалось сохранить отчёт', life: 4000 })
  }
}

async function downloadAct(ticket: any) {
  try {
    const response = await api.get(`/tickets/${ticket.id}/act/pdf`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `act_${ticket.number}.pdf`
    document.body.appendChild(link); link.click(); document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Ошибка', detail: 'Не удалось скачать акт', life: 3000 })
  }
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(() => { loadRefs(); loadTickets() })
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-neutral-900">Заявки</h1>
        <p class="text-sm text-neutral-500 mt-1">Диспетчер: создание и назначение · Бригада: приём и отчёт</p>
      </div>
      <Button v-if="auth.isDispatcher" label="Новая заявка" icon="pi pi-plus" @click="openCreateDialog" />
    </div>

    <!-- Фильтры -->
    <div class="bg-white rounded-lg border border-slate-200 p-4 mb-5">
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <span class="p-input-icon-left w-full sm:w-auto">
          <i class="pi pi-search" />
          <InputText v-model="search" placeholder="Поиск по номеру..." class="w-full sm:w-48" />
        </span>

        <Select
          v-model="filterStatus"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          placeholder="Статус"
          class="w-full sm:w-44"
          show-clear
        />

        <Select
          v-model="filterBrigade"
          :options="[{ id: null, name: 'Все бригады' }, ...brigades]"
          option-label="name"
          option-value="id"
          placeholder="Бригада"
          class="w-full sm:w-48"
          show-clear
        />

        <DatePicker
          v-model="filterDateFrom"
          placeholder="Дата с"
          date-format="dd.mm.yy"
          show-icon
          class="w-full sm:w-40"
        />

        <DatePicker
          v-model="filterDateTo"
          placeholder="Дата по"
          date-format="dd.mm.yy"
          show-icon
          class="w-full sm:w-40"
        />

        <Button label="Сбросить" icon="pi pi-filter-slash" severity="secondary" outlined size="small" class="w-full sm:w-auto" @click="resetFilters" />

        <span class="text-sm text-neutral-500 sm:ml-auto">
          Показано: {{ filteredTickets.length }} из {{ tickets.length }}
        </span>
      </div>
    </div>

    <!-- Таблица -->
    <div class="bg-white rounded-lg border border-slate-200 overflow-x-auto">
      <DataTable :value="filteredTickets" :loading="loading" paginator :rows="15" striped-rows data-key="id">
        <Column field="number" header="№" style="width: 130px">
          <template #body="{ data }">
            <router-link :to="`/tickets/${data.id}`" class="font-mono text-xs text-blue-600 hover:underline">{{ data.number }}</router-link>
          </template>
        </Column>
        <Column header="Дата" style="width: 110px">
          <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
        </Column>
        <Column header="Клиент"><template #body="{ data }">{{ data.client?.full_name || '—' }}</template></Column>
        <Column header="Адрес"><template #body="{ data }">{{ data.address?.full_address || '—' }}</template></Column>
        <Column header="Бригада"><template #body="{ data }">{{ data.brigade?.name || '—' }}</template></Column>
        <Column field="status" header="Статус" style="width: 140px">
          <template #body="{ data }">
            <Tag :value="statusLabels[data.status]?.text || data.status" :severity="statusLabels[data.status]?.severity || 'secondary'" />
          </template>
        </Column>
        <Column style="width: 170px" class="text-right">
          <template #body="{ data }">
            <Button v-if="data.status === 'new' && auth.isDispatcher" label="Назначить" icon="pi pi-user-plus" size="small" @click="openAssign(data)" />
            <Button v-else-if="data.status === 'assigned' && auth.isBrigade" label="В работу" icon="pi pi-play" size="small" severity="info" @click="acceptTicket(data)" />
            <Button v-else-if="data.status === 'in_progress' && auth.isBrigade" label="Отчёт бригады" icon="pi pi-check" size="small" @click="openCloseDialog(data)" />
            <Button v-else-if="data.status === 'done'" label="Акт PDF" icon="pi pi-file-pdf" size="small" severity="secondary" outlined @click="downloadAct(data)" />
            <Tag v-else-if="data.status === 'cancelled'" value="Отменена" severity="danger" />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Создание заявки -->
    <Dialog v-model:visible="createDialogVisible" header="Новая заявка (диспетчер)" modal :style="{ width: '580px' }">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Клиент *</label>
          <div class="flex gap-2">
            <Select v-model="createForm.client_id" :options="clients" option-label="full_name" option-value="id" placeholder="Выберите клиента" class="flex-1" filter />
            <Button label="+ Новый" severity="secondary" outlined @click="openNewClientDialog" />
          </div>
          <p v-if="createForm.is_new_connection" class="text-xs text-blue-600 mt-1.5 font-medium">✦ Новый клиент — заявка на подключение</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Адрес выезда *</label>
          <Select v-model="createForm.address_id" :options="addresses" option-label="full_address" option-value="id" placeholder="Выберите адрес" class="w-full" filter />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5">Бригада</label>
            <Select v-model="createForm.brigade_id" :options="brigades" option-label="name" option-value="id" placeholder="Назначим позже" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5">Вид работы</label>
            <Select v-model="createForm.work_type_id" :options="workTypes" option-label="name" option-value="id" placeholder="Не указан" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Описание проблемы</label>
          <Textarea v-model="createForm.description" rows="3" class="w-full" placeholder="Например: отсутствует сигнал..." />
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="createDialogVisible = false" />
        <Button label="Создать заявку" icon="pi pi-check" @click="submitCreate" />
      </template>
    </Dialog>

    <!-- Новый клиент -->
    <Dialog v-model:visible="newClientDialogVisible" header="Новый клиент (подключение)" modal :style="{ width: '560px' }">
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Фамилия *</label><InputText v-model="newClientForm.last_name" class="w-full" /></div>
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Имя *</label><InputText v-model="newClientForm.first_name" class="w-full" /></div>
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Отчество</label><InputText v-model="newClientForm.middle_name" class="w-full" /></div>
        </div>
        <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Телефон</label><InputText v-model="newClientForm.phone" class="w-full" placeholder="+7..." /></div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Город</label><InputText v-model="newClientForm.city" class="w-full" /></div>
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Улица *</label><InputText v-model="newClientForm.street" class="w-full" /></div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Дом *</label><InputText v-model="newClientForm.house" class="w-full" /></div>
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Кв.</label><InputText v-model="newClientForm.apartment" class="w-full" /></div>
          <div><label class="block text-sm font-medium text-neutral-700 mb-1.5">Подъезд</label><InputText v-model="newClientForm.entrance" class="w-full" /></div>
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="newClientDialogVisible = false" />
        <Button label="Создать клиента" icon="pi pi-check" @click="submitNewClient" />
      </template>
    </Dialog>

    <!-- Назначение бригады -->
    <Dialog v-model:visible="assignDialogVisible" :header="`Назначить бригаду: ${assignTicket?.number || ''}`" modal :style="{ width: '420px' }">
      <div>
        <label class="block text-sm font-medium text-neutral-700 mb-1.5">Бригада</label>
        <Select v-model="assignForm.brigade_id" :options="brigades" option-label="name" option-value="id" placeholder="Выберите бригаду" class="w-full" />
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="assignDialogVisible = false" />
        <Button label="Назначить" icon="pi pi-check" @click="submitAssign" />
      </template>
    </Dialog>

    <!-- Отчёт бригады -->
    <Dialog v-model:visible="closeDialogVisible" :header="`Отчёт бригады: ${closingTicket?.number || ''}`" modal :style="{ width: '520px' }">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Использовано кабеля, м</label>
          <InputNumber v-model="closeForm.cable_used_meters" :min="0" :max-fraction-digits="3" class="w-full" placeholder="0.000" />
          <p class="text-xs text-neutral-500 mt-1">Спишется с инвентаря бригады</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Виновная сторона</label>
          <Select v-model="closeForm.fault_party" :options="faultPartyOptions" option-label="label" option-value="value" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Причина / выполненные работы</label>
          <Textarea v-model="closeForm.cause_description" rows="3" class="w-full" placeholder="Что сделано, причина инцидента..." />
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined @click="closeDialogVisible = false" />
        <Button label="Сдать отчёт" icon="pi pi-check" @click="submitClose" />
      </template>
    </Dialog>
  </div>
</template>
