<template>
  <el-card class="conversation-card" :class="{ archived: conversation.is_archived }">
    <!-- Header -->
    <div class="card-header" @click="handleOpen">
      <div class="header-left">
        <el-icon class="conversation-icon">
          <ChatDotSquare />
        </el-icon>
        <div class="title-container">
          <h3 class="conversation-title">{{ conversation.title }}</h3>
          <el-tag
            v-if="conversation.is_archived"
            type="info"
            size="small"
            class="archived-tag"
          >
            <el-icon><FolderOpened /></el-icon>
            Archivée
          </el-tag>
        </div>
      </div>
      
      <!-- Menu actions -->
      <el-dropdown trigger="click" @command="handleCommand" @click.stop>
        <el-button :icon="MoreFilled" circle text />
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              :icon="conversation.is_archived ? FolderOpened : Folder"
              command="archive"
            >
              {{ conversation.is_archived ? 'Désarchiver' : 'Archiver' }}
            </el-dropdown-item>
            <el-dropdown-item
              :icon="Delete"
              command="delete"
            >
              Supprimer
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    
    <!-- Body -->
    <div class="card-body" @click="handleOpen">
      <!-- Dernier message -->
      <p v-if="lastMessage" class="last-message">
        <el-icon class="message-icon"><ChatLineSquare /></el-icon>
        {{ lastMessage }}
      </p>
      <p v-else class="last-message no-message">
        <el-icon class="message-icon"><Warning /></el-icon>
        Aucun message
      </p>
      
      <!-- Métadonnées -->
      <div class="card-meta">
        <span class="meta-item">
          <el-icon><Clock /></el-icon>
          {{ formatDate(conversation.updated_at) }}
        </span>
        
        <span class="meta-item">
          <el-icon><ChatLineSquare /></el-icon>
          {{ messageCountText }}
        </span>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * ConversationCard.vue
 * 
 * Carte d'affichage d'une conversation dans la grille
 * avec actions (archiver, supprimer)
 * 
 * Sprint 9 - Phase 3
 */
import { computed } from 'vue'
import {
  ChatDotSquare,
  ChatLineSquare,
  Clock,
  Folder,
  FolderOpened,
  Delete,
  MoreFilled,
  Warning
} from '@element-plus/icons-vue'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  conversation: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['open', 'archive', 'delete'])

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Dernier message (tronqué)
 */
const lastMessage = computed(() => {
  const preview = props.conversation.last_message_preview
  if (!preview) return null
  
  // Tronquer à 100 caractères
  return preview.length > 100
    ? preview.substring(0, 100) + '...'
    : preview
})

/**
 * Nombre de messages formaté
 */
const messageCountText = computed(() => {
  const count = props.conversation.message_count || 0
  return count === 1 ? '1 message' : `${count} messages`
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Formater la date en "il y a X"
 */
function formatDate(dateString) {
  if (!dateString) return 'Date inconnue'
  
  try {
    const date = new Date(dateString)
    return formatDistanceToNow(date, {
      addSuffix: true,
      locale: fr
    })
  } catch (error) {
    return 'Date invalide'
  }
}

/**
 * Ouvrir la conversation
 */
function handleOpen() {
  emit('open', props.conversation.id)
}

/**
 * Gérer les actions du menu
 */
function handleCommand(command) {
  if (command === 'archive') {
    emit('archive', {
      conversationId: props.conversation.id,
      archive: !props.conversation.is_archived
    })
  } else if (command === 'delete') {
    emit('delete', props.conversation.id)
  }
}
</script>

<style scoped lang="scss">
.conversation-card {
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 92, 169, 0.15);
    
    :deep(.el-card__body) {
      border-color: var(--el-color-primary);
    }
  }
  
  &.archived {
    opacity: 0.7;
    
    :deep(.el-card__body) {
      background: var(--el-fill-color-lighter);
    }
  }
  
  :deep(.el-card__body) {
    padding: 0;
    border: 2px solid transparent;
    transition: border-color 0.3s;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 16px 16px 12px 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    
    .header-left {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      flex: 1;
      
      .conversation-icon {
        font-size: 24px;
        color: var(--el-color-primary);
        flex-shrink: 0;
        margin-top: 2px;
      }
      
      .title-container {
        flex: 1;
        min-width: 0;
        
        .conversation-title {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          line-height: 1.4;
          
          // Tronquer avec ellipsis si trop long
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
        
        .archived-tag {
          margin-top: 6px;
        }
      }
    }
  }
  
  .card-body {
    padding: 16px;
    
    .last-message {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--el-text-color-regular);
      line-height: 1.6;
      
      // Tronquer à 3 lignes
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      
      .message-icon {
        font-size: 14px;
        margin-right: 6px;
        vertical-align: middle;
      }
      
      &.no-message {
        color: var(--el-text-color-placeholder);
        font-style: italic;
      }
    }
    
    .card-meta {
      display: flex;
      gap: 16px;
      
      .meta-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--el-text-color-secondary);
        
        .el-icon {
          font-size: 14px;
        }
      }
    }
  }
}
</style>