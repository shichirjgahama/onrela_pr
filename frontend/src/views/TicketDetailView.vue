<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { api } from '@/composables/useApi'

const route = useRoute()
const router = useRouter()

const ticket = ref<any>(null)
const loading = ref(true)
const error = ref('')

const statusLabels: Record<string, { text: string; severity: string }> = {
  new: { text: 'Новая', severity: 'info' },
  assigned: { text: 'Назначена', severity: 'warn' },
  in_progress: { text: 'В работе', severity: 'warn' },
  done: { text: 'Выполнено', severity: 'success' },
  cancelled: { text: 'Отменена', severity: 'danger' },
}

const faultLabels: Record<string, string> = {
  client: 'Клиент', provider: 'Провайдер', third_party: 'Третьи лица',
  weather: 'Погода', unknown: 'Неизвестно',
}

function formatDateTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/tickets/${route.params.id}/detail`)
    ticket.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || 'Не удалось загрузить заявку'
  } finally {
    loading.value = false
  }
})

async function downloadAct() {
  const response = await api.get(`/tickets/${ticket.value.id}/act/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `act_${ticket.value.number}.pdf`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div>
    <!-- Состояние ошибки -->
    <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-red-900">
      <h2 class="font-semibold mb-2">Ошибка загрузки</h2>
      <p class="text-sm">{{ error }}</p>
      <p class="text-xs mt-2 text-red-700">Проверь, что бэкенд запущен и эндпоинт /tickets/{{ route.params.id }}/detail добавлен.</p>
    </div>

    <div v-else-if="loading" class="text-slate-500">Загрузка...</div>

    <div v-else-if="ticket">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-4">
          <Button icon="pi pi-arrow-left" severity="secondary" outlined rounded @click="router.push('/tickets')" />
          <div>
            <div class="flex items-center gap-3">
              <h1 class="text-2xl font-semibold text-slate-900 font-mono">{{ ticket.number }}</h1>
              <Tag :value="statusLabels[ticket.status]?.text" :severity="statusLabels[ticket.status]?.severity" />
            </div>
            <p class="text-sm text-slate-500 mt-1">Создана: {{ formatDateTime(ticket.created_at) }}</p>
          </div>
        </div>
        <Button v-if="ticket.status === 'done'" label="Акт PDF" icon="pi pi-file-pdf" @click="downloadAct" />
      </div>

      <div class="grid grid-cols-3 gap-5">
        <div class="col-span-2 space-y-5">
          <div class="bg-white border border-slate-200 rounded-lg p-6">
            <h3 class="font-semibold text-slate-900 mb-4">Информация о заявке</h3>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-slate-500 mb-1">Клиент</div>
                <div class="font-medium text-slate-900">{{ ticket.client?.full_name }}</div>
                <div class="text-slate-500">{{ ticket.client?.phone || '' }}</div>
                <div v-if="ticket.client?.organization" class="text-slate-500">{{ ticket.client.organization }}</div>
              </div>
              <div>
                <div class="text-slate-500 mb-1">Адрес</div>
                <div class="font-medium text-slate-900">{{ ticket.address }}</div>
              </div>
              <div>
                <div class="text-slate-500 mb-1">Бригада</div>
                <div class="font-medium text-slate-900">{{ ticket.brigade || '—' }}</div>
              </div>
              <div>
                <div class="text-slate-500 mb-1">Вид работы</div>
                <div class="font-medium text-slate-900">{{ ticket.work_type || '—' }}</div>
              </div>
            </div>
            <div v-if="ticket.description" class="mt-4 pt-4 border-t border-slate-100">
              <div class="text-slate-500 text-sm mb-1">Описание</div>
              <p class="text-sm text-slate-900">{{ ticket.description }}</p>
            </div>
          </div>

          <div v-if="ticket.diagnostic" class="bg-white border border-slate-200 rounded-lg p-6">
            <h3 class="font-semibold text-slate-900 mb-4">Диагностика инцидента</h3>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-slate-500 mb-1">Виновная сторона</div>
                <Tag :value="faultLabels[ticket.diagnostic.fault_party] || ticket.diagnostic.fault_party" severity="warn" />
              </div>
              <div>
                <div class="text-slate-500 mb-1">Причина</div>
                <p class="text-slate-900">{{ ticket.diagnostic.cause_description || '—' }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white border border-slate-200 rounded-lg p-6">
            <h3 class="font-semibold text-slate-900 mb-4">Журнал диспетчера</h3>
            <div v-if="ticket.comments?.length" class="space-y-3">
              <div v-for="comment in ticket.comments" :key="comment.id" class="bg-slate-50 rounded-md p-3">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium text-slate-900">{{ comment.author }}</span>
                  <span class="text-xs text-slate-500">{{ formatDateTime(comment.created_at) }}</span>
                </div>
                <p class="text-sm text-slate-700">{{ comment.body }}</p>
              </div>
            </div>
            <p v-else class="text-sm text-slate-500">Комментариев пока нет</p>
          </div>
        </div>

        <div>
          <div class="bg-white border border-slate-200 rounded-lg p-6">
            <h3 class="font-semibold text-slate-900 mb-4">Использованные материалы</h3>
            <div class="flex items-center justify-between text-sm">
              <span class="text-slate-700">Оптический кабель</span>
              <span class="font-medium text-slate-900">{{ ticket.cable_used_meters }} м</span>
            </div>
            <p class="text-xs text-slate-500 mt-3">Списано с инвентаря бригады при закрытии заявки</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
