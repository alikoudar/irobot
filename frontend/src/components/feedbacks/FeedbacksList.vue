<template>
  <div class="feedbacks-list">
    <!-- Filtres -->
    <div class="filters-section" v-if="showFilters">
      <el-radio-group v-model="filterRating" @change="fetchFeedbacks" size="default">
        <el-radio-button label="">Tous</el-radio-button>
        <el-radio-button label="THUMBS_UP">
          <el-icon><CircleCheck /></el-icon>
          Positifs
        </el-radio-button>
        <el-radio-button label="THUMBS_DOWN">
          <el-icon><CircleClose /></el-icon>
          Négatifs
        </el-radio-button>
      </el-radio-group>
      
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="à"
        start-placeholder="Date début"
        end-placeholder="Date fin"
        format="DD/MM/YYYY"
        @change="fetchFeedbacks"
      />
      
      <el-checkbox v-if="!showCommentsOnly" v-model="onlyWithComments" @change="fetchFeedbacks">
        Seulement avec commentaires
      </el-checkbox>
    </div>
    
    <!-- Table -->
    <el-table
      :data="feedbacks"
      stripe
      v-loading="isLoading"
      style="width: 100%"
      @row-click="handleRowClick"
    >
      <!-- Date -->
      <el-table-column prop="created_at" label="Date" width="180" sortable>
        <template #default="{ row }">
          <el-tooltip :content="formatDateFull(row.created_at)" placement="top">
            <span>{{ formatDate(row.created_at) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      
      <!-- Utilisateur (si admin) -->
      <el-table-column v-if="showUserInfo" label="Utilisateur" width="200">
        <template #default="{ row }">
          <div class="user-info">
            <el-avatar :size="32" class="user-avatar">
              {{ getUserInitials(row) }}
            </el-avatar>
            <div class="user-details">
              <div class="user-name">{{ getUserName(row) }}</div>
              <div class="user-matricule">{{ row.user_matricule || 'N/A' }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      
      <!-- Message (si demandé) -->
      <el-table-column v-if="showMessageContent" label="Message" min-width="300">
        <template #default="{ row }">
          <div class="message-preview">
            <el-tag :type="row.message_role === 'USER' ? '' : 'info'" size="small">
              {{ row.message_role === 'USER' ? '👤 User' : '🤖 IroBot' }}
            </el-tag>
            <p class="message-text">{{ truncateMessage(row.message_content) }}</p>
          </div>
        </template>
      </el-table-column>
      
      <!-- Évaluation -->
      <el-table-column prop="rating" label="Évaluation" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="row.rating === 'THUMBS_UP' ? 'success' : 'danger'" size="large">
            {{ row.rating === 'THUMBS_UP' ? '👍' : '👎' }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- Commentaire -->
      <el-table-column label="Commentaire" min-width="250">
        <template #default="{ row }">
          <div v-if="row.comment" class="comment-cell">
            <el-icon class="comment-icon"><ChatLineSquare /></el-icon>
            <p class="comment-text">{{ row.comment }}</p>
          </div>
          <span v-else class="no-comment">—</span>
        </template>
      </el-table-column>
      
      <!-- Actions -->
      <el-table-column v-if="showConversationLink" label="Actions" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <el-tooltip content="Voir la conversation" placement="top">
            <el-button
              :icon="View"
              circle
              @click.stop="viewConversation(row.conversation_id)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- Pagination -->
    <div class="pagination-container" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, total"
        @current-change="fetchFeedbacks"
      />
    </div>
    
    <!-- Empty state -->
    <el-empty
      v-if="!isLoading && feedbacks.length === 0"
      description="Aucun feedback trouvé"
    />
  </div>
</template>

<script setup>
/**
 * FeedbacksList.vue
 * 
 * Composant de liste des feedbacks avec filtres et pagination
 * Utilisable pour :
 * - Page utilisateur (/feedbacks) : ses feedbacks
 * - Page admin (/admin/feedbacks) : tous les feedbacks
 * 
 * Sprint 9 - Phase 3
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  CircleCheck,
  CircleClose,
  View,
  ChatLineSquare
} from '@element-plus/icons-vue'
import { format, formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import apiClient from '@/services/api/auth'

// ============================================================================
// PROPS
// ============================================================================

const props = defineProps({
  // Filtrer par user_id (pour page utilisateur)
  userId: {
    type: String,
    default: null
  },
  
  // Filtrer par rating
  rating: {
    type: String,
    default: null,
    validator: (value) => ['THUMBS_UP', 'THUMBS_DOWN', null, ''].includes(value)
  },
  
  // Filtres de date (props externes)
  startDate: {
    type: [Date, String],
    default: null
  },
  
  endDate: {
    type: [Date, String],
    default: null
  },
  
  // Options d'affichage
  showUserInfo: {
    type: Boolean,
    default: false
  },
  
  showMessageContent: {
    type: Boolean,
    default: false
  },
  
  showConversationLink: {
    type: Boolean,
    default: false
  },
  
  showFilters: {
    type: Boolean,
    default: true
  },
  
  showCommentsOnly: {
    type: Boolean,
    default: false
  }
})

// ============================================================================
// STATE
// ============================================================================

const router = useRouter()

const feedbacks = ref([])
const isLoading = ref(false)

const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// Filtres internes
const filterRating = ref(props.rating || '')
const dateRange = ref(null)
const onlyWithComments = ref(props.showCommentsOnly)

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Paramètres de requête
 */
const queryParams = computed(() => {
  const params = {
    page: currentPage.value,
    page_size: pageSize.value
  }
  
  // Filtrer par user_id
  if (props.userId) {
    params.user_id = props.userId
  }
  
  // Filtrer par rating (props ou filtre interne)
  const rating = props.rating || filterRating.value
  if (rating) {
    params.rating = rating
  }
  
  // Filtrer par dates (props ou filtre interne)
  const start = props.startDate || dateRange.value?.[0]
  const end = props.endDate || dateRange.value?.[1]
  
  if (start) {
    params.start_date = start instanceof Date ? start.toISOString() : start
  }
  if (end) {
    params.end_date = end instanceof Date ? end.toISOString() : end
  }
  
  // Filtrer par commentaire
  if (onlyWithComments.value) {
    params.has_comment = true
  }
  
  return params
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Récupérer les feedbacks
 */
async function fetchFeedbacks() {
  isLoading.value = true
  
  try {
    const response = await apiClient.get('/feedbacks', {
      params: queryParams.value
    })
    
    feedbacks.value = response.data.feedbacks || []
    total.value = response.data.total || 0
    
  } catch (error) {
    console.error('Erreur chargement feedbacks:', error)
    ElMessage.error('Erreur lors du chargement des feedbacks')
  } finally {
    isLoading.value = false
  }
}

/**
 * Formater date relative
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
 * Formater date complète
 */
function formatDateFull(dateString) {
  if (!dateString) return 'Date inconnue'
  
  try {
    const date = new Date(dateString)
    return format(date, 'dd/MM/yyyy à HH:mm', { locale: fr })
  } catch (error) {
    return 'Date invalide'
  }
}

/**
 * Tronquer message
 */
function truncateMessage(content) {
  if (!content) return 'Message non disponible'
  return content.length > 150
    ? content.substring(0, 150) + '...'
    : content
}

/**
 * Obtenir initiales utilisateur
 */
function getUserInitials(feedback) {
  const nom = feedback.user_nom || ''
  const prenom = feedback.user_prenom || ''
  
  if (nom && prenom) {
    return `${prenom[0]}${nom[0]}`.toUpperCase()
  }
  return feedback.user_matricule ? feedback.user_matricule.substring(0, 2).toUpperCase() : '??'
}

/**
 * Obtenir nom complet utilisateur
 */
function getUserName(feedback) {
  const nom = feedback.user_nom || ''
  const prenom = feedback.user_prenom || ''
  
  if (nom && prenom) {
    return `${prenom} ${nom}`
  }
  return feedback.user_matricule || 'Utilisateur inconnu'
}

/**
 * Voir la conversation
 */
function viewConversation(conversationId) {
  router.push({
    path: '/chat',
    query: { conversation: conversationId }
  })
}

/**
 * Clic sur une ligne
 */
function handleRowClick(row) {
  if (props.showConversationLink) {
    viewConversation(row.conversation_id)
  }
}

// ============================================================================
// WATCHERS
// ============================================================================

// Recharger quand les props changent
watch(() => [props.rating, props.startDate, props.endDate, props.userId], () => {
  currentPage.value = 1
  fetchFeedbacks()
}, { deep: true })

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  fetchFeedbacks()
})
</script>

<style scoped lang="scss">
.feedbacks-list {
  .filters-section {
    display: flex;
    gap: 16px;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  
  .user-info {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .user-avatar {
      flex-shrink: 0;
      background: var(--el-color-primary);
      color: white;
      font-weight: 600;
    }
    
    .user-details {
      .user-name {
        font-weight: 600;
        color: var(--el-text-color-primary);
        line-height: 1.2;
      }
      
      .user-matricule {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        line-height: 1.2;
        margin-top: 2px;
      }
    }
  }
  
  .message-preview {
    .message-text {
      margin: 8px 0 0 0;
      color: var(--el-text-color-regular);
      line-height: 1.6;
    }
  }
  
  .comment-cell {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    
    .comment-icon {
      flex-shrink: 0;
      color: var(--el-color-primary);
      margin-top: 2px;
    }
    
    .comment-text {
      margin: 0;
      color: var(--el-text-color-regular);
      line-height: 1.6;
    }
  }
  
  .no-comment {
    color: var(--el-text-color-placeholder);
  }
  
  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 24px;
  }
  
  :deep(.el-table__row) {
    cursor: pointer;
    transition: background-color 0.2s;
    
    &:hover {
      background-color: var(--el-fill-color-light) !important;
    }
  }
}
</style>