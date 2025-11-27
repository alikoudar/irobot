<template>
  <div class="feedback-buttons">
    <!-- Thumbs up -->
    <el-tooltip content="Réponse utile" placement="top">
      <el-button
        class="feedback-btn"
        :class="{ active: currentRating === 'THUMBS_UP' }"
        text
        size="small"
        @click="handleFeedback('THUMBS_UP')"
      >
        <el-icon :size="16">
          <component :is="ThumbsUpIcon" />
        </el-icon>
      </el-button>
    </el-tooltip>
    
    <!-- Thumbs down -->
    <el-tooltip content="Réponse à améliorer" placement="top">
      <el-button
        class="feedback-btn"
        :class="{ active: currentRating === 'THUMBS_DOWN' }"
        text
        size="small"
        @click="handleFeedback('THUMBS_DOWN')"
      >
        <el-icon :size="16">
          <component :is="ThumbsDownIcon" />
        </el-icon>
      </el-button>
    </el-tooltip>
    
    <!-- Indicateur de feedback existant -->
    <Transition name="fade">
      <span v-if="currentRating" class="feedback-indicator">
        <el-icon v-if="currentRating === 'THUMBS_UP'" color="#10b981"><CircleCheck /></el-icon>
        <el-icon v-else color="#ef4444"><WarningFilled /></el-icon>
        <span class="feedback-text">Merci !</span>
      </span>
    </Transition>
    
    <!-- Modal de commentaire (pour feedback négatif) -->
    <el-dialog
      v-model="showCommentModal"
      title="Aidez-nous à nous améliorer"
      width="450px"
      :close-on-click-modal="false"
    >
      <div class="comment-modal-content">
        <p class="modal-description">
          Qu'est-ce qui pourrait être amélioré dans cette réponse ?
        </p>
        
        <!-- Options rapides -->
        <div class="quick-options">
          <el-check-tag
            v-for="option in quickOptions"
            :key="option.value"
            :checked="selectedOptions.includes(option.value)"
            @change="toggleOption(option.value)"
          >
            {{ option.label }}
          </el-check-tag>
        </div>
        
        <!-- Commentaire libre -->
        <el-input
          v-model="comment"
          type="textarea"
          :rows="3"
          placeholder="Ajoutez un commentaire (optionnel)..."
          maxlength="500"
          show-word-limit
        />
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cancelFeedback">Annuler</el-button>
          <el-button type="primary" @click="submitFeedback">
            Envoyer
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * FeedbackButtons.vue - VERSION CORRIGÉE
 * 
 * Boutons de feedback (thumbs up/down) avec :
 * - Feedback positif direct
 * - Feedback négatif avec modal de commentaire
 * - Indicateur visuel du feedback actuel
 * 
 * CORRECTION : Utilisation de composants Vue fonctionnels au lieu de template strings
 * 
 * Sprint 8 - Phase 2 : Composants Chat
 * Correction : 27 novembre 2025
 */
import { ref, computed, h } from 'vue'
import {
  CircleCheck,
  WarningFilled
} from '@element-plus/icons-vue'

// ============================================================================
// ICÔNES THUMBS (Composants fonctionnels Vue)
// ============================================================================

/**
 * Icône Thumbs Up (composant fonctionnel)
 */
const ThumbsUpIcon = {
  name: 'ThumbsUp',
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      fill: 'currentColor',
      xmlns: 'http://www.w3.org/2000/svg'
    }, [
      h('path', {
        d: 'M7.5 22h-3A1.5 1.5 0 0 1 3 20.5v-9A1.5 1.5 0 0 1 4.5 10h3a.5.5 0 0 1 .5.5v11a.5.5 0 0 1-.5.5ZM21 10h-4.5a.5.5 0 0 1-.5-.5V6a3 3 0 0 0-3-3h-.5a.5.5 0 0 0-.45.28l-2.8 5.6a.5.5 0 0 0-.05.22v11a.5.5 0 0 0 .5.5h8.3a2 2 0 0 0 1.97-1.67l1.5-9A2 2 0 0 0 21 10Z'
      })
    ])
  }
}

/**
 * Icône Thumbs Down (composant fonctionnel)
 */
const ThumbsDownIcon = {
  name: 'ThumbsDown',
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      fill: 'currentColor',
      xmlns: 'http://www.w3.org/2000/svg'
    }, [
      h('path', {
        d: 'M16.5 2h3A1.5 1.5 0 0 1 21 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-3a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5ZM3 14h4.5a.5.5 0 0 1 .5.5V18a3 3 0 0 0 3 3h.5a.5.5 0 0 0 .45-.28l2.8-5.6a.5.5 0 0 0 .05-.22v-11a.5.5 0 0 0-.5-.5H6.5a2 2 0 0 0-1.97 1.67l-1.5 9A2 2 0 0 0 3 14Z'
      })
    ])
  }
}

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  messageId: {
    type: String,
    required: true
  },
  currentFeedback: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['feedback'])

