/**
 * Service API pour la gestion des logs d'audit
 * Sprint 13 - Complément : Audit Logs Admin
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Instance axios configurée
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Intercepteur pour ajouter le token aux requêtes
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * Service des logs d'audit
 */
export const auditLogsService = {
  /**
   * Récupère la liste paginée des logs d'audit
   * @param {Object} params - Paramètres de filtrage et pagination
   * @returns {Promise} Liste des logs avec pagination
   */
  async getLogs(params = {}) {
    const response = await apiClient.get('/audit-logs/', { params })
    return response.data
  },

  /**
   * Récupère les statistiques des logs d'audit
   * @returns {Promise} Statistiques globales
   */
  async getStats() {
    const response = await apiClient.get('/audit-logs/stats')
    return response.data
  },

  /**
   * Récupère l'activité par date sur une période
   * @param {string} startDate - Date de début (YYYY-MM-DD)
   * @param {string} endDate - Date de fin (YYYY-MM-DD)
   * @returns {Promise} Activité quotidienne
   */
  async getActivity(startDate = null, endDate = null) {
    const params = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    
    const response = await apiClient.get('/audit-logs/activity', { params })
    return response.data
  },

  /**
   * Récupère les options de filtrage disponibles
   * @returns {Promise} Actions et types d'entités disponibles
   */
  async getFilters() {
    const response = await apiClient.get('/audit-logs/filters')
    return response.data
  },

  /**
   * Récupère un log d'audit spécifique
   * @param {string} logId - UUID du log
   * @returns {Promise} Détail du log
   */
  async getLogById(logId) {
    const response = await apiClient.get(`/audit-logs/${logId}`)
    return response.data
  },

  /**
   * Récupère les logs d'un utilisateur spécifique
   * @param {string} userId - UUID de l'utilisateur
   * @param {number} limit - Nombre max de résultats
   * @returns {Promise} Liste des logs de l'utilisateur
   */
  async getUserLogs(userId, limit = 50) {
    const response = await apiClient.get(`/audit-logs/user/${userId}`, {
      params: { limit }
    })
    return response.data
  }
}

export default auditLogsService