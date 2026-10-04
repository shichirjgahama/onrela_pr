<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  ArcElement,
} from 'chart.js'
import { api } from '@/composables/useApi'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement)

const stats = ref({ new: 0, in_progress: 0, done_today: 0, brigades_active: 0 })
const chartData = ref<any>(null)
const loading = ref(false)

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    title: { display: true, text: 'Заявки за последние 7 дней', font: { size: 14 } },
  },
  scales: {
    y: { beginAtZero: true, ticks: { stepSize: 1 } },
  },
}

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const },
    title: { display: true, text: 'Распределение по статусам', font: { size: 14 } },
  },
}

const barChartData = ref<any>({ labels: [], datasets: [] })
const doughnutChartData = ref<any>({ labels: [], datasets: [] })

const statusColors = ['#3b82f6', '#f59e0b', '#8b5cf6', '#10b981', '#ef4444']

onMounted(async () => {
  loading.value = true
  try {
    const [statsRes, chartRes] = await Promise.all([
      api.get('/tickets/stats'),
      api.get('/tickets/stats/chart'),
    ])
    stats.value = statsRes.data
    chartData.value = chartRes.data

    const dailyLabels = chartRes.data.daily.labels.map((d: string) => {
      const date = new Date(d)
      return date.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric' })
    })

    barChartData.value = {
      labels: dailyLabels,
      datasets: [{
        label: 'Заявок',
        data: chartRes.data.daily.values,
        backgroundColor: '#3b82f6',
        borderRadius: 6,
      }],
    }

    doughnutChartData.value = {
      labels: chartRes.data.by_status.labels,
      datasets: [{
        data: chartRes.data.by_status.values,
        backgroundColor: statusColors.slice(0, chartRes.data.by_status.labels.length),
      }],
    }
  } catch (e) {
    console.error('Ошибка загрузки статистики', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold text-neutral-900 mb-2">Дашборд</h1>
    <p class="text-sm text-neutral-500 mb-8">
      Сводка по работе службы на {{ new Date().toLocaleDateString('ru-RU') }}
    </p>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-5 mb-8">
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div class="text-sm text-neutral-500 mb-2">Новые заявки</div>
        <div class="text-3xl font-semibold text-blue-600">{{ stats.new }}</div>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div class="text-sm text-neutral-500 mb-2">В работе</div>
        <div class="text-3xl font-semibold text-amber-600">{{ stats.in_progress }}</div>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div class="text-sm text-neutral-500 mb-2">Закрыто сегодня</div>
        <div class="text-3xl font-semibold text-emerald-600">{{ stats.done_today }}</div>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div class="text-sm text-neutral-500 mb-2">Бригад на выезде</div>
        <div class="text-3xl font-semibold text-purple-600">{{ stats.brigades_active }}</div>
      </div>
    </div>

    <div v-if="!loading" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div style="height: 280px;">
          <Bar :data="barChartData" :options="barOptions" />
        </div>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div style="height: 280px;">
          <Doughnut :data="doughnutChartData" :options="doughnutOptions" />
        </div>
      </div>
    </div>

    <div v-else class="text-neutral-500">Загрузка...</div>
  </div>
</template>
