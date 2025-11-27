<template>
  <div class="chat-window">
    <!-- Header -->
    <div class="chat-header" v-if="chatStore.currentConversation">
      <div class="header-info">
        <h3 class="conversation-title">
          {{ chatStore.currentConversation.title || 'Nouvelle conversation' }}
        </h3>
        <span class="message-count">
          {{ chatStore.messages.length }} message{{ chatStore.messages.length > 1 ? 's' : '' }}
        </span>
      </div>
      
      <div class="header-actions">
        <el-dropdown trigger="click" @command="handleConversationAction">
          <el-button :icon="MoreFilled" circle text />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename" :icon="Edit">
                Renommer
              </el-dropdown-item>
              <el-dropdown-item 
                :command="chatStore.currentConversation.is_archived ? 'unarchive' : 'archive'"
                :icon="chatStore.currentConversation.is_archived ? FolderOpened : Folder"
              >
                {{ chatStore.currentConversation.is_archived ? 'Désarchiver' : 'Archiver' }}
              </el-dropdown-item>
              <el-dropdown-item command="export" :icon="Download">
                Exporter
              </el-dropdown-item>
              <el-dropdown-item command="delete" :icon="Delete" divided>
                Supprimer
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- Messages container -->
    <div ref="messagesContainer" class="messages-container">
      <!-- État vide -->
      <div v-if="chatStore.messages.length === 0 && !chatStore.isGenerating" class="welcome-state">
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
          />
        </TransitionGroup>
        
        <!-- 
          ✅ SIMPLIFIÉ : Un seul indicateur pendant la génération
          Visible UNIQUEMENT pendant isGenerating
        -->
        <Transition name="fade">
          <div v-if="chatStore.isGenerating" class="generating-bubble">
            <div class="generating-avatar">
              <el-icon :size="22"><ChatDotRound /></el-icon>
            </div>
            <div class="generating-content">
              <div class="generating-header">
                <span class="generating-label">IroBot</span>
              </div>
              <div class="generating-body">
                <span class="generating-text">IroBot réfléchit</span>
                <span class="generating-dots">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </span>
              </div>
            </div>
          </div>
        </Transition>
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
      <!-- Input -->
      <div class="input-wrapper">
        <el-input
          ref="inputRef"
          v-model="inputMessage"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 5 }"
          placeholder="Posez votre question..."
          :disabled="chatStore.isGenerating"
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
              :loading="chatStore.isGenerating"
              @click="handleSend"
            />
          </el-tooltip>
        </div>
      </div>
      
      <p class="input-hint">
        <el-icon><InfoFilled /></el-icon>
        Appuyez sur Entrée pour envoyer, Maj+Entrée pour un retour à la ligne
      </p>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatWindow.vue - VERSION SIMPLIFIÉE
 * 
 * Plus de gestion SSE complexe !
 * Simple indicateur pendant isGenerating.
 * 
 * Sprint 9 - Correction: Utilisation endpoint non-streaming
 */
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  MoreFilled,
  Edit,
  Folder,
  FolderOpened,
  Download,
  Delete,
  ArrowDown,
  Promotion,
  InfoFilled
} from '@element-plus/icons-vue'

import MessageBubble from './MessageBubble.vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  conversationId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['send', 'feedback'])

// ============================================================================
// STATE
// ============================================================================

const chatStore = useChatStore()
const inputMessage = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)
const showScrollButton = ref(false)

// Constantes
const MAX_LENGTH = 10000
const WARN_THRESHOLD = 9000

// Suggestions
const suggestions = [
  'Comment obtenir un prêt à la BEAC ?',
  'Quels sont les taux d\'intérêt actuels ?',
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
         !chatStore.isGenerating
})

const sendTooltip = computed(() => {
  if (chatStore.isGenerating) return 'Génération en cours...'
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

// Détecter le scroll pour afficher le bouton
watch(() => messagesContainer.value, (container) => {
  if (container) {
    container.addEventListener('scroll', handleScroll)
  }
}, { immediate: true })

// ============================================================================
// METHODS
// ============================================================================

function isNearBottom() {
  const container = messagesContainer.value
  if (!container) return true
  
  const threshold = 100
  return container.scrollHeight - container.scrollTop - container.clientHeight < threshold
}

function handleScroll() {
  showScrollButton.value = !isNearBottom()
}

function scrollToBottom() {
  const container = messagesContainer.value
  if (container) {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth'
    })
  }
}

