<template>
  <div
    class="message-bubble"
    :class="[roleClass]"
  >
    <!-- Avatar -->
    <div class="message-avatar">
      <template v-if="isUser">
        <el-avatar :size="40" class="user-avatar">
          {{ userInitials }}
        </el-avatar>
      </template>
      <template v-else>
        <div class="assistant-avatar">
          <el-icon :size="22"><ChatDotRound /></el-icon>
        </div>
      </template>
    </div>
    
    <!-- Contenu -->
    <div class="message-content">
      <!-- Header -->
      <div class="message-header">
        <span class="message-role">{{ isUser ? 'Vous' : 'IroBot' }}</span>
        <span class="message-time">{{ formatTime(message.created_at) }}</span>
      </div>
      
      <!-- Corps du message -->
      <div class="message-body">
        <!-- Contenu texte avec Markdown -->
        <div
          class="message-text"
          v-html="renderedContent"
        ></div>
      </div>
      
      <!-- Sources (uniquement pour l'assistant) -->
      <SourcesList
        v-if="!isUser && hasSources"
        :sources="message.sources"
        class="message-sources"
      />
      
      <!-- Footer avec feedback (SIMPLIFIÉ - Plus de gestion d'IDs temporaires) -->
      <div class="message-footer" v-if="!isUser">
        <!-- 
          ✅ SIMPLIFIÉ : message.id est TOUJOURS un UUID réel
          Plus besoin de vérifier server_message_id ou temp-
        -->
        <FeedbackButtons
          :message-id="message.id"
          :current-feedback="message.feedback"
          @feedback="handleFeedback"
        />
      </div>
      
      <!-- Métadonnées (optionnel, pour debug/admin) -->
      <div class="message-meta" v-if="showMeta && !isUser">
        <el-tag size="small" v-if="message.cache_hit" type="success">
          Cache
        </el-tag>
        <span v-if="message.response_time_seconds">
          {{ message.response_time_seconds.toFixed(2) }}s
        </span>
        <span v-if="message.token_count_total">
          {{ message.token_count_total }} tokens
        </span>
        <span v-if="message.model_used">
          {{ message.model_used }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * MessageBubble.vue - VERSION SIMPLIFIÉE
 * 
 * Plus de problème d'IDs temporaires !
 * Le message.id est TOUJOURS un UUID réel du backend.
 * 
 * Sprint 9 - Correction: Utilisation endpoint non-streaming
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ChatDotRound } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'

import SourcesList from './SourcesList.vue'
import FeedbackButtons from './FeedbackButtons.vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  showMeta: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['feedback'])

// ============================================================================
// STORE
// ============================================================================

const authStore = useAuthStore()

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Vérification du rôle
 */
const isUser = computed(() => {
  const role = props.message.role?.toUpperCase()
  return role === 'USER'
})

/**
 * Classe CSS basée sur le rôle
 */
const roleClass = computed(() => {
  return isUser.value ? 'user' : 'assistant'
})

const userInitials = computed(() => {
  const user = authStore.currentUser
  if (!user) return 'U'
  return `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase()
})

/**
 * Vérifier si le message a des sources
 */
const hasSources = computed(() => {
  return Array.isArray(props.message.sources) && props.message.sources.length > 0
})

/**
 * Rendu du contenu Markdown avec markdown-it
 */
const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return renderMarkdown(props.message.content)
})

/**
 * Formater l'horodatage
 */
function formatTime(timestamp) {
  if (!timestamp) return ''
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // Moins d'une minute
  if (diff < 60000) {
    return 'À l\'instant'
  }
  
  // Moins d'une heure
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `Il y a ${minutes} min`
  }
  
  // Aujourd'hui
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  }
  
  // Autre jour
  return date.toLocaleString('fr-FR', { 
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Gérer le feedback
 */
function handleFeedback(data) {
  emit('feedback', data)
}
</script>

<style scoped lang="scss">
.message-bubble {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  
  // =========================================================================
  // MESSAGES UTILISATEUR - Bulle bleue à droite
  // =========================================================================
  &.user {
    flex-direction: row-reverse;
    
    .message-content {
      align-items: flex-end;
    }
    
    .message-header {
      flex-direction: row-reverse;
    }
    
    .message-body {
      background: linear-gradient(135deg, #005ca9 0%, #004a8a 100%);
      color: #ffffff !important;
      border-radius: 20px 20px 4px 20px;
      box-shadow: 0 2px 8px rgba(0, 92, 169, 0.25);
      
      .message-text {
        color: #ffffff !important;
        
        :deep(*) {
          color: #ffffff !important;
        }
        
        :deep(a) {
          color: #90caf9 !important;
          text-decoration: underline;
        }
        
        :deep(code:not(.hljs)) {
          background: rgba(255, 255, 255, 0.2);
          color: #ffffff !important;
        }
      }
    }
    
    .user-avatar {
      background: linear-gradient(135deg, #005ca9 0%, #004a8a 100%);
      color: white;
      font-size: 14px;
      font-weight: 700;
      border: 2px solid white;
      box-shadow: 0 2px 8px rgba(0, 92, 169, 0.3);
    }
  }
  
  // =========================================================================
  // MESSAGES ASSISTANT - Bulle blanche à gauche
  // =========================================================================
  &.assistant {
    .message-body {
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 20px 20px 20px 4px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
      
      .message-text {
        color: #374151;
      }
    }
    
    .assistant-avatar {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #005ca9 0%, #0077cc 100%);
      border-radius: 12px;
      color: white;
      box-shadow: 0 2px 8px rgba(0, 92, 169, 0.3);
    }
  }
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 75%;
  min-width: 200px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  
  .message-role {
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
  }
  
  .message-time {
    font-size: 12px;
    color: #9ca3af;
  }
}

.message-body {
  padding: 14px 18px;
  
  .message-text {
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;
    
    // Paragraphes
    :deep(p) {
      margin: 0 0 8px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    // Listes
    :deep(ul),
    :deep(ol) {
      margin: 4px 0;
      padding-left: 24px;
      
      li {
        margin: 1px 0;
      }
    }
    
    :deep(ol) {
      list-style-type: decimal;
    }
    
    // Titres
    :deep(h2) {
      margin: 12px 0 6px;
      font-size: 18px;
      font-weight: 600;
    }
    
    :deep(h3) {
      margin: 10px 0 5px;
      font-size: 16px;
      font-weight: 600;
    }
    
    // Code inline
    :deep(code:not(.hljs)) {
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 13px;
      color: #be123c;
    }
    
    // Blocs de code avec highlight.js
    :deep(pre.hljs) {
  background: #1e293b;
  color: #ffffff; // ← TOUT EN BLANC PAR DÉFAUT
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
  
  code {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.5;
    background: transparent;
    padding: 0;
  }
  
  // UNIQUEMENT ces éléments en jaune
  .hljs-keyword,
  .hljs-type,
  .hljs-string,
  .hljs-built_in {
    color: #fcd34d !important; // Jaune
  }
  
  // Mots-clés en gras
  .hljs-keyword {
    font-weight: 600;
  }
  
  // Forcer TOUT LE RESTE en blanc
  * {
    color: #ffffff !important;
  }
  
  // Puis réappliquer le jaune (priorité plus haute)
  .hljs-keyword,
  .hljs-type,
  .hljs-string,
  .hljs-built_in {
    color: #fcd34d !important;
  }
}
    
    // Tableaux
    :deep(table) {
      border-collapse: collapse;
      width: 100%;
      margin: 12px 0;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
      
      th, td {
        border: 1px solid #e5e7eb;
        padding: 10px 14px;
        text-align: left;
      }
      
      th {
        background: #f9fafb;
        font-weight: 600;
        color: #374151;
      }
      
      tr:hover {
        background: #f9fafb;
      }
    }
    
    // Citations
    :deep(blockquote) {
      border-left: 4px solid #005ca9;
      padding-left: 16px;
      margin: 12px 0;
      color: #6b7280;
      font-style: italic;
      background: #f9fafb;
      padding: 12px 16px;
      border-radius: 4px;
    }
    
    // Liens
    :deep(a) {
      color: #0066cc;
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s;
      
      &:hover {
        border-bottom-color: #0066cc;
      }
    }
  }
}

.message-sources {
  margin-top: 12px;
}

.message-footer {
  display: flex;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 11px;
  color: #9ca3af;
}
</style>