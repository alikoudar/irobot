<template>
  <div class="chat-window">
    <!-- Header de la conversation -->
    <div class="chat-header" v-if="chatStore.currentConversation">
      <div class="header-info">
        <h3 class="conversation-title">
          {{ chatStore.currentConversation.title || 'Nouvelle conversation' }}
        </h3>
        <span class="message-count" v-if="chatStore.messages.length">
          {{ chatStore.messages.length }} messages
        </span>
      </div>
      <div class="header-actions">
        <el-tooltip content="Partager" placement="bottom">
          <el-button :icon="Share" text circle disabled />
        </el-tooltip>
        <el-tooltip content="Options" placement="bottom">
          <el-dropdown trigger="click" @command="handleHeaderCommand">
            <el-button :icon="MoreFilled" text circle />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename" :icon="Edit">
                  Renommer
                </el-dropdown-item>
                <el-dropdown-item command="export" :icon="Download">
                  Exporter
                </el-dropdown-item>
                <el-dropdown-item command="delete" :icon="Delete" divided>
                  <span style="color: var(--error-color)">Supprimer</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-tooltip>
      </div>
    </div>
    
    <!-- Zone des messages -->
    <div class="messages-container" ref="messagesContainer">
      <!-- État vide -->
      <div v-if="!chatStore.messages.length && !chatStore.isStreaming" class="welcome-state">
        <div class="welcome-icon">
          <el-icon :size="64"><ChatDotRound /></el-icon>
        </div>
        <h2>Bienvenue sur IroBot</h2>
        <p>Je suis votre assistant pour les documents de la BEAC.</p>
        <p class="hint">Posez-moi une question pour commencer.</p>
        
        <!-- Suggestions -->
        <div class="suggestions">
          <p class="suggestions-title">Exemples de questions :</p>
          <div class="suggestion-chips">
            <el-button
              v-for="suggestion in suggestions"
              :key="suggestion"
              class="suggestion-chip"
              round
              @click="handleSuggestionClick(suggestion)"
            >
              {{ suggestion }}
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- Messages -->
      <div v-else class="messages-list">
        <TransitionGroup name="message">
          <MessageBubble
            v-for="message in chatStore.sortedMessages"
            :key="message.id"
            :message="message"
            @feedback="handleFeedback"
            @copy="handleCopy"
            @regenerate="handleRegenerate"
          />
        </TransitionGroup>
        
        <!-- Indicateur de streaming -->
        <div v-if="chatStore.isStreaming" class="streaming-indicator">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span class="typing-text">IroBot réfléchit...</span>
        </div>
      </div>
      
      <!-- Scroll to bottom button -->
      <Transition name="fade">
        <el-button
          v-if="showScrollButton"
          class="scroll-bottom-btn"
          :icon="ArrowDown"
          circle
          @click="scrollToBottom"
        />
      </Transition>
    </div>
    
    <!-- Zone de saisie -->
    <div class="input-container">
      <!-- Annuler le streaming -->
      <Transition name="fade">
        <el-button
          v-if="chatStore.isStreaming"
          class="cancel-btn"
          type="danger"
          plain
          :icon="VideoPause"
          @click="$emit('cancel')"
        >
          Arrêter la génération
        </el-button>
      </Transition>
      
      <!-- Input -->
      <div class="input-wrapper">
        <el-input
          ref="inputRef"
          v-model="inputMessage"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 5 }"
          placeholder="Posez votre question..."
          :disabled="chatStore.isStreaming"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.exact="handleNewLine"
        />
        <div class="input-actions">
          <span class="char-count" :class="{ warning: isNearLimit, error: isOverLimit }">
            {{ inputMessage.length }} / 10000
          </span>
          <el-tooltip :content="sendTooltip" placement="top">
            <el-button
              class="send-btn"
              type="primary"
              :icon="Promotion"
              circle
              :disabled="!canSend"
              :loading="chatStore.isSending && !chatStore.isStreaming"
              @click="handleSend"
            />
          </el-tooltip>
        </div>
      </div>
      
      <p class="input-hint">
        <el-icon><InfoFilled /></el-icon>
        Appuyez sur Entrée pour envoyer, Maj+Entrée pour un saut de ligne
      </p>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatWindow.vue
 * 
 * Fenêtre principale de chat avec :
 * - Zone de messages scrollable
 * - Input de saisie avec validation
 * - Indicateurs de streaming
 * 
 * Sprint 8 - Phase 2 : Composants Chat
 */
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Promotion,
  ArrowDown,
  VideoPause,
  MoreFilled,
  Share,
  Edit,
  Download,
  Delete,
  InfoFilled
} from '@element-plus/icons-vue'

