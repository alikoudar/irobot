/**
 * Service API pour la gestion des utilisateurs (admin)
 */
import apiClient from './auth'

/**
 * Service de gestion des utilisateurs
 */
export const usersService = {
  /**
   * Récupérer la liste paginée des utilisateurs
   * @param {Object} params - Paramètres de pagination et filtres
   * @param {number} params.skip - Nombre d'éléments à sauter
   * @param {number} params.limit - Nombre d'éléments par page
   * @param {string} params.search - Recherche (matricule, nom, prénom, email)
   * @param {string} params.role - Filtrer par rôle
   * @param {boolean} params.is_active - Filtrer par statut actif
   * @returns {Promise<Object>} Liste paginée d'utilisateurs
   */
  async getUsers(params = {}) {
    const response = await apiClient.get('/users', { params })
    return response.data
  },

  /**
   * Créer un nouvel utilisateur
   * @param {Object} userData - Données de l'utilisateur
   * @param {string} userData.matricule - Matricule unique
   * @param {string} userData.email - Email unique
   * @param {string} userData.nom - Nom de famille
   * @param {string} userData.prenom - Prénom
   * @param {string} userData.password - Mot de passe
   * @param {string} userData.role - Rôle (ADMIN, MANAGER, USER)
   * @param {boolean} userData.is_active - Statut actif
   * @returns {Promise<Object>} Utilisateur créé
   */
  async createUser(userData) {
    const response = await apiClient.post('/users', userData)
    return response.data
  },

  /**
   * Récupérer les détails d'un utilisateur
   * @param {string} userId - ID de l'utilisateur
   * @returns {Promise<Object>} Détails de l'utilisateur
   */
  async getUser(userId) {
    const response = await apiClient.get(`/users/${userId}`)
    return response.data
  },

  /**
   * Mettre à jour un utilisateur
   * @param {string} userId - ID de l'utilisateur
   * @param {Object} userData - Données à mettre à jour
   * @returns {Promise<Object>} Utilisateur mis à jour
   */
  async updateUser(userId, userData) {
    const response = await apiClient.put(`/users/${userId}`, userData)
    return response.data
  },

  /**
   * Supprimer un utilisateur
   * @param {string} userId - ID de l'utilisateur
   * @returns {Promise<void>}
   */
  async deleteUser(userId) {
    await apiClient.delete(`/users/${userId}`)
  },

  /**
   * Télécharger le template Excel
   * @returns {Promise<Blob>} Fichier Excel
   */
  async downloadTemplate() {
    const response = await apiClient.get('/users/import-excel/template', {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * Importer des utilisateurs depuis un fichier Excel
   * @param {File} file - Fichier Excel à importer
   * @returns {Promise<Object>} Résultat de l'import
   */
  async importExcel(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/users/import-excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  /**
   * Réinitialiser le mot de passe d'un utilisateur
   * @param {string} userId - ID de l'utilisateur
   * @param {string} newPassword - Nouveau mot de passe
   * @param {boolean} forceChange - Forcer le changement au prochain login
   * @returns {Promise<Object>} Message de confirmation
   */
  async resetPassword(userId, newPassword, forceChange = true) {
    const response = await apiClient.post(`/users/${userId}/reset-password`, {
      new_password: newPassword,
      force_change: forceChange
    })
    return response.data
  },

  /**
   * Récupérer les statistiques des utilisateurs
   * @returns {Promise<Object>} Statistiques
   */
  async getStats() {
    const response = await apiClient.get('/users/stats/overview')
    return response.data
  }
}

export default usersService