<template>
  <router-view v-if="isPublic" />
  <AppLayout v-else />
  <Toast />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Toast from 'primevue/toast'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const isPublic = computed(() => route.meta.public === true)
</script>
