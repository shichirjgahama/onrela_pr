import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

interface SessionUser {
  id: number
  username: string
  full_name: string
  role: string
}

const USER_KEY = 'erp_user'
const TOKEN_KEY = 'erp_token'

function readStored<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<SessionUser | null>(readStored<SessionUser>(USER_KEY))
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))

  const isLoggedIn = computed(() => !!user.value && !!token.value)
  const isDispatcher = computed(() => ['dispatcher', 'admin'].includes(user.value?.role ?? ''))
  const isBrigade = computed(() =>
    ['engineer', 'brigade_lead', 'admin'].includes(user.value?.role ?? ''),
  )
  const isWarehouse = computed(() =>
    ['warehouse_manager', 'admin'].includes(user.value?.role ?? ''),
  )

  function login(u: SessionUser, accessToken: string) {
    user.value = u
    token.value = accessToken
    localStorage.setItem(USER_KEY, JSON.stringify(u))
    localStorage.setItem(TOKEN_KEY, accessToken)
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(TOKEN_KEY)
  }

  return {
    user,
    token,
    isLoggedIn,
    isDispatcher,
    isBrigade,
    isWarehouse,
    login,
    logout,
  }
})