import MessageBubble from './MessageBubble.vue'

// ============================================================================
// EMITS
// ============================================================================

const emit = defineEmits(['send', 'cancel', 'feedback'])

// ============================================================================
// STORE
// ============================================================================

const chatStore = useChatStore()

// ============================================================================
// REFS
// ============================================================================

const messagesContainer = ref(null)
const inputRef = ref(null)
const inputMessage = ref('')
const showScrollButton = ref(false)

// ============================================================================
// CONSTANTS
// ============================================================================

const MAX_LENGTH = 10000
const WARN_THRESHOLD = 9000

const suggestions = [
  'Quelle est la procédure pour ouvrir un compte ?',
  'Quelles sont les conditions des lettres circulaires ?',
  'Comment fonctionne le système de paiement ?'
]

// ============================================================================
// COMPUTED
// ============================================================================

const isNearLimit = computed(() => {
  return inputMessage.value.length >= WARN_THRESHOLD && inputMessage.value.length < MAX_LENGTH
})

const isOverLimit = computed(() => {
  return inputMessage.value.length > MAX_LENGTH
})

const canSend = computed(() => {
  return inputMessage.value.trim().length > 0 &&
         inputMessage.value.length <= MAX_LENGTH &&
         !chatStore.isSending &&
         !chatStore.isStreaming
})

const sendTooltip = computed(() => {
  if (chatStore.isStreaming) return 'Génération en cours...'
  if (isOverLimit.value) return 'Message trop long'
  if (!inputMessage.value.trim()) return 'Entrez un message'
  return 'Envoyer (Entrée)'
})

// ============================================================================
// WATCHERS
// ============================================================================

// Auto-scroll quand de nouveaux messages arrivent
watch(() => chatStore.messages.length, async () => {
  await nextTick()
  scrollToBottom()
})

// Auto-scroll pendant le streaming
watch(() => chatStore.streamingContent, async () => {
  await nextTick()
  if (isNearBottom()) {
    scrollToBottom()
  }
})

// Détecter le scroll pour afficher le bouton
watch(() => messagesContainer.value, (container) => {
  if (container) {
    container.addEventListener('scroll', handleScroll)
  }
}, { immediate: true })

// ============================================================================
// METHODS
// ============================================================================

/**
 * Vérifier si on est proche du bas
 */
function isNearBottom() {
  const container = messagesContainer.value
  if (!container) return true
  
  const threshold = 100
  return container.scrollHeight - container.scrollTop - container.clientHeight < threshold
}

/**
 * Gérer le scroll
 */
function handleScroll() {
  showScrollButton.value = !isNearBottom()
}

/**
 * Scroller vers le bas
 */
function scrollToBottom() {
  const container = messagesContainer.value
  if (container) {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth'
    })
  }
}

/**
 * Envoyer le message
 */
async function handleSend() {
  if (!canSend.value) return
  
  const message = inputMessage.value.trim()
  inputMessage.value = ''
  
  emit('send', message)
  
  await nextTick()
  scrollToBottom()
}

/**
 * Nouvelle ligne (Maj+Entrée)
 */
function handleNewLine(event) {
  // Laisser le comportement par défaut
}

/**
 * Cliquer sur une suggestion
 */
function handleSuggestionClick(suggestion) {
  inputMessage.value = suggestion
  inputRef.value?.focus()
}

/**
 * Gérer le feedback
 */
function handleFeedback(data) {
  emit('feedback', data)
}

/**
 * Copier un message
 */
async function handleCopy(content) {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('Copié dans le presse-papier')
  } catch (error) {
    ElMessage.error('Erreur lors de la copie')
  }
}

/**
 * Régénérer la dernière réponse
 */
async function handleRegenerate() {
  // Trouver le dernier message utilisateur
  const userMessages = chatStore.messages.filter(m => m.role === 'user')
  const lastUserMessage = userMessages[userMessages.length - 1]
  
  if (lastUserMessage) {
    emit('send', lastUserMessage.content)
  }
}

/**
 * Commandes du header
 */
