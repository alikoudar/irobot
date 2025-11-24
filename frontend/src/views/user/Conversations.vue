<template>
  <div class="conversations-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <el-icon :size="28" class="header-icon"><Clock /></el-icon>
        <div>
          <h1>Historique des conversations</h1>
          <p>Retrouvez et gérez toutes vos conversations avec IroBot</p>
        </div>
      </div>
      <el-button type="primary" @click="startNewConversation">
        <el-icon><Plus /></el-icon>
        Nouvelle conversation
      </el-button>
    </div>
    
    <!-- Stats Cards -->
    <div class="stats-cards">
      <div class="stat-card">
        <span class="stat-label">Total conversations</span>
        <div class="stat-value">
          <el-icon><ChatDotSquare /></el-icon>
          {{ stats.total }}
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-label">Ce mois</span>
        <div class="stat-value">
          <el-icon><Calendar /></el-icon>
          {{ stats.thisMonth }}
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-label">Messages envoyés</span>
        <div class="stat-value">
          <el-icon><ChatLineSquare /></el-icon>
          {{ stats.totalMessages }}
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-label">Archivées</span>
        <div class="stat-value">
          <el-icon><FolderOpened /></el-icon>
          {{ stats.archived }}
        </div>
      </div>
    </div>
    
    <!-- Filtres -->
    <div class="filters-bar">
      <el-input
        v-model="filters.search"
        placeholder="Rechercher une conversation..."
        clearable
        class="search-input"
        @input="handleSearchDebounced"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="à"
        start-placeholder="Date début"
        end-placeholder="Date fin"
        format="DD/MM/YYYY"
        value-format="YYYY-MM-DD"
        :shortcuts="dateShortcuts"
        @change="loadConversations"
      />
      
      <el-select
        v-model="filters.status"
        placeholder="Statut"
        clearable
        @change="loadConversations"
      >
        <el-option label="Actives" value="active" />
        <el-option label="Archivées" value="archived" />
        <el-option label="Toutes" value="all" />
      </el-select>
      
      <el-button @click="loadConversations">
        <el-icon><Refresh /></el-icon>
        Actualiser
      </el-button>
    </div>
    
    <!-- Tableau -->
    <div class="conversations-table">
      <el-table
        :data="filteredConversations"
        v-loading="isLoading"
        @row-click="handleRowClick"
        row-class-name="clickable-row"
        empty-text="Aucune conversation trouvée"
      >
        <el-table-column label="Conversation" min-width="300">
          <template #default="{ row }">
            <div class="conversation-cell">
              <el-icon class="conv-icon" :class="{ archived: row.is_archived }">
                <ChatLineSquare />
              </el-icon>
              <div class="conv-info">
                <span class="conv-title">{{ row.title || 'Nouvelle conversation' }}</span>
                <span class="conv-preview" v-if="row.last_message_preview">
                  {{ row.last_message_preview }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="Messages" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">
              {{ row.message_count || 0 }} msg
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="Dernière activité" width="180">
          <template #default="{ row }">
            <div class="date-cell">
              <span class="date-relative">{{ formatRelativeDate(row.updated_at) }}</span>
              <span class="date-full">{{ formatFullDate(row.updated_at) }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="Statut" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_archived ? 'info' : 'success'" size="small">
              {{ row.is_archived ? 'Archivée' : 'Active' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="Actions" width="150" align="center">
          <template #default="{ row }">
            <div class="actions-cell">
              <el-tooltip content="Ouvrir" placement="top">
                <el-button
                  type="primary"
                  link
                  :icon="View"
                  @click.stop="openConversation(row.id)"
                />
              </el-tooltip>
              <el-tooltip :content="row.is_archived ? 'Désarchiver' : 'Archiver'" placement="top">
                <el-button
                  type="warning"
                  link
                  :icon="row.is_archived ? FolderRemove : Folder"
                  @click.stop="toggleArchive(row)"
                />
              </el-tooltip>
              <el-tooltip content="Supprimer" placement="top">
                <el-button
                  type="danger"
                  link
                  :icon="Delete"
                  @click.stop="confirmDelete(row)"
                />
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- Empty state -->
      <el-empty
        v-if="!isLoading && filteredConversations.length === 0"
        description="Aucune conversation pour le moment"
      >
        <el-button type="primary" @click="startNewConversation">
          Démarrer une conversation
        </el-button>
      </el-empty>
      
      <!-- Pagination -->
      <div class="pagination-wrapper" v-if="chatStore.total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="chatStore.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Conversations.vue
 * 
 * Vue de l'historique des conversations avec :
 * - Stats CORRECTES et persistantes
 * - Filtres fonctionnels
 * - Pagination
 * 
 * Sprint 8 - CORRECTIONS
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Clock,
  Plus,
  Search,
  Refresh,
  ChatDotSquare,
  ChatLineSquare,
  Calendar,
  FolderOpened,
  Folder,
  FolderRemove,
  View,
  Delete
} from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'

// ============================================================================
// SETUP
// ============================================================================

const router = useRouter()
const chatStore = useChatStore()

// ============================================================================
// STATE
// ============================================================================

const currentPage = ref(1)
const pageSize = ref(20)
const isLoading = ref(false)
const searchTimeout = ref(null)

const filters = ref({
  search: '',
  dateRange: null,
  status: null
})

// Stats calculées à partir des données réelles
const stats = ref({
  total: 0,
  thisMonth: 0,
  totalMessages: 0,
  archived: 0
})

// Raccourcis de dates
const dateShortcuts = [
  {
    text: "Aujourd'hui",
    value: () => {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      return [today, new Date()]
    }
  },
  {
    text: 'Cette semaine',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - start.getDay())
      start.setHours(0, 0, 0, 0)
      return [start, end]
    }
  },
  {
    text: 'Ce mois',
    value: () => {
      const end = new Date()
      const start = new Date(end.getFullYear(), end.getMonth(), 1)
      return [start, end]
    }
  },
  {
    text: '3 derniers mois',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setMonth(start.getMonth() - 3)
      return [start, end]
    }
  }
]

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Conversations filtrées
 */
