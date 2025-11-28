/**
 * Manager Dashboard Store - Sprint 11 Phase 2
 * 
 * Gère les statistiques du dashboard manager (version simplifiée) :
 * - Stats documents (total, completed, processing, failed, chunks)
 * - Messages utilisant les documents du manager
 * - Documents par catégorie
 * - Top documents les plus utilisés
 * - Timeline des uploads
 * 
 * PAS DE COÛTS, PAS DE FEEDBACKS (contrairement au dashboard admin)
 * 
 * Style : Composition API
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api/auth'
import { ElMessage } from 'element-plus'

const api = apiClient

export const useManagerDashboardStore = defineStore('managerDashboard', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  // Données dashboard
  const stats = ref({})
  const topDocuments = ref([])
  const timeline = ref([])
  
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
   * Calcule le taux de complétion des documents
   */
  const documentCompletionRate = computed(() => {
    const total = stats.value.documents?.total || 0
    const completed = stats.value.documents?.completed || 0
    return total > 0 ? Math.round((completed / total) * 100) : 0
  })
  
  /**
   * Récupère le nombre total de documents
   */
  const totalDocuments = computed(() => {
    return stats.value.documents?.total || 0
  })
  
  /**
   * Récupère le nombre de documents complétés
   */
  const completedDocuments = computed(() => {
    return stats.value.documents?.completed || 0
  })
  
  /**
   * Récupère le nombre total de messages
   */
  const totalMessages = computed(() => {
    return stats.value.messages?.total || 0
  })
  
  /**
   * Récupère le nombre total de chunks
   */
  const totalChunks = computed(() => {
    return stats.value.documents?.total_chunks || 0
  })
  
  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /**
   * Récupère les statistiques générales du dashboard manager
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
      
      const response = await api.get('/manager/dashboard/stats', { params })
      stats.value = response.data
      
      console.log('📊 Manager dashboard stats loaded:', stats.value)
      return stats.value
      
    } catch (err) {
      console.error('❌ Error fetching manager dashboard stats:', err)
      error.value = err.response?.data?.message || 'Erreur lors du chargement des statistiques'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Récupère le top des documents les plus utilisés du manager
   * @param {number} limit - Nombre de documents à récupérer
   */
  async function fetchTopDocuments(limit = 10) {
    try {
      const params = { limit }
      
      const response = await api.get('/manager/dashboard/top-documents', { params })
      topDocuments.value = response.data.documents || []
      
      console.log(`📈 Top ${limit} manager documents loaded:`, topDocuments.value.length)
      return topDocuments.value
      
    } catch (err) {
      console.error('❌ Error fetching top documents:', err)
      topDocuments.value = []
      return []
    }
  }
  
  /**
   * Récupère la timeline des uploads du manager
   * @param {number} days - Nombre de jours à récupérer
   */
  async function fetchTimeline(days = 30) {
    try {
      const response = await api.get('/manager/dashboard/documents-timeline', {
        params: { days }
      })
      timeline.value = response.data.timeline || []
      
      console.log(`📅 Manager timeline loaded: ${days} days,`, timeline.value.length, 'entries')
      return timeline.value
      
    } catch (err) {
      console.error('❌ Error fetching timeline:', err)
      timeline.value = []
      return []
    }
  }
  
  /**
   * Réinitialise les données du dashboard
   */
  function reset() {
    stats.value = {}
    topDocuments.value = []
    timeline.value = []
    loading.value = false
    error.value = null
    
    console.log('🔄 Manager dashboard store réinitialisé')
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
    timeline,
    loading,
    error,
    
    // Getters
    hasData,
    documentCompletionRate,
    totalDocuments,
    completedDocuments,
    totalMessages,
    totalChunks,
    
    // Actions
    fetchStats,
    fetchTopDocuments,
    fetchTimeline,
    reset,
    $reset
  }
})