/**
 * Service API pour la gestion des configurations système
 * Sprint 12 - Phase 2
 */
import apiClient from './auth'

const API_BASE = '/config'

export const configService = {
  /**
   * Récupère toutes les configurations
   * @param {Object} params - Paramètres de filtrage (category, etc.)
   * @returns {Promise} Liste des configurations
   */
  async getAll(params = {}) {
    const response = await apiClient.get(API_BASE, { params })
    return response.data
  },

  /**
   * Récupère les configurations par catégorie
   * @param {string} category - Catégorie (models, pricing, chunking, etc.)
   * @returns {Promise} Configurations groupées par sous-clé
   */
  async getByCategory(category) {
    const response = await apiClient.get(`${API_BASE}/category/${category}`)
    return response.data
  },

  /**
   * Récupère une configuration spécifique
   * @param {string} key - Clé de la configuration (ex: "models.generation")
   * @returns {Promise} Configuration complète
   */
  async getByKey(key) {
    const response = await apiClient.get(`${API_BASE}/${key}`)
    return response.data
  },

  /**
   * Met à jour une configuration
   * @param {string} key - Clé de la configuration
   * @param {Object} data - Données de mise à jour { value, description }
   * @returns {Promise} Configuration mise à jour
   */
  async update(key, data) {
    const response = await apiClient.put(`${API_BASE}/${key}`, data)
    return response.data
  },

  /**
   * Récupère l'historique des modifications d'une configuration
   * @param {string} key - Clé de la configuration
   * @param {number} limit - Nombre max de résultats (défaut: 50)
   * @returns {Promise} Liste des modifications
   */
  async getHistory(key, limit = 50) {
    const response = await apiClient.get(`${API_BASE}/history/${key}`, {
      params: { limit }
    })
    return response.data
  }
}

export default configService