async function handleHeaderCommand(command) {
  const conversation = chatStore.currentConversation
  if (!conversation) return
  
  switch (command) {
    case 'rename':
      try {
        const { value } = await ElMessageBox.prompt(
          'Nouveau titre',
          'Renommer la conversation',
          {
            inputValue: conversation.title,
            confirmButtonText: 'Valider',
            cancelButtonText: 'Annuler'
          }
        )
        if (value) {
          await chatStore.updateConversationTitle(conversation.id, value)
        }
      } catch {}
      break
      
    case 'export':
      exportConversation()
      break
      
    case 'delete':
      try {
        await ElMessageBox.confirm(
          'Supprimer cette conversation ?',
          'Confirmation',
          { type: 'warning' }
        )
        await chatStore.deleteConversation(conversation.id)
      } catch {}
      break
  }
}

/**
 * Exporter la conversation
 */
function exportConversation() {
  const conversation = chatStore.currentConversation
  const messages = chatStore.messages
  
  const content = messages.map(m => {
    const role = m.role === 'USER' ? 'Vous' : 'IroBot'
    return `[${role}]\n${m.content}\n`
  }).join('\n---\n\n')
  
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${conversation.title || 'conversation'}.txt`
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('Conversation exportée')
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  inputRef.value?.focus()
})
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--content-bg);
}

// Header
.chat-header {
  height: 56px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  
  .header-info {
    .conversation-title {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }
    
    .message-count {
      font-size: 12px;
      color: var(--text-tertiary);
    }
  }
  
  .header-actions {
    display: flex;
    gap: 4px;
  }
}

// Messages container
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  position: relative;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 3px;
  }
}

// Welcome state
.welcome-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px 20px;
  
  .welcome-icon {
    width: 100px;
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--primary-color) 0%, #0077cc 100%);
    border-radius: 24px;
    margin-bottom: 24px;
    
    .el-icon {
      color: white;
    }
  }
  
  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
  }
  
  p {
    margin: 0 0 4px;
    font-size: 15px;
    color: var(--text-secondary);
    
    &.hint {
      font-size: 13px;
      color: var(--text-tertiary);
    }
  }
  
  .suggestions {
    margin-top: 32px;
    
    .suggestions-title {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-tertiary);
      margin-bottom: 12px;
    }
    
    .suggestion-chips {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 8px;
    }
    
    .suggestion-chip {
      font-size: 13px;
      color: var(--primary-color);
      border-color: var(--primary-color);
      
      &:hover {
        background: var(--hover-bg);
      }
    }
  }
}

// Messages list
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

// Streaming indicator
.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  
  .typing-dots {
    display: flex;
    gap: 4px;
    
    span {
      width: 8px;
      height: 8px;
      background: var(--primary-color);
      border-radius: 50%;
      animation: typing 1.4s infinite;
      
      &:nth-child(2) {
        animation-delay: 0.2s;
      }
      
      &:nth-child(3) {
        animation-delay: 0.4s;
      }
    }
  }
  
  .typing-text {
    font-size: 13px;
    color: var(--text-secondary);
  }
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
}

// Scroll button
.scroll-bottom-btn {
  position: absolute;
  bottom: 20px;
  right: 20px;
  box-shadow: var(--shadow-md);
}

// Input container
.input-container {
  padding: 16px 20px;
  background: var(--card-bg);
  border-top: 1px solid var(--border-color);
  
  .cancel-btn {
    margin-bottom: 12px;
  }
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color 0.2s;
  
  &:focus-within {
    border-color: var(--primary-color);
  }
  
  :deep(.el-textarea__inner) {
    border: none;
    background: transparent;
    box-shadow: none;
    padding: 4px 0;
    resize: none;
    
    &:focus {
      box-shadow: none;
    }
  }
  
  .input-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .char-count {
      font-size: 11px;
      color: var(--text-tertiary);
      
      &.warning {
        color: var(--warning-color);
      }
      
      &.error {
        color: var(--error-color);
      }
    }
    
    .send-btn {
      width: 36px;
      height: 36px;
    }
  }
}

.input-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--text-tertiary);
  
  .el-icon {
    font-size: 12px;
  }
}

// Transitions
.message-enter-active {
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// Responsive
@media (max-width: 768px) {
  .messages-container {
    padding: 12px;
  }
  
  .input-container {
    padding: 12px;
  }
  
  .welcome-state {
    .suggestions {
      .suggestion-chips {
        flex-direction: column;
      }
    }
  }
}
</style>