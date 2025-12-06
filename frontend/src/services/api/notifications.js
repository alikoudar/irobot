/**
 * Service API pour les notifications
 * Sprint 14
 */
import apiClient from './auth'

/**
 * Service de gestion des notifications
 */
export const notificationsService = {
  /**
   * Récupérer les notifications de l'utilisateur
   * @param {Object} params - Paramètres de requête
   * @param {number} params.skip - Offset
   * @param {number} params.limit - Limite
   * @param {boolean} params.unread_only - Uniquement non lues
   * @returns {Promise<Object>} Liste paginée de notifications
   */
  async getNotifications(params = {}) {
    const response = await apiClient.get('/notifications', { params })
    return response.data
  },

  /**
   * Récupérer le nombre de notifications non lues
   * @returns {Promise<Object>} { count: number }
   */
  async getUnreadCount() {
    const response = await apiClient.get('/notifications/unread-count')
    return response.data
  },

  /**
   * Marquer une notification comme lue
   * @param {string} notificationId - ID de la notification
   * @returns {Promise<Object>} Notification mise à jour
   */
  async markAsRead(notificationId) {
    const response = await apiClient.post(`/notifications/${notificationId}/read`)
    return response.data
  },

  /**
   * Marquer toutes les notifications comme lues
   * @returns {Promise<Object>} { updated_count: number }
   */
  async markAllAsRead() {
    const response = await apiClient.post('/notifications/read-all')
    return response.data
  },

  /**
   * Rejeter (dismiss) une notification
   * @param {string} notificationId - ID de la notification
   * @returns {Promise<Object>} Notification mise à jour
   */
  async dismiss(notificationId) {
    const response = await apiClient.post(`/notifications/${notificationId}/dismiss`)
    return response.data
  },

  /**
   * Rejeter toutes les notifications
   * @returns {Promise<Object>} { count: number }
   */
  async dismissAll() {
    const response = await apiClient.post('/notifications/dismiss-all')
    return response.data
  },

  /**
   * Supprimer une notification
   * @param {string} notificationId - ID de la notification
   * @returns {Promise<void>}
   */
  async deleteNotification(notificationId) {
    await apiClient.delete(`/notifications/${notificationId}`)
  },

  /**
   * Supprimer toutes les notifications lues
   * @returns {Promise<Object>} { deleted_count: number }
   */
  async deleteAllRead() {
    const response = await apiClient.delete('/notifications/read')
    return response.data
  }
}

export default notificationsService