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
        <span class="item-date">{{ relativeTime }}</span>
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
 * ✅ CORRIGÉ v2.4 : Temps relatif réactif (se met à jour automatiquement)
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
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
// STATE
// ============================================================================

// 🔥 AJOUT v2.4 : Compteur pour forcer le rafraîchissement du computed
const now = ref(Date.now())
let interval = null

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Temps relatif réactif
 * 
 * ✅ CORRIGÉ v2.4 : Se met à jour automatiquement toutes les 30 secondes
 */
const relativeTime = computed(() => {
  return formatDate(props.conversation.updated_at, now.value)
})

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  // 🔥 AJOUT v2.4 : Rafraîchir le temps toutes les 30 secondes
  interval = setInterval(() => {
    now.value = Date.now()
  }, 30000) // 30 secondes
})

onUnmounted(() => {
  // Nettoyer l'interval
  if (interval) {
    clearInterval(interval)
  }
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Formater la date en temps relatif
 * 
 * ✅ CORRIGÉ v2.4 : Accepte maintenant un timestamp "now" pour la réactivité
 */
function formatDate(dateString, nowTimestamp = Date.now()) {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const diff = nowTimestamp - date.getTime()
  
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

<style scoped>
.conversation-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 8px;
  margin-bottom: 4px;
}

.conversation-item:hover {
  background-color: var(--bg-hover, #f5f5f5);
}

.conversation-item.active {
  background-color: var(--primary-color-light, #e6f7ff);
  border-left: 3px solid var(--primary-color, #1890ff);
}

.conversation-item.archived {
  opacity: 0.6;
}

/* Icône */
.item-icon {
  flex-shrink: 0;
  font-size: 20px;
  color: var(--text-secondary, #666);
}

.conversation-item.active .item-icon {
  color: var(--primary-color, #1890ff);
}

/* Contenu */
.item-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-item.active .item-title {
  color: var(--primary-color, #1890ff);
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary, #999);
}

.item-date {
  white-space: nowrap;
}

.item-count {
  white-space: nowrap;
}

.item-count::before {
  content: '•';
  margin-right: 8px;
}

/* Actions */
.item-actions {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.conversation-item:hover .item-actions {
  opacity: 1;
}

.action-btn {
  color: var(--text-secondary, #666);
}

.action-btn:hover {
  color: var(--primary-color, #1890ff);
}
</style>