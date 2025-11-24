<template>
  <aside class="conversations-sidebar" :class="{ collapsed }">
    <!-- Header -->
    <div class="sidebar-header">
      <template v-if="!collapsed">
        <h2 class="sidebar-title">Conversations</h2>
        <el-tooltip content="Réduire" placement="right">
          <el-button
            class="collapse-btn"
            :icon="DArrowLeft"
            text
            @click="$emit('toggle')"
          />
        </el-tooltip>
      </template>
      <template v-else>
        <el-tooltip content="Développer" placement="right">
          <el-button
            class="expand-btn"
            :icon="DArrowRight"
            text
            @click="$emit('toggle')"
          />
        </el-tooltip>
      </template>
    </div>
    
    <!-- Bouton nouvelle conversation -->
    <div class="new-conversation" v-if="!collapsed">
      <el-button
        type="primary"
        class="new-btn"
        :icon="Plus"
        @click="$emit('new')"
      >
        Nouvelle conversation
      </el-button>
    </div>
    <div class="new-conversation-collapsed" v-else>
      <el-tooltip content="Nouvelle conversation" placement="right">
        <el-button
          type="primary"
          :icon="Plus"
          circle
          @click="$emit('new')"
        />
      </el-tooltip>
    </div>
    
    <!-- Recherche -->
    <div class="search-box" v-if="!collapsed">
      <el-input
        v-model="searchQuery"
        placeholder="Rechercher..."
        :prefix-icon="Search"
        clearable
        size="default"
        @input="handleSearch"
      />
    </div>
    
    <!-- Liste des conversations -->
    <div class="conversations-list" v-if="!collapsed">
      <!-- Loading -->
      <div v-if="chatStore.isLoading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>
      
      <!-- Empty state -->
      <div v-else-if="filteredConversations.length === 0" class="empty-state">
        <el-icon :size="48" color="#d9d9d9"><ChatDotSquare /></el-icon>
        <p>Aucune conversation</p>
        <span>Commencez une nouvelle conversation</span>
      </div>
      
      <!-- Conversations -->
      <div v-else class="conversations-scroll">
        <!-- Conversations du jour -->
        <div v-if="todayConversations.length > 0" class="conversation-group">
          <div class="group-title">Aujourd'hui</div>
          <ConversationItem
            v-for="conv in todayConversations"
            :key="conv.id"
            :conversation="conv"
            :active="isActive(conv.id)"
            @click="$emit('select', conv.id)"
            @delete="handleDelete"
            @archive="handleArchive"
            @rename="handleRename"
          />
        </div>
        
        <!-- Conversations de la semaine -->
        <div v-if="weekConversations.length > 0" class="conversation-group">
          <div class="group-title">Cette semaine</div>
          <ConversationItem
            v-for="conv in weekConversations"
            :key="conv.id"
            :conversation="conv"
            :active="isActive(conv.id)"
            @click="$emit('select', conv.id)"
            @delete="handleDelete"
            @archive="handleArchive"
            @rename="handleRename"
          />
        </div>
        
        <!-- Conversations plus anciennes -->
        <div v-if="olderConversations.length > 0" class="conversation-group">
          <div class="group-title">Plus anciennes</div>
          <ConversationItem
            v-for="conv in olderConversations"
            :key="conv.id"
            :conversation="conv"
            :active="isActive(conv.id)"
            @click="$emit('select', conv.id)"
            @delete="handleDelete"
            @archive="handleArchive"
            @rename="handleRename"
          />
        </div>
      </div>
    </div>
    
    <!-- Liste réduite (icônes uniquement) -->
    <div class="conversations-list-collapsed" v-else>
      <el-tooltip
        v-for="conv in recentConversations"
        :key="conv.id"
        :content="conv.title"
        placement="right"
      >
        <div
          class="conversation-icon"
          :class="{ active: isActive(conv.id) }"
          @click="$emit('select', conv.id)"
        >
          <el-icon><ChatLineSquare /></el-icon>
        </div>
      </el-tooltip>
    </div>
    
    <!-- Footer avec toggle archives -->
    <div class="sidebar-footer" v-if="!collapsed">
      <el-checkbox
        v-model="showArchived"
        label="Afficher les archives"
        size="small"
        @change="handleToggleArchived"
      />
    </div>
  </aside>
</template>

<script setup>
/**
 * ConversationsSidebar.vue
 * 
 * Sidebar affichant la liste des conversations avec :
 * - Recherche
 * - Groupement par date
 * - Actions (renommer, archiver, supprimer)
 * 
 * Sprint 8 - Phase 2 : Composants Chat
 */
import { ref, computed, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Plus,
  Search,
  DArrowLeft,
  DArrowRight,
  ChatDotSquare,
  ChatLineSquare
} from '@element-plus/icons-vue'

