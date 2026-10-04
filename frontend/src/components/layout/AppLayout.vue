<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
</script>

<template>
  <div class="flex h-screen bg-slate-50 overflow-hidden">
    <AppSidebar />
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0 px-4 lg:px-8 py-6">
      <router-view />
    </main>
  </div>
</template>
