<template>
  <div
    class="message-bubble"
    :class="[roleClass, { streaming: message.isStreaming }]"
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
        
        <!-- Indicateur de streaming -->
        <span v-if="message.isStreaming" class="cursor-blink">▌</span>
      </div>
      
      <!-- Sources (uniquement pour l'assistant) -->
    <SourcesList
        v-if="!isUser && hasSources && !message.isStreaming"
        :sources="message.sources"
        class="message-sources"
    />
      
      <!-- Footer avec actions -->
      <div class="message-footer" v-if="!isUser && !message.isStreaming">
        <!-- Feedback -->
        <FeedbackButtons
          :message-id="message.id"
          :current-feedback="message.feedback"
          @feedback="handleFeedback"
        />
        
        <!-- Actions -->
        <div class="message-actions">
          <el-tooltip content="Copier" placement="top">
            <el-button
              :icon="CopyDocument"
              text
              size="small"
              @click="copyContent"
            />
          </el-tooltip>
          <el-tooltip content="Régénérer" placement="top">
            <el-button
              :icon="RefreshRight"
              text
              size="small"
              @click="$emit('regenerate', message.id)"
            />
          </el-tooltip>
        </div>
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
 * MessageBubble.vue
 * 
 * Bulle de message avec :
 * - Rendu Markdown AMÉLIORÉ (tableaux, code, listes)
 * - Affichage des sources
 * - Boutons de feedback
 * - Actions (copier, régénérer)
 * - Support des Enums en MAJUSCULE (USER, ASSISTANT)
 * 
 * Sprint 8 - CORRECTIONS V2
 * - Texte BLANC sur fond bleu (utilisateur)
 * - Espacement corrigé
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  CopyDocument,
  RefreshRight
} from '@element-plus/icons-vue'

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

const emit = defineEmits(['feedback', 'copy', 'regenerate'])

// ============================================================================
// STORE
// ============================================================================

const authStore = useAuthStore()

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Vérification du rôle - SUPPORTE MAJUSCULE ET MINUSCULE
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

const hasSources = computed(() => {
  return props.message.sources?.length > 0
})

/**
 * Contenu rendu avec Markdown AMÉLIORÉ - ESPACEMENT CORRIGÉ
 */
const renderedContent = computed(() => {
  let content = props.message.content || ''
  
  // Échapper le HTML
  content = escapeHtml(content)
  
  // Convertir le Markdown
  content = parseMarkdown(content)
  
  return content
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Échapper le HTML
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, m => map[m])
}

/**
 * Parser le Markdown - VERSION CORRIGÉE sans espaces excessifs
 */
