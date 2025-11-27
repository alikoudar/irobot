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
    
    <!-- Stats Cards - Harmonisées avec animation -->
<el-row :gutter="20" style="margin-bottom: 20px;">
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Conversations"
      :value="stats.total"
      :icon="ChatDotSquare"
      icon-color="#3498db"
    />
  </el-col>
  
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Ce mois"
      :value="stats.thisMonth"
      :icon="Calendar"
      icon-color="#f39c12"
    />
  </el-col>
  
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Messages envoyés"
      :value="stats.totalMessages"
      :icon="ChatLineSquare"
      icon-color="#9b59b6"
    />
  </el-col>
  
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Archivées"
      :value="stats.archived"
      :icon="FolderOpened"
      icon-color="#e67e22"
    />
  </el-col>
</el-row>

    <!-- ✨ NOUVEAU : Composant ConversationSearch Phase 3 -->
    <ConversationSearch
      @search="handleSearch"
      class="search-section"
    />
    
    <!-- ✨ AMÉLIORÉ : Grille de cartes au lieu du tableau -->
    <div class="conversations-grid" v-loading="isLoading">
      <ConversationCard
        v-for="conversation in filteredConversations"
        :key="conversation.id"
        :conversation="conversation"
        @open="openConversation"
        @archive="handleArchive"
        @delete="confirmDelete"
      />
      
      <!-- Empty state -->
      <el-empty
        v-if="!isLoading && filteredConversations.length === 0"
        description="Aucune conversation trouvée"
      >
        <el-button type="primary" @click="startNewConversation">
          Démarrer une conversation
        </el-button>
      </el-empty>
    </div>
    
    <!-- Pagination - Conservée -->
    <div class="pagination-container" v-if="chatStore.total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="chatStore.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * Conversations.vue - VERSION AMÉLIORÉE PHASE 3
 * 
 * Historique des conversations avec :
 * ✅ Stats CORRECTES et persistantes (conservées)
 * ✅ Filtres fonctionnels (conservés)
 * ✅ Pagination (conservée)
 * ✨ Composant ConversationSearch (nouveau)
 * ✨ Composant ConversationCard en grille (nouveau)
 * 
 * Sprint 9 - Phase 3
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Clock,
  Plus,
  ChatDotSquare,
  ChatLineSquare,
  Calendar,
  FolderOpened
} from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'

// ✨ NOUVEAU : Import des composants Phase 3
import ConversationSearch from '@/components/conversations/ConversationSearch.vue'
import ConversationCard from '@/components/conversations/ConversationCard.vue'
import StatCard from '@/components/common/StatCard.vue'

// ============================================================================
// SETUP
// ============================================================================

const router = useRouter()
const chatStore = useChatStore()

// ============================================================================
// STATE - CONSERVÉ
// ============================================================================

const currentPage = ref(1)
const pageSize = ref(20)
const isLoading = ref(false)

// ✨ AMÉLIORÉ : Filtres simplifiés (gérés par ConversationSearch)
const searchFilters = ref({
  query: '',
  startDate: null,
  endDate: null,
  showArchived: false
})

// Stats calculées - CONSERVÉES
const stats = ref({
  total: 0,
  thisMonth: 0,
  totalMessages: 0,
  archived: 0
})

// ============================================================================
// COMPUTED - CONSERVÉ ET AMÉLIORÉ
// ============================================================================

/**
 * Conversations filtrées - LOGIQUE CONSERVÉE
 */
const filteredConversations = computed(() => {
  let result = [...chatStore.conversations]
  
  // Filtrer par statut archivé
  if (!searchFilters.value.showArchived) {
    result = result.filter(c => !c.is_archived)
  }
  
  // Filtrer par recherche texte
  if (searchFilters.value.query) {
    const search = searchFilters.value.query.toLowerCase()
    result = result.filter(c => 
      c.title?.toLowerCase().includes(search) ||
      c.last_message_preview?.toLowerCase().includes(search)
    )
  }
  
  // Filtrer par dates
  if (searchFilters.value.startDate && searchFilters.value.endDate) {
    const start = new Date(searchFilters.value.startDate)
    const end = new Date(searchFilters.value.endDate)
    end.setHours(23, 59, 59, 999)
    
    result = result.filter(c => {
      const date = new Date(c.updated_at)
      return date >= start && date <= end
    })
  }
  
  return result
})

// ============================================================================
// METHODS - CONSERVÉS
// ============================================================================

/**
 * Charger les conversations - CONSERVÉ
 */
async function loadConversations() {
  isLoading.value = true
  
  try {
    await chatStore.fetchConversations({
      page: currentPage.value,
      page_size: pageSize.value,
      include_archived: true
    })
    
    calculateStats()
    
  } catch (error) {
    console.error('Erreur chargement conversations:', error)
    ElMessage.error('Erreur lors du chargement des conversations')
  } finally {
    isLoading.value = false
  }
}

/**
 * Calculer les stats - CONSERVÉ EXACT
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
  
  // Total messages (divisé par 2 pour USER uniquement)
  stats.value.totalMessages = Math.floor(
    conversations.reduce((sum, c) => sum + (c.message_count || 0), 0) / 2
  )
}

/**
 * ✨ NOUVEAU : Handler de recherche (émis par ConversationSearch)
 */
function handleSearch(filters) {
  console.log('🔍 Recherche:', filters)
  searchFilters.value = filters
}

/**
 * Ouvrir une conversation - CONSERVÉ
 */
function openConversation(conversationId) {
  router.push({ path: '/chat', query: { conversation: conversationId } })
}

/**
 * Démarrer une nouvelle conversation - CONSERVÉ
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
 * ✨ AMÉLIORÉ : Archiver/Désarchiver (adapté pour ConversationCard)
 */
async function handleArchive({ conversationId, archive }) {
  try {
    await chatStore.archiveConversation(conversationId, archive)
    ElMessage.success(archive ? 'Conversation archivée' : 'Conversation désarchivée')
    calculateStats()
  } catch (error) {
    ElMessage.error('Erreur lors de l\'opération')
  }
}

/**
 * Supprimer une conversation - CONSERVÉ
 */
async function confirmDelete(conversationId) {
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
    
    await chatStore.deleteConversation(conversationId)
    ElMessage.success('Conversation supprimée')
    await loadConversations()
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Erreur lors de la suppression')
    }
  }
}

/**
 * Changement de taille de page - CONSERVÉ
 */
function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  loadConversations()
}

/**
 * Changement de page - CONSERVÉ
 */
function handlePageChange(page) {
  currentPage.value = page
  loadConversations()
}

// ============================================================================
// LIFECYCLE - CONSERVÉ
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
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .header-icon {
      color: var(--el-color-primary);
    }
    
    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
    
    p {
      margin: 4px 0 0 0;
      color: var(--el-text-color-regular);
      font-size: 14px;
    }
  }
}

.search-section {
  margin-bottom: 24px;
}

/* ✨ NOUVEAU : Grille de cartes */
.conversations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
  min-height: 200px;
  
  /* Empty state dans la grille */
  .el-empty {
    grid-column: 1 / -1;
  }
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

/* Responsive */
@media (max-width: 768px) {
  .conversations-page {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .quick-stats {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
  }
  
  .conversations-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
</style>