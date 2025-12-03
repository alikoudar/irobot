/**
 * Store Pinia pour la gestion des logs d'audit
 * Sprint 13 - Complément : Audit Logs Admin
 * 
 * Gère :
 * - Chargement des logs avec pagination et filtrage
 * - Statistiques globales
 * - Activité par date
 * - Options de filtrage
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auditLogsService } from '@/services/api/auditLogs'
import { ElMessage } from 'element-plus'

export const useAuditLogsStore = defineStore('auditLogs', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  // Liste des logs
  const logs = ref([])
  
  // Pagination
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  
  // Filtres appliqués
  const filters = ref({
    user_id: null,
    action: null,
    entity_type: null,
    start_date: null,
    end_date: null,
    search: ''
  })
  
  // Options de filtrage disponibles
  const filterOptions = ref({
    actions: [],
    entity_types: []
  })
  
  // Statistiques
  const stats = ref({
    total_logs: 0,
    logs_today: 0,
    logs_this_week: 0,
    logs_this_month: 0,
    by_action: {},
    by_entity_type: {},
    last_activity: null
  })
  
  // Activité par date
  const activity = ref({
    start_date: null,
    end_date: null,
    total: 0,
    daily_activity: []
  })
  
  // Log sélectionné (pour détails)
  const selectedLog = ref(null)
  
  // États de chargement
  const loading = ref(false)
  const loadingStats = ref(false)
  const loadingActivity = ref(false)
  const error = ref(null)
  
  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /**
   * Vérifie si des logs sont chargés
   */
  const hasLogs = computed(() => logs.value.length > 0)
  
  /**
   * Nombre de logs affichés
   */
  const logsCount = computed(() => logs.value.length)
  
  /**
   * Vérifie si des filtres sont actifs
   */
  const hasActiveFilters = computed(() => {
    return !!(
      filters.value.user_id ||
      filters.value.action ||
      filters.value.entity_type ||
      filters.value.start_date ||
      filters.value.end_date ||
      filters.value.search
    )
  })
  
  /**
   * Actions groupées par catégorie
   */
  const actionsByCategory = computed(() => {
    const grouped = {}
    filterOptions.value.actions.forEach(action => {
      const category = action.category || 'OTHER'
      if (!grouped[category]) {
        grouped[category] = []
      }
      grouped[category].push(action)
    })
    return grouped
  })
  
  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /**
   * Récupère les logs avec pagination et filtrage
   */
  async function fetchLogs(options = {}) {
    loading.value = true
    error.value = null
    
    // Construire les paramètres
    const params = {
      page: options.page || page.value,
      page_size: options.page_size || pageSize.value
    }
    
    // Ajouter les filtres non vides
    if (filters.value.user_id) params.user_id = filters.value.user_id
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.entity_type) params.entity_type = filters.value.entity_type
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    if (filters.value.search) params.search = filters.value.search
    
    try {
      const data = await auditLogsService.getLogs(params)
      
      logs.value = data.items || []
      total.value = data.total || 0
      page.value = data.page || 1
      pageSize.value = data.page_size || 20
      totalPages.value = data.total_pages || 0
      
      console.log('✅ Logs d\'audit chargés:', logs.value.length, '/', total.value)
      return logs.value
      
    } catch (err) {
      console.error('❌ Erreur chargement logs:', err)
      error.value = err.response?.data?.detail || 'Erreur lors du chargement des logs'
      ElMessage.error(error.value)
      throw err
      
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Récupère les statistiques globales
   */
  async function fetchStats() {
    loadingStats.value = true
    
    try {
      const data = await auditLogsService.getStats()
      stats.value = data
      
      console.log('✅ Stats logs chargées:', data.total_logs, 'logs')
      return stats.value
      
    } catch (err) {
      console.error('❌ Erreur chargement stats:', err)
      ElMessage.error('Erreur lors du chargement des statistiques')
      throw err
      
    } finally {
      loadingStats.value = false
    }
  }
  
  /**
   * Récupère l'activité par date
   */
  async function fetchActivity(startDate = null, endDate = null) {
    loadingActivity.value = true
    
    try {
      const data = await auditLogsService.getActivity(startDate, endDate)
      activity.value = data
      
      console.log('✅ Activité chargée:', data.total, 'logs sur', data.daily_activity?.length, 'jours')
      return activity.value
      
    } catch (err) {
      console.error('❌ Erreur chargement activité:', err)
      ElMessage.error('Erreur lors du chargement de l\'activité')
      throw err
      
    } finally {
      loadingActivity.value = false
    }
  }
  
  /**
   * Récupère les options de filtrage
   */
  async function fetchFilterOptions() {
    try {
      const data = await auditLogsService.getFilters()
      filterOptions.value = data
      
      console.log('✅ Options filtrage chargées:', data.actions?.length, 'actions')
      return filterOptions.value
      
    } catch (err) {
      console.error('❌ Erreur chargement options filtrage:', err)
      // Ne pas afficher d'erreur, ce n'est pas critique
    }
  }
  
  /**
   * Récupère un log spécifique
   */
  async function fetchLogById(logId) {
    loading.value = true
    
    try {
      const data = await auditLogsService.getLogById(logId)
      selectedLog.value = data
      
      return selectedLog.value
      
    } catch (err) {
      console.error('❌ Erreur chargement log:', err)
      ElMessage.error('Erreur lors du chargement du log')
      throw err
      
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Met à jour les filtres et recharge les logs
   */
  async function updateFilters(newFilters) {
    // Mettre à jour les filtres
    Object.assign(filters.value, newFilters)
    
    // Revenir à la page 1
    page.value = 1
    
    // Recharger les logs
    await fetchLogs()
  }
  
  /**
   * Réinitialise les filtres
   */
  async function resetFilters() {
    filters.value = {
      user_id: null,
      action: null,
      entity_type: null,
      start_date: null,
      end_date: null,
      search: ''
    }
    
    page.value = 1
    await fetchLogs()
  }
  
  /**
   * Change de page
   */
  async function changePage(newPage) {
    page.value = newPage
    await fetchLogs()
  }
  
  /**
   * Change la taille de page
   */
  async function changePageSize(newSize) {
    pageSize.value = newSize
    page.value = 1
    await fetchLogs()
  }
  
  /**
   * Initialise le store (charge tout)
   */
  async function initialize() {
    await Promise.all([
      fetchFilterOptions(),
      fetchStats(),
      fetchLogs()
    ])
  }
  
  // ===========================================================================
  // EXPORT
  // ===========================================================================
  
  return {
    // State
    logs,
    total,
    page,
    pageSize,
    totalPages,
    filters,
    filterOptions,
    stats,
    activity,
    selectedLog,
    loading,
    loadingStats,
    loadingActivity,
    error,
    
    // Getters
    hasLogs,
    logsCount,
    hasActiveFilters,
    actionsByCategory,
    
    // Actions
    fetchLogs,
    fetchStats,
    fetchActivity,
    fetchFilterOptions,
    fetchLogById,
    updateFilters,
    resetFilters,
    changePage,
    changePageSize,
    initialize
  }
})