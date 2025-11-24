<template>
  <div class="profile-stats">
    <div class="stats-card">
      <div class="stats-header">
        <el-icon class="stats-icon"><DataAnalysis /></el-icon>
        <h3>Statistiques d'utilisation</h3>
      </div>
      
      <!-- Stats principales -->
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-icon conversations">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.totalConversations }}</span>
            <span class="stat-label">Conversations</span>
          </div>
        </div>
        
        <div class="stat-item">
          <div class="stat-icon messages">
            <el-icon><ChatLineSquare /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.totalMessages }}</span>
            <span class="stat-label">Messages envoyés</span>
          </div>
        </div>
        
        <div class="stat-item">
          <div class="stat-icon feedbacks">
            <el-icon><Star /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.totalFeedbacks }}</span>
            <span class="stat-label">Feedbacks donnés</span>
          </div>
        </div>
        
        <div class="stat-item">
          <div class="stat-icon satisfaction">
            <el-icon><Trophy /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.satisfactionRate }}%</span>
            <span class="stat-label">Taux satisfaction</span>
          </div>
        </div>
      </div>
      
      <!-- Détails feedbacks -->
      <div class="feedback-details" v-if="stats.totalFeedbacks > 0">
        <h4>Détails des feedbacks</h4>
        <div class="feedback-breakdown">
          <div class="feedback-item positive">
            <el-icon><CaretTop /></el-icon>
            <span class="feedback-count">{{ stats.thumbsUp }}</span>
            <span class="feedback-label">Réponses utiles</span>
          </div>
          <div class="feedback-item negative">
            <el-icon><CaretBottom /></el-icon>
            <span class="feedback-count">{{ stats.thumbsDown }}</span>
            <span class="feedback-label">À améliorer</span>
          </div>
        </div>
        <div class="satisfaction-bar">
          <span class="bar-label">Taux de satisfaction</span>
          <el-progress
            :percentage="stats.satisfactionRate"
            :color="getSatisfactionColor(stats.satisfactionRate)"
            :stroke-width="12"
          />
        </div>
      </div>
      
      <!-- Message si pas de feedbacks -->
      <div class="no-feedbacks" v-else>
        <el-icon><InfoFilled /></el-icon>
        <span>Aucun feedback donné pour le moment</span>
      </div>
      
      <!-- Activité récente -->
      <div class="recent-activity">
        <h4>Activité récente</h4>
        <div class="activity-grid">
          <div class="activity-item">
            <span class="activity-label">Cette semaine</span>
            <span class="activity-value">{{ stats.thisWeek }} conversation{{ stats.thisWeek > 1 ? 's' : '' }}</span>
          </div>
          <div class="activity-item">
            <span class="activity-label">Ce mois</span>
            <span class="activity-value">{{ stats.thisMonth }} conversation{{ stats.thisMonth > 1 ? 's' : '' }}</span>
          </div>
          <div class="activity-item">
            <span class="activity-label">Dernière activité</span>
            <span class="activity-value">{{ lastActivityText }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * ProfileStats.vue
 * 
 * Statistiques d'utilisation sur la page profil.
 * 
 * CORRECTIONS V2 :
 * - Feedbacks à 0 par défaut (pas d'estimation fantaisiste)
 * - Chargement depuis l'API uniquement
 * - Stats correctes depuis les conversations
 * 
 * Sprint 8 - CORRECTIONS V2
 */
import { ref, computed, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import {
  DataAnalysis,
  ChatDotRound,
  ChatLineSquare,
  Star,
  Trophy,
  CaretTop,
  CaretBottom,
  InfoFilled
} from '@element-plus/icons-vue'

// ============================================================================
// STORES
// ============================================================================

const chatStore = useChatStore()

// ============================================================================
// STATE
// ============================================================================

const isLoading = ref(false)

const stats = ref({
  totalConversations: 0,
  totalMessages: 0,
  totalFeedbacks: 0,      // 0 par défaut, pas d'estimation
  thumbsUp: 0,            // 0 par défaut
  thumbsDown: 0,          // 0 par défaut
  satisfactionRate: 0,    // 0 par défaut
  thisWeek: 0,
  thisMonth: 0,
  lastActivity: null
})

// ============================================================================
// COMPUTED
// ============================================================================

const lastActivityText = computed(() => {
  if (!stats.value.lastActivity) return 'Aucune'
  
  const now = new Date()
  const last = new Date(stats.value.lastActivity)
  const diffMs = now - last
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'À l\'instant'
  if (diffMins < 60) return `Il y a ${diffMins} min`
  if (diffHours < 24) return `Il y a ${diffHours}h`
  if (diffDays < 7) return `Il y a ${diffDays} jour${diffDays > 1 ? 's' : ''}`
  
  return last.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Couleur basée sur le taux de satisfaction
 */
function getSatisfactionColor(rate) {
  if (rate >= 80) return '#10b981'
  if (rate >= 60) return '#f59e0b'
  if (rate >= 40) return '#f97316'
  return '#ef4444'
}

/**
 * Charger les statistiques
 */
async function loadStats() {
  isLoading.value = true
  
  try {
    // 1. Charger les conversations si nécessaire
    if (chatStore.conversations.length === 0) {
      await chatStore.fetchConversations({
        page: 1,
        page_size: 100,
        include_archived: true
      })
    }
    
    const conversations = chatStore.conversations
    const now = new Date()
    
    // 2. Stats de base depuis les conversations
    stats.value.totalConversations = chatStore.total || conversations.length
    
    // Compter les messages
    stats.value.totalMessages = conversations.reduce((sum, c) => {
      return sum + (c.message_count || 0)
    }, 0)
    
    // Cette semaine (7 derniers jours)
    const weekAgo = new Date(now)
    weekAgo.setDate(weekAgo.getDate() - 7)
    stats.value.thisWeek = conversations.filter(c => {
      const date = new Date(c.updated_at || c.created_at)
      return date >= weekAgo
    }).length
    
    // Ce mois
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    stats.value.thisMonth = conversations.filter(c => {
      const date = new Date(c.updated_at || c.created_at)
      return date >= startOfMonth
    }).length
    
    // Dernière activité
    if (conversations.length > 0) {
      const sorted = [...conversations].sort((a, b) => 
        new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)
      )
      stats.value.lastActivity = sorted[0].updated_at || sorted[0].created_at
    }
    
    // 3. Essayer de charger les stats de feedback depuis l'API
    await loadFeedbackStatsFromAPI()
    
  } catch (error) {
    console.error('Erreur chargement stats:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * Charger les stats de feedback depuis l'API backend
 * Si l'endpoint n'existe pas, garde les valeurs à 0
 */
async function loadFeedbackStatsFromAPI() {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return
    
    const response = await fetch('/api/v1/chat/stats/user', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      
      // Mettre à jour uniquement si l'API retourne des données
      if (data.feedbacks !== undefined) {
        stats.value.totalFeedbacks = data.feedbacks?.total || 0
        stats.value.thumbsUp = data.feedbacks?.positive || 0
        stats.value.thumbsDown = data.feedbacks?.negative || 0
        
        // Calculer le taux seulement si on a des feedbacks
        if (stats.value.totalFeedbacks > 0) {
          stats.value.satisfactionRate = Math.round(
            (stats.value.thumbsUp / stats.value.totalFeedbacks) * 100
          )
        }
      }
      
      // Mettre à jour les autres stats si disponibles
      if (data.conversations !== undefined) {
        stats.value.totalConversations = data.conversations
      }
      if (data.messages !== undefined) {
        stats.value.totalMessages = data.messages
      }
    }
    // Si 404 ou autre erreur, on garde les valeurs à 0 (pas d'estimation)
    
  } catch (error) {
    // Silencieux - on garde les valeurs à 0
    console.log('API stats non disponible, valeurs à 0')
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
.profile-stats {
  margin-top: 24px;
}

.stats-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  padding: 24px;
}

.stats-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  
  .stats-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #005ca9 0%, #0077cc 100%);
    border-radius: 10px;
    color: white;
    font-size: 20px;
  }
  
  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  
  @media (max-width: 900px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 500px) {
    grid-template-columns: 1fr;
  }
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  
  .stat-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    font-size: 22px;
    
    &.conversations {
      background: #dbeafe;
      color: #2563eb;
    }
    
    &.messages {
      background: #fef3c7;
      color: #d97706;
    }
    
    &.feedbacks {
      background: #ede9fe;
      color: #7c3aed;
    }
    
    &.satisfaction {
      background: #d1fae5;
      color: #059669;
    }
  }
  
  .stat-info {
    display: flex;
    flex-direction: column;
    
    .stat-value {
      font-size: 26px;
      font-weight: 700;
      color: #1f2937;
      line-height: 1.2;
    }
    
    .stat-label {
      font-size: 13px;
      color: #6b7280;
    }
  }
}

.feedback-details {
  padding: 20px;
  background: #f8fafc;
  border-radius: 10px;
  margin-bottom: 24px;
  
  h4 {
    margin: 0 0 16px;
    font-size: 15px;
    font-weight: 600;
    color: #374151;
  }
  
  .feedback-breakdown {
    display: flex;
    gap: 24px;
    margin-bottom: 20px;
    
    .feedback-item {
      display: flex;
      align-items: center;
      gap: 10px;
      
      .el-icon {
        font-size: 24px;
      }
      
      &.positive {
        .el-icon {
          color: #10b981;
        }
      }
      
      &.negative {
        .el-icon {
          color: #ef4444;
        }
      }
      
      .feedback-count {
        font-size: 22px;
        font-weight: 700;
        color: #1f2937;
      }
      
      .feedback-label {
        font-size: 13px;
        color: #6b7280;
      }
    }
  }
  
  .satisfaction-bar {
    .bar-label {
      display: block;
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 8px;
    }
  }
}

.no-feedbacks {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 10px;
  margin-bottom: 24px;
  color: #6b7280;
  font-size: 14px;
  
  .el-icon {
    font-size: 18px;
    color: #9ca3af;
  }
}

.recent-activity {
  h4 {
    margin: 0 0 16px;
    font-size: 15px;
    font-weight: 600;
    color: #374151;
  }
  
  .activity-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    
    @media (max-width: 600px) {
      grid-template-columns: 1fr;
    }
    
    .activity-item {
      text-align: center;
      padding: 16px;
      background: #f8fafc;
      border-radius: 10px;
      
      .activity-label {
        display: block;
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 6px;
      }
      
      .activity-value {
        font-size: 15px;
        font-weight: 600;
        color: #1f2937;
      }
    }
  }
}
</style>