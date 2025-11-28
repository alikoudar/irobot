<template>
  <div class="chat-interface">
    <!-- Sidebar des conversations -->
    <ConversationsSidebar
      :collapsed="sidebarCollapsed"
      @toggle="toggleSidebar"
      @select="handleSelectConversation"
      @new="handleNewConversation"
    />
    
    <!-- Zone principale du chat -->
    <div class="chat-main" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <ChatWindow
        @send="handleSendMessage"
        @cancel="handleCancelStreaming"
        @feedback="handleFeedback"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * ChatInterface.vue - ✅ CORRIGÉ Sprint 11
 * 
 * Interface principale du chatbot combinant :
 * - Sidebar des conversations (gauche)
 * - Fenêtre de chat (droite)
 * 
 * ✅ CORRECTIF : Passe explicitement conversation_id à sendMessage
 * 
 * Sprint 8 - Phase 2 : Composants Chat
 * Sprint 11 - Correction conversation_id
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { ElMessage } from 'element-plus'

import ConversationsSidebar from './ConversationsSidebar.vue'
import ChatWindow from './ChatWindow.vue'

// ============================================================================
// STORES & ROUTER
// ============================================================================

const chatStore = useChatStore()
const route = useRoute()
const router = useRouter()

// ============================================================================
// STATE
// ============================================================================

const sidebarCollapsed = ref(false)

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  // Restaurer l'état du sidebar
  const savedState = localStorage.getItem('chat-sidebar-collapsed')
  if (savedState !== null) {
    sidebarCollapsed.value = savedState === 'true'
  }
  
  // Charger les conversations
  await chatStore.fetchConversations()
  
  // 🔥 AJOUT v2.3 : Restaurer la dernière conversation active
  const conversationId = route.query.conversation
  if (conversationId) {
    // Si conversation dans l'URL, la charger
    await chatStore.fetchConversation(conversationId)
  } else {
    // Sinon, restaurer la dernière conversation active depuis localStorage
    await chatStore.restoreLastConversation()
  }
})

onUnmounted(() => {
  // Pas besoin avec l'endpoint non-streaming
  // if (chatStore.isSending) {
  //   chatStore.cancelStreaming()
  // }
})

// ============================================================================
// WATCHERS
// ============================================================================

// Synchroniser l'URL avec la conversation courante
watch(() => chatStore.currentConversation, (conversation) => {
  if (conversation?.id) {
    router.replace({
      query: { ...route.query, conversation: conversation.id }
    })
  }
}, { deep: true })

// ============================================================================
// METHODS
// ============================================================================

/**
 * Basculer le sidebar
 */
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('chat-sidebar-collapsed', sidebarCollapsed.value)
}

/**
 * Sélectionner une conversation
 */
async function handleSelectConversation(conversationId) {
  if (chatStore.currentConversation?.id === conversationId) {
    return
  }
  
  await chatStore.fetchConversation(conversationId)
}

/**
 * Créer une nouvelle conversation
 */
function handleNewConversation() {
  chatStore.createConversation()
  
  // Retirer le paramètre conversation de l'URL
  const query = { ...route.query }
  delete query.conversation
  router.replace({ query })
}

/**
 * Envoyer un message
 * 
 * ✅ CORRECTIF Sprint 11 v2 : Lecture dynamique de conversation_id
 * Le store lit directement currentConversation.value?.id au moment de l'envoi
 */
async function handleSendMessage(message) {
  if (!message?.trim()) return
  
  // ✅ SIMPLIFICATION : Ne plus capturer l'ID ici
  // Le store lira currentConversation.value?.id directement
  console.log('🔍 [handleSendMessage] Envoi message...')
  console.log('🔍 [handleSendMessage] Conversation active:', chatStore.currentConversation?.id)
  
  // ✅ SIMPLIFICATION : Ne plus passer conversationId en paramètre
  await chatStore.sendMessage(message)
  
  // Recharger les conversations pour avoir le nouveau titre
  if (!chatStore.currentConversation?.title || 
      chatStore.currentConversation?.title === 'Nouvelle conversation') {
    await chatStore.fetchConversations()
  }
}

/**
 * Annuler le streaming
 */
function handleCancelStreaming() {
  chatStore.cancelStreaming()
}

/**
 * Ajouter un feedback
 */
async function handleFeedback({ messageId, rating, comment }) {
  const success = await chatStore.addFeedback(messageId, rating, comment)
  
  if (success) {
    ElMessage.success('Merci pour votre retour !')
  }
}
</script>

<style scoped lang="scss">
.chat-interface {
  display: flex;
  height: 100%;
  width: 100%;
  background: var(--bg-color);
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0; // Éviter le débordement
  transition: margin-left 0.3s ease;
}

// Responsive
@media (max-width: 768px) {
  .chat-interface {
    flex-direction: column;
  }
  
  .chat-main {
    height: calc(100% - 60px);
  }
}
</style>