import ConversationItem from './ConversationItem.vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle', 'select', 'new'])

// ============================================================================
// STORE
// ============================================================================

const chatStore = useChatStore()

// ============================================================================
// STATE
// ============================================================================

const searchQuery = ref('')
const showArchived = ref(false)

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Conversations filtrées par recherche
 */
const filteredConversations = computed(() => {
  let conversations = showArchived.value
    ? chatStore.conversations
    : chatStore.activeConversations
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    conversations = conversations.filter(c =>
      c.title?.toLowerCase().includes(query)
    )
  }
  
  return conversations
})

/**
 * Conversations du jour
 */
const todayConversations = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  return filteredConversations.value.filter(c => {
    const date = new Date(c.updated_at)
    return date >= today
  })
})

/**
 * Conversations de la semaine (hors aujourd'hui)
 */
const weekConversations = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)
  
  return filteredConversations.value.filter(c => {
    const date = new Date(c.updated_at)
    return date < today && date >= weekAgo
  })
})

/**
 * Conversations plus anciennes
 */
const olderConversations = computed(() => {
  const weekAgo = new Date()
  weekAgo.setDate(weekAgo.getDate() - 7)
  weekAgo.setHours(0, 0, 0, 0)
  
  return filteredConversations.value.filter(c => {
    const date = new Date(c.updated_at)
    return date < weekAgo
  })
})

/**
 * Conversations récentes (pour mode réduit)
 */
const recentConversations = computed(() => {
  return filteredConversations.value.slice(0, 10)
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Vérifier si une conversation est active
 */
function isActive(conversationId) {
  return chatStore.currentConversation?.id === conversationId
}

/**
 * Rechercher dans les conversations
 */
function handleSearch() {
  // Debounce géré par le watcher si nécessaire
}

/**
 * Basculer l'affichage des archives
 */
function handleToggleArchived(value) {
  chatStore.setFilters({ include_archived: value })
}

/**
 * Supprimer une conversation
 */
async function handleDelete(conversationId) {
  try {
    await ElMessageBox.confirm(
      'Êtes-vous sûr de vouloir supprimer cette conversation ?',
      'Confirmation',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'warning'
      }
    )
    
    await chatStore.deleteConversation(conversationId)
    
  } catch (error) {
    // L'utilisateur a annulé
  }
}

/**
 * Archiver/désarchiver une conversation
 */
async function handleArchive(conversationId, isArchived) {
  await chatStore.archiveConversation(conversationId, !isArchived)
}

/**
 * Renommer une conversation
 */
async function handleRename(conversationId, currentTitle) {
  try {
    const { value } = await ElMessageBox.prompt(
      'Nouveau titre de la conversation',
      'Renommer',
      {
        confirmButtonText: 'Valider',
        cancelButtonText: 'Annuler',
        inputValue: currentTitle,
        inputPattern: /^.{1,100}$/,
        inputErrorMessage: 'Le titre doit faire entre 1 et 100 caractères'
      }
    )
    
    if (value && value !== currentTitle) {
      await chatStore.updateConversationTitle(conversationId, value)
    }
    
  } catch (error) {
    // L'utilisateur a annulé
  }
}
</script>

<style scoped lang="scss">
.conversations-sidebar {
  width: 280px;
  height: 100%;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  
  &.collapsed {
    width: 60px;
  }
}

.sidebar-header {
  height: 56px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  
  .sidebar-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }
  
  .collapse-btn,
  .expand-btn {
    color: var(--text-secondary);
    
    &:hover {
      color: var(--primary-color);
    }
  }
}

.new-conversation {
  padding: 12px 16px;
  
  .new-btn {
    width: 100%;
    border-radius: 8px;
    font-weight: 500;
  }
}

.new-conversation-collapsed {
  padding: 12px;
  display: flex;
  justify-content: center;
}

.search-box {
  padding: 0 16px 12px;
  
  :deep(.el-input__wrapper) {
    border-radius: 8px;
  }
}

.conversations-list {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.loading-state {
  padding: 16px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
  
  p {
    margin: 12px 0 4px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-secondary);
  }
  
  span {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.conversations-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  
  &::-webkit-scrollbar {
    width: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 2px;
  }
}

.conversation-group {
  margin-bottom: 8px;
  
  .group-title {
    padding: 8px 16px 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-tertiary);
  }
}

.conversations-list-collapsed {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.conversation-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  
  &:hover {
    background: var(--hover-bg);
    color: var(--primary-color);
  }
  
  &.active {
    background: var(--active-bg);
    color: var(--primary-color);
  }
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  
  :deep(.el-checkbox__label) {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

// Responsive
@media (max-width: 768px) {
  .conversations-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 100;
    height: 100vh;
    
    &.collapsed {
      width: 0;
      overflow: hidden;
    }
  }
}
</style>