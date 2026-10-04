<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Button from 'primevue/button'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const mobileOpen = ref(false)

const roleLabels: Record<string, string> = {
  dispatcher: 'Диспетчер',
  brigade_lead: 'Бригадир',
  engineer: 'Монтажник',
  warehouse_manager: 'Кладовщик',
  admin: 'Администратор',
}

function logout() {
  auth.logout()
  router.push('/login')
}

function toggleMobile() {
  mobileOpen.value = !mobileOpen.value
}

function closeMobile() {
  mobileOpen.value = false
}

const navItems = [
  { label: 'Дашборд', icon: 'pi pi-home', to: '/' },
  { label: 'Заявки', icon: 'pi pi-ticket', to: '/tickets' },
  { label: 'Бригады', icon: 'pi pi-users', to: '/brigades' },
  { label: 'Склад', icon: 'pi pi-warehouse', to: '/warehouse' },
  { label: 'Клиенты', icon: 'pi pi-id-card', to: '/clients' },
  { label: 'Ключи', icon: 'pi pi-key', to: '/keys' },
]
</script>

<template>
  <!-- Бургер-кнопка для мобильных -->
  <button
    class="lg:hidden fixed top-3 left-3 z-50 bg-white border border-slate-200 rounded-lg p-2 shadow-md"
    @click="toggleMobile"
  >
    <i :class="mobileOpen ? 'pi pi-times' : 'pi pi-bars'" class="text-xl text-neutral-700"></i>
  </button>

  <!-- Оверлей для мобильных -->
  <div
    v-if="mobileOpen"
    class="lg:hidden fixed inset-0 bg-black/40 z-40"
    @click="closeMobile"
  ></div>

  <!-- Сайдбар -->
  <aside
    class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200 flex flex-col h-full transform transition-transform duration-200 ease-in-out"
    :class="mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'"
  >
    <div class="p-5 border-b border-slate-200">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-slate-800 text-white flex items-center justify-center font-bold text-sm">ISP</div>
        <div>
<div class="font-semibold text-neutral-900 text-sm">ISP ERP</div>
          <div class="text-xs text-neutral-500">Провайдер «Онрела»</div>
        </div>
      </div>
    </div>

    <nav class="flex-1 p-3 overflow-y-auto">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-neutral-700 hover:bg-slate-100 transition mb-0.5"
        active-class="!bg-slate-800 !text-white"
        @click="closeMobile"
      >
        <i :class="item.icon" class="text-base" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="p-4 border-t border-slate-200">
      <div class="text-sm font-medium text-neutral-900">{{ auth.user?.full_name }}</div>
      <div class="text-xs text-neutral-500 mb-2">{{ auth.user ? roleLabels[auth.user.role] || auth.user.role : '' }}</div>
      <Button label="Выйти" icon="pi pi-sign-out" severity="secondary" outlined size="small" class="w-full" @click="logout" />
    </div>
  </aside>
</template>
