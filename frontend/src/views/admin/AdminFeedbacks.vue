<template>
  <div class="admin-feedbacks-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <el-icon :size="28" class="header-icon"><DataAnalysis /></el-icon>
        <div>
          <h1>Statistiques des Feedbacks</h1>
          <p>Analyse globale des feedbacks de tous les utilisateurs</p>
        </div>
      </div>
      
      <div class="header-actions">
        <el-button
          :icon="Download"
          @click="exportFeedbacks"
        >
          Exporter (CSV)
        </el-button>
        
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="à"
          start-placeholder="Date début"
          end-placeholder="Date fin"
          @change="loadStats"
        />
      </div>
    </div>
    
    <!-- Stats globales - PHASE 3 -->
    <FeedbackStats
      :stats="globalStats"
      :trends="trends"
      show-global-metrics
      class="stats-section"
    />
    
    <!-- Onglets -->
    <el-tabs v-model="activeTab" class="feedback-tabs">
      <!-- Tous les feedbacks -->
      <el-tab-pane label="Tous les feedbacks" name="all">
        <FeedbacksList
          show-user-info
          show-message-content
          show-conversation-link
          :start-date="dateRange?.[0]"
          :end-date="dateRange?.[1]"
        />
      </el-tab-pane>
      
      <!-- Feedbacks positifs -->
      <el-tab-pane label="👍 Positifs" name="positive">
        <FeedbacksList
          rating="THUMBS_UP"
          show-user-info
          show-message-content
          :start-date="dateRange?.[0]"
          :end-date="dateRange?.[1]"
        />
      </el-tab-pane>
      
      <!-- Feedbacks négatifs -->
      <el-tab-pane label="👎 Négatifs" name="negative">
        <FeedbacksList
          rating="THUMBS_DOWN"
          show-user-info
          show-message-content
          show-comments-only
          :start-date="dateRange?.[0]"
          :end-date="dateRange?.[1]"
        />
      </el-tab-pane>
      
      <!-- Avec commentaires -->
      <el-tab-pane label="💬 Avec commentaires" name="comments">
        <FeedbacksList
          show-user-info
          show-message-content
          show-comments-only
          :start-date="dateRange?.[0]"
          :end-date="dateRange?.[1]"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
/**
 * AdminFeedbacks.vue - Page Admin Feedbacks
 * 
 * Vue globale des feedbacks pour les administrateurs avec :
 * - FeedbackStats : Statistiques globales
 * - FeedbacksList : Liste de tous les feedbacks avec filtres
 * - Export CSV
 * 
 * Sprint 9 - Phase 3
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Download
} from '@element-plus/icons-vue'
import apiClient from '@/services/api/auth'

// Importer les composants Phase 3
import FeedbackStats from '@/components/feedbacks/FeedbackStats.vue'
import FeedbacksList from '@/components/feedbacks/FeedbacksList.vue'

// ============================================================================
// STATE
// ============================================================================

const activeTab = ref('all')
const dateRange = ref(null)

const globalStats = ref({
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
// METHODS
// ============================================================================

/**
 * Charger les statistiques globales
 */
async function loadStats() {
  try {
    isLoading.value = true
    
    const params = {}
    if (dateRange.value?.[0]) {
      params.start_date = dateRange.value[0].toISOString()
    }
    if (dateRange.value?.[1]) {
      params.end_date = dateRange.value[1].toISOString()
    }
    
    // Stats globales
    const statsResponse = await apiClient.get('/feedbacks/stats', { params })
    globalStats.value = statsResponse.data
    
    // Tendances (30 derniers jours)
    const trendsParams = { days: 30, ...params }
    const trendsResponse = await apiClient.get('/feedbacks/trends', {
      params: trendsParams
    })
    trends.value = trendsResponse.data.trends || []
    
  } catch (error) {
    console.error('Erreur chargement stats:', error)
    ElMessage.error('Erreur lors du chargement des statistiques')
  } finally {
    isLoading.value = false
  }
}

/**
 * Exporter les feedbacks en CSV
 */
async function exportFeedbacks() {
  try {
    const params = {
      format: 'csv',
      include_context: true
    }
    
    if (dateRange.value?.[0]) {
      params.start_date = dateRange.value[0].toISOString()
    }
    if (dateRange.value?.[1]) {
      params.end_date = dateRange.value[1].toISOString()
    }
    
    const response = await apiClient.get('/feedbacks/export', {
      params,
      responseType: 'blob'
    })
    
    // Créer un lien de téléchargement
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `feedbacks_${new Date().toISOString().split('T')[0]}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    ElMessage.success('Export réussi')
    
  } catch (error) {
    console.error('Erreur export:', error)
    ElMessage.error('Erreur lors de l\'export')
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  loadStats()
})
</script>

<style scoped lang="scss">
.admin-feedbacks-page {
  padding: 24px;
  max-width: 1600px;
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
  
  .header-actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }
}

.stats-section {
  margin-bottom: 32px;
}

.feedback-tabs {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 24px;
  
  :deep(.el-tabs__header) {
    margin-bottom: 24px;
  }
}
</style>