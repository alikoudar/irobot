<template>
  <div class="chat-view">
    <ChatInterface />
  </div>
</template>

<script setup>
/**
 * Chat.vue
 * 
 * Vue principale du chatbot IroBot.
 * Wrapper simple autour du composant ChatInterface.
 * 
 * Sprint 8 - Phase 3 : Views & Routing
 */
import { ChatInterface } from '@/components/chat'
</script>

<style scoped lang="scss">
.chat-view {
  height: calc(100vh - 64px); // Hauteur moins la navbar
  width: 100%;
  overflow: hidden;
}
</style>