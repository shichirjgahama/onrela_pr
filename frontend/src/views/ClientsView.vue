<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import { api } from '@/composables/useApi'

const clients = ref<any[]>([])
const loading = ref(false)
const search = ref('')

const filtered = computed(() => {
  if (!search.value) return clients.value
  const q = search.value.toLowerCase()
  return clients.value.filter(
    (c) =>
      c.full_name?.toLowerCase().includes(q) ||
      c.organization?.toLowerCase().includes(q) ||
      c.phone?.includes(q),
  )
})

const stats = computed(() => ({
  total: clients.value.length,
  b2b: clients.value.filter((c) => c.type === 'b2b').length,
  b2c: clients.value.filter((c) => c.type === 'b2c').length,
}))

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get('/clients')
    clients.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-semibold text-slate-900">Клиенты</h1>
      <p class="text-sm text-slate-500 mt-1">
        Всего: {{ stats.total }} · Физлица: {{ stats.b2c }} · Юрлица: {{ stats.b2b }}
      </p>
    </div>

    <div class="bg-white rounded-lg border border-slate-200">
      <div class="p-4 border-b border-slate-200">
        <span class="p-input-icon-left w-full max-w-md">
          <i class="pi pi-search" />
          <InputText v-model="search" placeholder="Поиск по ФИО, организации, телефону..." class="w-full" />
        </span>
      </div>

      <DataTable :value="filtered" :loading="loading" paginator :rows="15" striped-rows data-key="id">
        <Column field="full_name" header="ФИО" />
        <Column field="phone" header="Телефон" style="width: 160px">
          <template #body="{ data }">
            <span class="font-mono text-xs">{{ data.phone || '—' }}</span>
          </template>
        </Column>
        <Column header="Тип" style="width: 120px">
          <template #body="{ data }">
            <Tag v-if="data.type === 'b2b'" value="Юрлицо" severity="info" />
            <Tag v-else value="Физлицо" severity="secondary" />
          </template>
        </Column>
        <Column header="Организация">
          <template #body="{ data }">
            <div v-if="data.organization">
              <div class="text-sm">{{ data.organization }}</div>
              <div class="text-xs text-slate-500">ИНН {{ data.inn }}</div>
            </div>
            <span v-else class="text-slate-400">—</span>
          </template>
        </Column>
        <Column field="tariff" header="Тариф" style="width: 180px">
          <template #body="{ data }">{{ data.tariff || '—' }}</template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>
