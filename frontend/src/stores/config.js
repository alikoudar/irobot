/**
 * Store Pinia pour la gestion des configurations système
 * Sprint 12 - Phase 2
 * 
 * Gère :
 * - Chargement des configurations par catégorie
 * - Mise à jour des configurations
 * - Historique des modifications
 * - Cache local des configurations
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { configService } from '@/services/api/config'
import { ElMessage } from 'element-plus'

export const useConfigStore = defineStore('config', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  // Configurations par catégorie
  const configs = ref({
    pricing: {},
    models: {},
    chunking: {},
    embedding: {},
    search: {},
    upload: {},
    rate_limit: {},
    cache: {},
    exchange_rate: {}
  })
  
  // Liste complète des configurations
  const allConfigs = ref([])
  
  // Historique de modification
  const history = ref([])
  
  // État
  const loading = ref(false)
  const saving = ref(false)
  const error = ref(null)
  
  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /**
   * Vérifie si les configs sont chargées
   */
  const hasConfigs = computed(() => {
    return Object.keys(configs.value.models || {}).length > 0
  })
  
  /**
   * Compte le nombre total de configurations
   */
  const totalConfigs = computed(() => {
    return allConfigs.value.length
  })
  
  /**
   * Récupère les modèles disponibles
   */
  const availableModels = computed(() => {
    return configs.value.models || {}
  })
  
  /**
   * Récupère les tarifs
   */
  const pricing = computed(() => {
    return configs.value.pricing || {}
  })
  
  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /**
   * Charge toutes les configurations
   */
  async function fetchAllConfigs(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const data = await configService.getAll(params)
      allConfigs.value = data.items || []
      
      console.log('✅ All configs loaded:', allConfigs.value.length)
      return allConfigs.value
    } catch (err) {
      error.value = err.message
      console.error('❌ Error loading configs:', err)
      ElMessage.error('Erreur lors du chargement des configurations')
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Charge les configurations d'une catégorie
   * @param {string} category - Catégorie à charger
   */
  async function fetchCategory(category) {
    loading.value = true
    error.value = null
    
    try {
      const data = await configService.getByCategory(category)
      configs.value[category] = data
      
      console.log(`✅ Category ${category} loaded:`, Object.keys(data).length, 'configs')
      return data
    } catch (err) {
      error.value = err.message
      console.error(`❌ Error loading category ${category}:`, err)
      ElMessage.error(`Erreur lors du chargement de la catégorie ${category}`)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Charge toutes les catégories nécessaires
   */
  async function fetchAllCategories() {
    loading.value = true
    error.value = null
    
    try {
      const categories = ['pricing', 'models', 'chunking', 'embedding', 'search', 'upload', 'rate_limit', 'cache', 'exchange_rate']
      
      await Promise.all(
        categories.map(category => fetchCategory(category))
      )
      
      console.log('✅ All categories loaded')
    } catch (err) {
      error.value = err.message
      console.error('❌ Error loading categories:', err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Récupère une configuration spécifique
   * @param {string} key - Clé de la configuration
   */
  async function fetchConfig(key) {
    loading.value = true
    error.value = null
    
    try {
      const data = await configService.getByKey(key)
      
      console.log(`✅ Config ${key} loaded`)
      return data
    } catch (err) {
      error.value = err.message
      console.error(`❌ Error loading config ${key}:`, err)
      ElMessage.error(`Erreur lors du chargement de la configuration ${key}`)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Met à jour une configuration
   * @param {string} key - Clé de la configuration
   * @param {Object} value - Nouvelle valeur
   * @param {string} description - Description (optionnel)
   */
  async function updateConfig(key, value, description = null) {
    saving.value = true
    error.value = null
    
    try {
      const data = await configService.update(key, {
        value,
        description
      })
      
      // Mettre à jour le cache local
      const [category, subKey] = key.split('.')
      if (configs.value[category]) {
        configs.value[category][subKey] = value
      }
      
      // Mettre à jour allConfigs si présent
      const index = allConfigs.value.findIndex(c => c.key === key)
      if (index !== -1) {
        allConfigs.value[index] = data
      }
      
      console.log(`✅ Config ${key} updated`)
      ElMessage.success('Configuration mise à jour avec succès')
      
      return data
    } catch (err) {
      error.value = err.message
      console.error(`❌ Error updating config ${key}:`, err)
      
      // Message d'erreur plus spécifique
      if (err.response?.status === 400) {
        ElMessage.error(err.response.data.detail || 'Valeur invalide')
      } else {
        ElMessage.error('Erreur lors de la mise à jour de la configuration')
      }
      
      throw err
    } finally {
      saving.value = false
    }
  }
  
  /**
   * Récupère l'historique des modifications d'une configuration
   * @param {string} key - Clé de la configuration
   * @param {number} limit - Nombre max de résultats
   */
  async function fetchHistory(key, limit = 50) {
    loading.value = true
    error.value = null
    
    try {
      const data = await configService.getHistory(key, limit)
      history.value = data
      
      console.log(`✅ History for ${key} loaded:`, data.length, 'entries')
      return data
    } catch (err) {
      error.value = err.message
      console.error(`❌ Error loading history for ${key}:`, err)
      ElMessage.error('Erreur lors du chargement de l\'historique')
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Réinitialise l'état du store
   */
  function reset() {
    configs.value = {
      pricing: {},
      models: {},
      chunking: {},
      embedding: {},
      search: {},
      upload: {},
      rate_limit: {},
      cache: {},
      exchange_rate: {}
    }
    allConfigs.value = []
    history.value = []
    error.value = null
  }
  
  // ===========================================================================
  // RETURN
  // ===========================================================================
  
  return {
    // State
    configs,
    allConfigs,
    history,
    loading,
    saving,
    error,
    
    // Getters
    hasConfigs,
    totalConfigs,
    availableModels,
    pricing,
    
    // Actions
    fetchAllConfigs,
    fetchCategory,
    fetchAllCategories,
    fetchConfig,
    updateConfig,
    fetchHistory,
    reset
  }
})

export default useConfigStore