// ============================================================================
// STATE
// ============================================================================

const showCommentModal = ref(false)
const comment = ref('')
const selectedOptions = ref([])
const pendingRating = ref(null)

// Options rapides pour le feedback négatif
const quickOptions = [
  { value: 'incorrect', label: 'Information incorrecte' },
  { value: 'incomplete', label: 'Réponse incomplète' },
  { value: 'unclear', label: 'Pas assez clair' },
  { value: 'off_topic', label: 'Hors sujet' },
  { value: 'sources', label: 'Mauvaises sources' }
]

// ============================================================================
// COMPUTED
// ============================================================================

const currentRating = computed(() => {
  if (!props.currentFeedback) return null
  
  // Normaliser le rating en majuscules avec underscore
  const rating = props.currentFeedback.rating
  if (!rating) return null
  
  // Gérer différents formats : "thumbs_up", "THUMBS_UP", "thumbs-up"
  return rating.toUpperCase().replace(/-/g, '_')
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Gérer le clic sur un bouton de feedback
 */
function handleFeedback(rating) {
  console.log('🔘 Feedback clicked:', { rating, messageId: props.messageId })
  
  // Si même feedback, on le retire
  if (currentRating.value === rating) {
    emit('feedback', {
      messageId: props.messageId,
      rating: null,
      comment: null
    })
    return
  }
  
  // Feedback positif : envoi direct
  if (rating === 'THUMBS_UP') {
    emit('feedback', {
      messageId: props.messageId,
      rating,
      comment: null
    })
    return
  }
  
  // Feedback négatif : ouvrir le modal
  pendingRating.value = rating
  showCommentModal.value = true
}

/**
 * Basculer une option rapide
 */
function toggleOption(option) {
  const index = selectedOptions.value.indexOf(option)
  if (index === -1) {
    selectedOptions.value.push(option)
  } else {
    selectedOptions.value.splice(index, 1)
  }
}

/**
 * Annuler le feedback
 */
function cancelFeedback() {
  showCommentModal.value = false
  comment.value = ''
  selectedOptions.value = []
  pendingRating.value = null
}

/**
 * Soumettre le feedback
 */
function submitFeedback() {
  // Construire le commentaire complet
  let fullComment = ''
  
  if (selectedOptions.value.length > 0) {
    const optionLabels = selectedOptions.value.map(opt => {
      return quickOptions.find(o => o.value === opt)?.label
    }).filter(Boolean)
    fullComment = optionLabels.join(', ')
  }
  
  if (comment.value.trim()) {
    fullComment += fullComment ? '. ' : ''
    fullComment += comment.value.trim()
  }
  
  emit('feedback', {
    messageId: props.messageId,
    rating: pendingRating.value,
    comment: fullComment || null
  })
  
  cancelFeedback()
}
</script>

<style scoped lang="scss">
.feedback-buttons {
  display: flex;
  align-items: center;
  gap: 4px;
}

.feedback-btn {
  width: 32px;
  height: 32px;
  padding: 4px;
  color: var(--text-tertiary);
  border-radius: 6px;
  transition: all 0.2s;
  
  &:hover {
    color: var(--text-secondary);
    background: var(--hover-bg);
  }
  
  &.active {
    // Thumbs up
    &:nth-of-type(1) {
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
      
      &:hover {
        background: rgba(16, 185, 129, 0.15);
      }
    }
    
    // Thumbs down
    &:nth-of-type(2) {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
      
      &:hover {
        background: rgba(239, 68, 68, 0.15);
      }
    }
  }
}

.feedback-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  animation: fadeIn 0.3s ease;
  
  .el-icon {
    font-size: 14px;
  }
  
  .feedback-text {
    font-weight: 500;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

// Modal
.comment-modal-content {
  .modal-description {
    margin: 0 0 16px;
    font-size: 14px;
    color: var(--text-secondary);
  }
  
  .quick-options {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
    
    :deep(.el-check-tag) {
      border-radius: 16px;
      padding: 6px 12px;
      font-size: 13px;
      background: var(--bg-color);
      border: 1px solid var(--border-color);
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.2s;
      
      &:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
      }
      
      &.is-checked {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: white;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// Transition
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>