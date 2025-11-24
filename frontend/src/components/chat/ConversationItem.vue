<template>
  <div
    class="conversation-item"
    :class="{ active, archived: conversation.is_archived }"
    @click="$emit('click')"
  >
    <!-- Icône -->
    <div class="item-icon">
      <el-icon v-if="conversation.is_archived"><FolderOpened /></el-icon>
      <el-icon v-else><ChatLineSquare /></el-icon>
    </div>
    
    <!-- Contenu -->
    <div class="item-content">
      <div class="item-title">{{ conversation.title || 'Nouvelle conversation' }}</div>
      <div class="item-meta">
        <span class="item-date">{{ formatDate(conversation.updated_at) }}</span>
        <span v-if="conversation.message_count" class="item-count">
          {{ conversation.message_count }} msg
        </span>
      </div>
    </div>
    
    <!-- Actions -->
    <el-dropdown
      class="item-actions"
      trigger="click"
      @command="handleCommand"
      @click.stop
    >
      <el-button
        class="action-btn"
        :icon="MoreFilled"
        text
        size="small"
        @click.stop
      />
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="rename" :icon="Edit">
            Renommer
          </el-dropdown-item>
          <el-dropdown-item
            command="archive"
            :icon="conversation.is_archived ? FolderOpened : Folder"
          >
            {{ conversation.is_archived ? 'Désarchiver' : 'Archiver' }}
          </el-dropdown-item>
          <el-dropdown-item command="delete" :icon="Delete" divided>
            <span style="color: var(--error-color)">Supprimer</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
/**
 * ConversationItem.vue
 * 
 * Item individuel de conversation dans la sidebar.
 * 
 * Sprint 8 - Phase 2 : Composants Chat
 */
import {
  ChatLineSquare,
  FolderOpened,
  Folder,
  MoreFilled,
  Edit,
  Delete
} from '@element-plus/icons-vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  conversation: {
    type: Object,
    required: true
  },
  active: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'delete', 'archive', 'rename'])

// ============================================================================
// METHODS
// ============================================================================

/**
 * Formater la date
 */
function formatDate(dateString) {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  // Moins d'une minute
  if (diff < 60 * 1000) {
    return 'À l\'instant'
  }
  
  // Moins d'une heure
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `Il y a ${minutes} min`
  }
  
  // Moins de 24h
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `Il y a ${hours}h`
  }
  
  // Moins de 7 jours
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return `Il y a ${days}j`
  }
  
  // Plus ancien
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short'
  })
}

/**
 * Gérer les commandes du dropdown
 */
function handleCommand(command) {
  switch (command) {
    case 'delete':
      emit('delete', props.conversation.id)
      break
    case 'archive':
      emit('archive', props.conversation.id, props.conversation.is_archived)
      break
    case 'rename':
      emit('rename', props.conversation.id, props.conversation.title)
      break
  }
}
</script>

<style scoped lang="scss">
.conversation-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin: 2px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: var(--hover-bg);
    
    .item-actions {
      opacity: 1;
    }
  }
  
  &.active {
    background: var(--active-bg);
    
    .item-icon {
      color: var(--primary-color);
    }
    
    .item-title {
      color: var(--primary-color);
      font-weight: 600;
    }
  }
  
  &.archived {
    opacity: 0.7;
    
    .item-title {
      font-style: italic;
    }
  }
}

.item-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--support-card-bg);
  color: var(--text-secondary);
  
  .el-icon {
    font-size: 16px;
  }
}

.item-content {
  flex: 1;
  min-width: 0; // Permet le text-overflow
  
  .item-title {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .item-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 2px;
    font-size: 11px;
    color: var(--text-tertiary);
    
    .item-count {
      &::before {
        content: '•';
        margin-right: 8px;
      }
    }
  }
}

.item-actions {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
  
  .action-btn {
    width: 28px;
    height: 28px;
    padding: 0;
    color: var(--text-secondary);
    
    &:hover {
      color: var(--primary-color);
      background: var(--hover-bg);
    }
  }
}

// Toujours visible sur mobile
@media (max-width: 768px) {
  .item-actions {
    opacity: 1;
  }
}
</style>