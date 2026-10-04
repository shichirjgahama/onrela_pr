import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/tickets', name: 'tickets', component: () => import('@/views/TicketsView.vue') },
    { path: '/tickets/:id', name: 'ticket-detail', component: () => import('@/views/TicketDetailView.vue') },
    { path: '/brigades', name: 'brigades', component: () => import('@/views/BrigadesView.vue') },
    { path: '/warehouse', name: 'warehouse', component: () => import('@/views/WarehouseView.vue') },
    { path: '/clients', name: 'clients', component: () => import('@/views/ClientsView.vue') },
    { path: '/keys', name: 'keys', component: () => import('@/views/KeysView.vue') },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return { name: 'login' }
  if (to.meta.public && auth.isLoggedIn) return { name: 'dashboard' }
})

export default router