const filteredConversations = computed(() => {
  let result = [...chatStore.conversations]
  
  // Filtrer par statut
  if (filters.value.status === 'active') {
    result = result.filter(c => !c.is_archived)
  } else if (filters.value.status === 'archived') {
    result = result.filter(c => c.is_archived)
  }
  
  // Filtrer par recherche
  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    result = result.filter(c => 
      c.title?.toLowerCase().includes(search) ||
      c.last_message_preview?.toLowerCase().includes(search)
    )
  }
  
  // Filtrer par dates
  if (filters.value.dateRange?.length === 2) {
    const [start, end] = filters.value.dateRange
    result = result.filter(c => {
      const date = new Date(c.updated_at)
      const startDate = new Date(start)
      const endDate = new Date(end)
      endDate.setHours(23, 59, 59, 999)
      return date >= startDate && date <= endDate
    })
  }
  
  return result
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Charger les conversations
 */
async function loadConversations() {
  isLoading.value = true
  
  try {
    // Charger les conversations incluant les archivées
    await chatStore.fetchConversations({
      page: currentPage.value,
      page_size: pageSize.value,
      include_archived: true  // Important : inclure toutes les conversations
    })
    
    // Calculer les stats à partir des données
    calculateStats()
    
  } catch (error) {
    console.error('Erreur chargement conversations:', error)
    ElMessage.error('Erreur lors du chargement des conversations')
  } finally {
    isLoading.value = false
  }
}

/**
 * Calculer les stats - CORRIGÉ pour être exact
 */
function calculateStats() {
  const conversations = chatStore.conversations
  
  // Total
  stats.value.total = chatStore.total || conversations.length
  
  // Archivées
  stats.value.archived = conversations.filter(c => c.is_archived).length
  
  // Ce mois
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
  stats.value.thisMonth = conversations.filter(c => {
    const created = new Date(c.updated_at || c.created_at)
    return created >= startOfMonth
  }).length
  
  // Total messages
  stats.value.totalMessages = conversations.reduce((sum, c) => {
    return sum + (c.message_count || 0)
  }, 0)
}

/**
 * Recherche avec debounce
 */
function handleSearchDebounced() {
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  searchTimeout.value = setTimeout(() => {
    // La recherche est faite côté client via filteredConversations
  }, 300)
}

/**
 * Changement de taille de page
 */
function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  loadConversations()
}

