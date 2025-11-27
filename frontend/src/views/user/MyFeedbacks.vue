<template>
  <div class="feedbacks-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <el-icon :size="28" class="header-icon"><ChatLineSquare /></el-icon>
        <div>
          <h1>Mes Feedbacks</h1>
          <p>Consultez tous les feedbacks que vous avez donnés sur les réponses d'IroBot</p>
        </div>
      </div>
    </div>
    
    <!-- Stats personnelles - PHASE 3 -->
    <FeedbackStats
      :stats="personalStats"
      :trends="trends"
      class="stats-section"
    />
    
    <!-- Liste des feedbacks - PHASE 3 -->
    <FeedbacksList
      :user-id="currentUserId"
      show-message-content
      class="feedbacks-list-section"
    />
  </div>
</template>

<script setup>
/**
 * MyFeedbacks.vue - Page Mes Feedbacks
 * 
 * Affiche les feedbacks personnels de l'utilisateur avec :
 * - FeedbackStats : Statistiques personnelles
 * - FeedbacksList : Liste de ses feedbacks
 * 
 * Sprint 9 - Phase 3
 */
import { ref, computed, onMounted } from 'vue'
import { ChatLineSquare } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/services/api/auth'

// Importer les composants Phase 3
import FeedbackStats from '@/components/feedbacks/FeedbackStats.vue'
import FeedbacksList from '@/components/feedbacks/FeedbacksList.vue'

// ============================================================================
// SETUP
// ============================================================================

const authStore = useAuthStore()

// ============================================================================
// STATE
// ============================================================================

const personalStats = ref({
  total_feedbacks: 0,
  thumbs_up: 0,
  thumbs_down: 0,
  with_comments: 0,
  satisfaction_rate: 0,
  feedback_rate: 0,
  total_messages: 0
})

const trends = ref([])
const isLoading = ref(false)

// ============================================================================
// COMPUTED
// ============================================================================

const currentUserId = computed(() => authStore.currentUser?.id)

// ============================================================================
// METHODS
// ============================================================================

/**
 * Charger les statistiques personnelles
 */
async function loadPersonalStats() {
  if (!currentUserId.value) return
  
  try {
    isLoading.value = true
    
    // Récupérer les stats de l'utilisateur
    const response = await apiClient.get('/feedbacks/stats', {
      params: { user_id: currentUserId.value }
    })
    
    personalStats.value = response.data
    
    // AJOUTER CETTE LIGNE ⬇️
    console.log('📊 STATS REÇUES:', JSON.stringify(response.data, null, 2))
    
  } catch (error) {
    console.error('Erreur chargement stats:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * Charger les tendances (30 derniers jours)
 */
async function loadTrends() {
  if (!currentUserId.value) return
  
  try {
    const response = await apiClient.get('/feedbacks/trends', {
      params: {
        user_id: currentUserId.value,
        days: 30
      }
    })
    
    trends.value = response.data.trends || []
    
  } catch (error) {
    console.error('Erreur chargement tendances:', error)
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  await loadPersonalStats()
  await loadTrends()
})
</script>

<style scoped lang="scss">
.feedbacks-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
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

.stats-section {
  margin-bottom: 32px;
}

.feedbacks-list-section {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 24px;
}
</style>