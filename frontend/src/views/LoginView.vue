<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { api } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const username = ref('')
const password = ref('')
const loading = ref(false)

const demoAccounts = [
  { username: 'dispatcher', password: 'disp123', role: 'Диспетчер', severity: 'info' },
  { username: 'engineer1', password: 'eng123', role: 'Монтажник', severity: 'success' },
  { username: 'warehouse', password: 'wh123', role: 'Кладовщик', severity: 'warn' },
  { username: 'admin', password: 'admin123', role: 'Администратор', severity: 'danger' },
]

function fillDemo(account: { username: string; password: string }) {
  username.value = account.username
  password.value = account.password
}

async function doLogin() {
  if (!username.value || !password.value) {
    toast.add({
      severity: 'warn',
      summary: 'Заполните поля',
      detail: 'Введите логин и пароль',
      life: 3000,
    })
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/auth/login', {
      username: username.value,
      password: password.value,
    })
    auth.login(data.user, data.access_token)
    router.push('/')
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Ошибка входа',
      detail: err?.response?.data?.detail || 'Не удалось войти в систему',
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-100 flex items-center justify-center p-6">
    <div class="w-full max-w-md">
      <div class="text-center mb-6">
        <div
          class="w-14 h-14 rounded-xl bg-slate-800 text-white flex items-center justify-center font-bold text-lg mx-auto mb-3"
        >
          ISP
        </div>
        <h1 class="text-xl font-semibold text-neutral-900">ISP ERP</h1>
        <p class="text-sm text-neutral-500">Система учёта заявок и складских остатков</p>
      </div>

      <div class="bg-white rounded-lg border border-slate-200 p-4">
        <div class="space-y-3">
          <div class="flex flex-col gap-1">
            <label class="text-xs text-neutral-500" for="login">Логин</label>
            <InputText id="login" v-model="username" placeholder="dispatcher" autocomplete="username" fluid />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs text-neutral-500" for="password">Пароль</label>
            <Password
              input-id="password"
              v-model="password"
              placeholder="••••••••"
              :feedback="false"
              toggle-mask
              autocomplete="current-password"
              fluid
              @keyup.enter="doLogin"
            />
          </div>
          <Button
            class="w-full"
            label="Войти"
            icon="pi pi-sign-in"
            :loading="loading"
            @click="doLogin"
          />
        </div>
      </div>

      <div class="bg-white rounded-lg border border-slate-200 p-4 mt-3">
        <div class="text-xs text-neutral-500 mb-2">Учебные учётные записи (нажмите для подстановки)</div>
        <div class="flex flex-col gap-1.5">
          <button
            v-for="acc in demoAccounts"
            :key="acc.username"
            class="w-full flex items-center justify-between px-3 py-2 rounded-md border border-slate-200 hover:bg-slate-50 transition"
            @click="fillDemo(acc)"
          >
            <span class="font-mono text-xs text-neutral-700">{{ acc.username }} / {{ acc.password }}</span>
            <Tag :value="acc.role" :severity="acc.severity" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>