/**
 * Changement de page
 */
function handlePageChange(page) {
  currentPage.value = page
  loadConversations()
}

/**
 * Clic sur une ligne
 */
function handleRowClick(row) {
  openConversation(row.id)
}

/**
 * Ouvrir une conversation
 */
function openConversation(id) {
  router.push({ path: '/chat', query: { conversation: id } })
}

/**
 * Démarrer une nouvelle conversation
 */
async function startNewConversation() {
  try {
    const conversation = await chatStore.createConversation()
    if (conversation) {
      router.push({ path: '/chat', query: { conversation: conversation.id } })
    } else {
      router.push('/chat')
    }
  } catch (error) {
    router.push('/chat')
  }
}

/**
 * Archiver/Désarchiver
 */
async function toggleArchive(row) {
  try {
    const newStatus = !row.is_archived
    await chatStore.archiveConversation(row.id, newStatus)
    ElMessage.success(newStatus ? 'Conversation archivée' : 'Conversation désarchivée')
    
    // Recalculer les stats immédiatement
    calculateStats()
  } catch (error) {
    ElMessage.error('Erreur lors de l\'opération')
  }
}

/**
 * Supprimer une conversation
 */
async function confirmDelete(row) {
  try {
    await ElMessageBox.confirm(
      'Êtes-vous sûr de vouloir supprimer cette conversation ? Cette action est irréversible.',
      'Confirmer la suppression',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'warning'
      }
    )
    
    await chatStore.deleteConversation(row.id)
    ElMessage.success('Conversation supprimée')
    
    // Recharger les données et recalculer les stats
    await loadConversations()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Erreur lors de la suppression')
    }
  }
}

/**
 * Formater la date relative
 */
function formatRelativeDate(dateString) {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return "À l'instant"
  if (diffMins < 60) return `Il y a ${diffMins} min`
  if (diffHours < 24) return `Il y a ${diffHours}h`
  if (diffDays < 7) return `Il y a ${diffDays}j`
  
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

/**
 * Formater la date complète
 */
function formatFullDate(dateString) {
  if (!dateString) return ''
  
  return new Date(dateString).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  loadConversations()
})

// Recalculer les stats quand les conversations changent
watch(() => chatStore.conversations, () => {
  calculateStats()
}, { deep: true })
</script>

<style scoped lang="scss">
.conversations-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .header-icon {
      color: #005ca9;
    }
    
    h1 {
      font-size: 26px;
      font-weight: 700;
      margin: 0;
      color: #1f2937;
    }
    
    p {
      color: #6b7280;
      margin: 4px 0 0;
      font-size: 14px;
    }
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  
  .stat-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e5e7eb;
    
    .stat-label {
      display: block;
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 8px;
    }
    
    .stat-value {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 28px;
      font-weight: 700;
      color: #1f2937;
      
      .el-icon {
        font-size: 24px;
        color: #005ca9;
      }
    }
  }
}

.filters-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  
  .search-input {
    width: 280px;
  }
}

.conversations-table {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  
  :deep(.clickable-row) {
    cursor: pointer;
    
    &:hover {
      background: #f9fafb;
    }
  }
}

.conversation-cell {
  display: flex;
  align-items: center;
  gap: 14px;
  
  .conv-icon {
    font-size: 22px;
    color: #005ca9;
    
    &.archived {
      color: #9ca3af;
    }
  }
  
  .conv-info {
    min-width: 0;
    
    .conv-title {
      display: block;
      font-weight: 500;
      color: #1f2937;
      margin-bottom: 4px;
    }
    
    .conv-preview {
      display: block;
      font-size: 12px;
      color: #6b7280;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 300px;
    }
  }
}

.date-cell {
  .date-relative {
    display: block;
    font-weight: 500;
    color: #374151;
  }
  
  .date-full {
    display: block;
    font-size: 11px;
    color: #9ca3af;
    margin-top: 2px;
  }
}

.actions-cell {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.pagination-wrapper {
  padding: 16px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #e5e7eb;
}

// Responsive
@media (max-width: 1024px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .filters-bar {
    flex-direction: column;
    
    .search-input {
      width: 100%;
    }
  }
}
</style>