function parseMarkdown(text) {
  // 1. Blocs de code (avant tout le reste)
  text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    const language = lang || 'text'
    return `<pre class="code-block"><code class="language-${language}">${code.trim()}</code></pre>`
  })
  
  // 2. Tableaux Markdown
  text = parseMarkdownTables(text)
  
  // 3. Code inline (après les blocs)
  text = text.replace(/`([^`]+)`/g, '<code class="code-inline">$1</code>')
  
  // 4. Gras
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  
  // 5. Italique
  text = text.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>')
  
  // 6. Citations [Document X]
  text = text.replace(/\[Document (\d+(?:,\s*\d+)*)\]/g, '<span class="source-ref">[Document $1]</span>')
  
  // 7. Liens
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  
  // 8. Titres
  text = text.replace(/^####\s+(.+)$/gm, '<h5 class="md-h5">$1</h5>')
  text = text.replace(/^###\s+(.+)$/gm, '<h4 class="md-h4">$1</h4>')
  text = text.replace(/^##\s+(.+)$/gm, '<h3 class="md-h3">$1</h3>')
  text = text.replace(/^#\s+(.+)$/gm, '<h2 class="md-h2">$1</h2>')
  
  // 9. Ligne horizontale
  text = text.replace(/^---+$/gm, '<hr class="md-hr">')
  
  // 10. Listes - CORRIGÉ pour éviter espaces excessifs
  text = parseListsCompact(text)
  
  // 11. Paragraphes - CORRIGÉ pour éviter <br> multiples
  text = formatParagraphs(text)
  
  return text
}

/**
 * Parser les tableaux Markdown
 */
function parseMarkdownTables(text) {
  const tableRegex = /(?:^|\n)(\|[^\n]+\|)\n(\|[-:\s|]+\|)\n((?:\|[^\n]+\|\n?)+)/g
  
  return text.replace(tableRegex, (match, headerRow, separator, bodyRows) => {
    const alignments = separator.split('|').filter(c => c.trim()).map(cell => {
      const trimmed = cell.trim()
      if (trimmed.startsWith(':') && trimmed.endsWith(':')) return 'center'
      if (trimmed.endsWith(':')) return 'right'
      return 'left'
    })
    
    const headers = headerRow.split('|').filter(c => c.trim()).map(c => c.trim())
    const rows = bodyRows.trim().split('\n').map(row => 
      row.split('|').filter(c => c.trim()).map(c => c.trim())
    )
    
    let html = '<div class="table-wrapper"><table class="md-table">'
    html += '<thead><tr>'
    headers.forEach((cell, i) => {
      const align = alignments[i] || 'left'
      html += `<th style="text-align:${align}">${cell}</th>`
    })
    html += '</tr></thead><tbody>'
    rows.forEach(row => {
      html += '<tr>'
      row.forEach((cell, i) => {
        const align = alignments[i] || 'left'
        html += `<td style="text-align:${align}">${cell}</td>`
      })
      html += '</tr>'
    })
    html += '</tbody></table></div>'
    
    return '\n' + html + '\n'
  })
}

/**
 * Parser les listes de manière compacte
 */
function parseListsCompact(text) {
  const lines = text.split('\n')
  let result = []
  let inList = false
  let listType = null
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()
    
    // Détecter les éléments de liste
    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/)
    const numberMatch = trimmed.match(/^(\d+)\.\s+(.+)$/)
    
    if (bulletMatch) {
      if (!inList || listType !== 'ul') {
        if (inList) result.push(listType === 'ul' ? '</ul>' : '</ol>')
        result.push('<ul class="md-list">')
        inList = true
        listType = 'ul'
      }
      result.push(`<li>${bulletMatch[1]}</li>`)
    } else if (numberMatch) {
      if (!inList || listType !== 'ol') {
        if (inList) result.push(listType === 'ul' ? '</ul>' : '</ol>')
        result.push('<ol class="md-list">')
        inList = true
        listType = 'ol'
      }
      result.push(`<li>${numberMatch[2]}</li>`)
    } else {
      if (inList) {
        result.push(listType === 'ul' ? '</ul>' : '</ol>')
        inList = false
        listType = null
      }
      result.push(line)
    }
  }
  
  if (inList) {
    result.push(listType === 'ul' ? '</ul>' : '</ol>')
  }
  
  return result.join('\n')
}

/**
 * Formater les paragraphes sans espaces excessifs
 */
function formatParagraphs(text) {
  // Séparer par double saut de ligne pour les paragraphes
  const blocks = text.split(/\n\n+/)
  
  return blocks.map(block => {
    const trimmed = block.trim()
    if (!trimmed) return ''
    
    // Ne pas envelopper les éléments de bloc
    if (trimmed.startsWith('<h') || 
        trimmed.startsWith('<ul') || 
        trimmed.startsWith('<ol') || 
        trimmed.startsWith('<pre') || 
        trimmed.startsWith('<table') || 
        trimmed.startsWith('<div') ||
        trimmed.startsWith('<hr')) {
      return trimmed
    }
    
    // Convertir les sauts de ligne simples en <br> seulement si nécessaire
    const withBreaks = trimmed.replace(/\n/g, '<br>')
    return `<p>${withBreaks}</p>`
  }).filter(b => b).join('')
}

/**
 * Formater l'heure
 */
function formatTime(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Copier le contenu
 */
async function copyContent() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('Contenu copié !')
    emit('copy', props.message.content)
  } catch (err) {
    ElMessage.error('Impossible de copier')
  }
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
  // MESSAGES UTILISATEUR - Bulle bleue à droite, TEXTE BLANC
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
      color: #ffffff !important; // FORCE LE BLANC
      border-radius: 20px 20px 4px 20px;
      box-shadow: 0 2px 8px rgba(0, 92, 169, 0.25);
      
      .message-text {
        color: #ffffff !important; // TEXTE BLANC
        
        // Tous les éléments enfants en blanc
        :deep(*) {
          color: #ffffff !important;
        }
        
        :deep(a) {
          color: #90caf9 !important;
          text-decoration: underline;
        }
        
        :deep(.code-inline) {
          background: rgba(255, 255, 255, 0.2);
          color: #ffffff !important;
        }
        
        :deep(strong) {
          color: #ffffff !important;
        }
        
        :deep(em) {
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
  
  &.streaming {
    .message-body {
      min-height: 50px;
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
    
    // Paragraphes - ESPACEMENT RÉDUIT
    :deep(p) {
      margin: 0 0 8px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    // Titres
    :deep(.md-h2) {
      font-size: 17px;
      font-weight: 700;
      margin: 14px 0 8px;
      color: #111827;
      
      &:first-child {
        margin-top: 0;
      }
    }
    
    :deep(.md-h3) {
      font-size: 15px;
      font-weight: 600;
      margin: 12px 0 6px;
      color: #1f2937;
      
      &:first-child {
        margin-top: 0;
      }
    }
    
    :deep(.md-h4), :deep(.md-h5) {
      font-size: 14px;
      font-weight: 600;
      margin: 10px 0 4px;
      color: #374151;
      
      &:first-child {
        margin-top: 0;
      }
    }
    
    // Listes - COMPACTES
    :deep(.md-list) {
      margin: 6px 0;
      padding-left: 20px;
      
      li {
        margin: 2px 0;
        line-height: 1.5;
        
        &::marker {
          color: #005ca9;
        }
      }
    }
    
    // Code inline
    :deep(.code-inline) {
      background: #f3f4f6;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 13px;
      color: #dc2626;
    }
    
    // Blocs de code
    :deep(.code-block) {
      background: #1e1e1e;
      border-radius: 8px;
      margin: 10px 0;
      padding: 12px 14px;
      overflow-x: auto;
      
      code {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 13px;
        line-height: 1.5;
        color: #e5e7eb;
      }
    }
    
    // Tableaux
    :deep(.table-wrapper) {
      overflow-x: auto;
      margin: 10px 0;
      border-radius: 6px;
      border: 1px solid #e5e7eb;
    }
    
    :deep(.md-table) {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      
      th, td {
        padding: 8px 12px;
        border-bottom: 1px solid #e5e7eb;
      }
      
      th {
        background: #f9fafb;
        font-weight: 600;
        color: #374151;
      }
      
      tbody tr:last-child td {
        border-bottom: none;
      }
    }
    
    // Ligne horizontale
    :deep(.md-hr) {
      border: none;
      height: 1px;
      background: #e5e7eb;
      margin: 12px 0;
    }
    
    // Références aux sources
    :deep(.source-ref) {
      color: #005ca9;
      font-weight: 600;
      font-style: italic;
    }
    
    // Liens
    :deep(a) {
      color: #005ca9;
      text-decoration: none;
      
      &:hover {
        text-decoration: underline;
      }
    }
    
    // Gras
    :deep(strong) {
      font-weight: 600;
      color: #111827;
    }
    
    // Supprimer les <br> multiples
    :deep(br + br) {
      display: none;
    }
  }
  
  .cursor-blink {
    animation: blink 1s infinite;
    color: #005ca9;
    font-size: 16px;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-sources {
  margin-top: 12px;
}

.message-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f3f4f6;
}

.message-actions {
  display: flex;
  gap: 4px;
  
  .el-button {
    color: #9ca3af;
    
    &:hover {
      color: #005ca9;
    }
  }
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  font-size: 11px;
  color: #9ca3af;
}

@media (max-width: 768px) {
  .message-content {
    max-width: 90%;
  }
}
</style>