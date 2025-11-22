<template>
  <router-view v-slot="{ Component, route }">
    <!-- Pages sans layout (login, change-password) -->
    <component
      v-if="route.meta.noLayout"
      :is="Component"
    />
    <!-- Pages avec layout (dashboard, admin, etc.) -->
    <AppLayout v-else>
      <component :is="Component" />
    </AppLayout>
  </router-view>
</template>

<script setup>
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
</style>