async function handleSend() {
  if (!canSend.value) return
  
  const message = inputMessage.value.trim()
  inputMessage.value = ''
  
  emit('send', message)
  
  await nextTick()
  scrollToBottom()
}

function handleNewLine(event) {
  // Laisser le comportement par défaut (Maj+Entrée ajoute \n)
}

function handleSuggestionClick(suggestion) {
  inputMessage.value = suggestion
  handleSend()
}

function handleFeedback(data) {
  emit('feedback', data)
}

async function handleConversationAction(command) {
  const conversationId = chatStore.currentConversation?.id
  
  if (!conversationId) return
  
  switch (command) {
    case 'rename':
      await handleRename(conversationId)
      break
    case 'archive':
      await chatStore.archiveConversation(conversationId, true)
      break
    case 'unarchive':
      await chatStore.archiveConversation(conversationId, false)
      break
    case 'export':
      await handleExport(conversationId)
      break
    case 'delete':
      await handleDelete(conversationId)
      break
  }
}

async function handleRename(conversationId) {
  try {
    const { value } = await ElMessageBox.prompt(
      'Nouveau titre de la conversation',
      'Renommer',
      {
        confirmButtonText: 'Enregistrer',
        cancelButtonText: 'Annuler',
        inputValue: chatStore.currentConversation?.title,
        inputPattern: /.+/,
        inputErrorMessage: 'Le titre ne peut pas être vide'
      }
    )
    
    if (value) {
      await chatStore.updateConversationTitle(conversationId, value)
    }
  } catch (error) {
    // Annulé
  }
}

async function handleExport(conversationId) {
  ElMessage.info('Export en cours...')
  // TODO: Implémenter l'export
}

async function handleDelete(conversationId) {
  try {
    await ElMessageBox.confirm(
      'Cette action est irréversible. Continuer ?',
      'Supprimer la conversation',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'warning'
      }
    )
    
    await chatStore.deleteConversation(conversationId)
  } catch (error) {
    // Annulé
  }
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

// ✅ INDICATEUR "IROBOT RÉFLÉCHIT..."
.generating-bubble {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  animation: fadeIn 0.3s ease;
  
  .generating-avatar {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #005ca9 0%, #0077cc 100%);
    border-radius: 12px;
    color: white;
    box-shadow: 0 2px 8px rgba(0, 92, 169, 0.3);
  }
  
  .generating-content {
    display: flex;
    flex-direction: column;
    max-width: 75%;
    min-width: 200px;
  }
  
  .generating-header {
    margin-bottom: 6px;
    
    .generating-label {
      font-size: 14px;
      font-weight: 600;
      color: #1f2937;
    }
  }
  
  .generating-body {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 20px 20px 20px 4px;
    padding: 14px 18px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    display: flex;
    align-items: center;
    gap: 8px;
    
    .generating-text {
      font-size: 14px;
      color: #6b7280;
    }
    
    .generating-dots {
      display: flex;
      gap: 4px;
      
      .dot {
        width: 6px;
        height: 6px;
        background: #005ca9;
        border-radius: 50%;
        animation: bounce 1.4s infinite;
        
        &:nth-child(1) {
          animation-delay: 0s;
        }
        
        &:nth-child(2) {
          animation-delay: 0.2s;
        }
        
        &:nth-child(3) {
          animation-delay: 0.4s;
        }
      }
    }
  }
}

@keyframes bounce {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-6px);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// Scroll button
.scroll-bottom-btn {
  position: absolute;
  bottom: 20px;
  right: 20px;
  box-shadow: var(--shadow-md);
  z-index: 10;
}

// Input container
.input-container {
  padding: 16px 20px;
  background: var(--card-bg);
  border-top: 1px solid var(--border-color);
}

.input-wrapper {
  position: relative;
  
  .input-actions {
    position: absolute;
    bottom: 8px;
    right: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .char-count {
    font-size: 12px;
    color: var(--text-tertiary);
    
    &.warning {
      color: #f59e0b;
    }
    
    &.error {
      color: #ef4444;
      font-weight: 600;
    }
  }
  
  .send-btn {
    width: 36px;
    height: 36px;
  }
  
  :deep(.el-textarea__inner) {
    padding-right: 120px !important;
    padding-bottom: 12px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.6;
  }
}

.input-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
  
  .el-icon {
    font-size: 14px;
  }
}

// Transitions
.message-enter-active,
.message-leave-active {
  transition: all 0.3s ease;
}

.message-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.message-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>