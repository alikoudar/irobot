/**
 * Dashboard Store - Sprint 10 Phase 3
 * 
 * Gère les statistiques et données du dashboard admin :
 * - Overview stats (users, documents, messages, cache, tokens, feedbacks)
 * - Top documents utilisés
 * - Timeline d'activité
 * - Activité utilisateurs
 * - Export des statistiques
 * 
 * Style : Composition API (comme chat.js)
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api/auth'
import { ElMessage } from 'element-plus'

const api = apiClient

export const useDashboardStore = defineStore('dashboard', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  // Données dashboard
  const stats = ref({})
  const topDocuments = ref([])
  const activityTimeline = ref([])
  const userActivity = ref([])
  
  // État
  const loading = ref(false)
  const error = ref(null)
  
  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /**
   * Vérifie si des données sont chargées
   */
  const hasData = computed(() => {
    return Object.keys(stats.value).length > 0
  })
  
  /**
   * Récupère le taux de satisfaction global
   */
  const overallSatisfactionRate = computed(() => {
    return stats.value.feedbacks?.satisfaction_rate || 0
  })
  
  /**
   * Récupère le taux de hit du cache
   */
  const cacheHitRate = computed(() => {
    return stats.value.cache?.hit_rate || 0
  })
  
  /**
   * Récupère le coût total en USD
   */
  const totalCostUSD = computed(() => {
    return stats.value.tokens?.total?.total_cost_usd || 0
  })
  
  /**
   * Récupère le coût total en XAF
   */
  const totalCostXAF = computed(() => {
    return stats.value.tokens?.total?.total_cost_xaf || 0
  })
  
  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /**
   * Récupère les statistiques générales du dashboard
   * @param {Date} startDate - Date de début
   * @param {Date} endDate - Date de fin
   */
  async function fetchStats(startDate, endDate) {
    loading.value = true
    error.value = null
    
    try {
      const params = {}
      if (startDate) params.start_date = startDate.toISOString()
      if (endDate) params.end_date = endDate.toISOString()
      
      const response = await api.get('/dashboard/overview', { params })
      stats.value = response.data
      
      console.log('📊 Dashboard stats loaded:', stats.value)
      return stats.value
      
    } catch (err) {
      console.error('❌ Error fetching dashboard stats:', err)
      error.value = err.response?.data?.message || 'Erreur lors du chargement des statistiques'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Récupère le top des documents les plus utilisés
   * @param {number} limit - Nombre de documents à récupérer
   * @param {Date} startDate - Date de début
   * @param {Date} endDate - Date de fin
   */
  async function fetchTopDocuments(limit = 10, startDate = null, endDate = null) {
    try {
      const params = { limit }
      if (startDate) params.start_date = startDate.toISOString()
      if (endDate) params.end_date = endDate.toISOString()
      
      const response = await api.get('/dashboard/top-documents', { params })
      topDocuments.value = response.data.documents || []
      
      console.log(`📈 Top ${limit} documents loaded:`, topDocuments.value.length)
      return topDocuments.value
      
    } catch (err) {
      console.error('❌ Error fetching top documents:', err)
      topDocuments.value = []
      return []
    }
  }
  
  /**
   * Récupère la timeline d'activité
   * @param {number} days - Nombre de jours à récupérer
   */
  async function fetchActivityTimeline(days = 30) {
    try {
      const response = await api.get('/dashboard/activity-timeline', {
        params: { days }
      })
      activityTimeline.value = response.data.timeline || []
      
      console.log(`📅 Activity timeline loaded: ${days} days,`, activityTimeline.value.length, 'entries')
      return activityTimeline.value
      
    } catch (err) {
      console.error('❌ Error fetching activity timeline:', err)
      activityTimeline.value = []
      return []
    }
  }
  
  /**
   * Récupère l'activité des utilisateurs
   * @param {Date} startDate - Date de début
   * @param {Date} endDate - Date de fin
   */
  async function fetchUserActivity(startDate = null, endDate = null) {
    try {
      const params = {}
      if (startDate) params.start_date = startDate.toISOString()
      if (endDate) params.end_date = endDate.toISOString()
      
      const response = await api.get('/dashboard/user-activity', { params })
      userActivity.value = response.data.users || []
      
      console.log('👥 User activity loaded:', userActivity.value.length, 'users')
      return userActivity.value
      
    } catch (err) {
      console.error('❌ Error fetching user activity:', err)
      userActivity.value = []
      return []
    }
  }
  
  /**
   * Exporte les statistiques du dashboard
   * @param {string} format - Format d'export (csv, json, xlsx)
   */
  async function exportStats(format = 'csv') {
    try {
      const response = await api.get('/dashboard/export', {
        params: { format },
        responseType: 'blob'
      })
      
      // Créer un lien de téléchargement
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `dashboard_stats_${new Date().toISOString().split('T')[0]}.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      
      console.log('✅ Stats exported:', format)
      ElMessage.success('Export réussi')
      return true
      
    } catch (err) {
      console.error('❌ Error exporting stats:', err)
      ElMessage.error('Erreur lors de l\'export')
      throw err
    }
  }
  
  /**
   * Réinitialise les données du dashboard
   */
  function reset() {
    stats.value = {}
    topDocuments.value = []
    activityTimeline.value = []
    userActivity.value = []
    loading.value = false
    error.value = null
    
    console.log('🔄 Dashboard store réinitialisé')
  }
  
  function $reset() {
    reset()
  }
  
  // ===========================================================================
  // RETURN
  // ===========================================================================
  
  return {
    // State
    stats,
    topDocuments,
    activityTimeline,
    userActivity,
    loading,
    error,
    
    // Getters
    hasData,
    overallSatisfactionRate,
    cacheHitRate,
    totalCostUSD,
    totalCostXAF,
    
    // Actions
    fetchStats,
    fetchTopDocuments,
    fetchActivityTimeline,
    fetchUserActivity,
    exportStats,
    reset,
    $reset
  }
})