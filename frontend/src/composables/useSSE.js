/**
 * Composable pour la gestion des connexions Server-Sent Events (SSE).
 * 
 * Fournit une interface réutilisable pour :
 * - Établir une connexion SSE avec authentification
 * - Recevoir et parser les événements
 * - Gérer les erreurs et reconnexions
 * - Fermer proprement la connexion
 * 
 * Sprint 8 - Phase 1 : Stores & Composables
 */
import { ref, onUnmounted } from 'vue'

/**
 * Configuration par défaut pour les connexions SSE.
 */
const DEFAULT_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000,
  heartbeatTimeout: 30000
}

/**
 * Composable pour gérer une connexion SSE.
 * 
 * @param {Object} options - Options de configuration
 * @param {number} options.maxRetries - Nombre max de tentatives de reconnexion
 * @param {number} options.retryDelay - Délai entre les tentatives (ms)
 * @param {number} options.heartbeatTimeout - Timeout pour le heartbeat (ms)
 * @returns {Object} API du composable
 */
export function useSSE(options = {}) {
  const config = { ...DEFAULT_CONFIG, ...options }
  
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  /**
   * Connexion EventSource active
   */
  const eventSource = ref(null)
  
  /**
   * Indique si la connexion est active
   */
  const isConnected = ref(false)
  
  /**
   * Indique si une tentative de connexion est en cours
   */
  const isConnecting = ref(false)
  
  /**
   * Dernière erreur survenue
   */
  const error = ref(null)
  
  /**
   * Nombre de tentatives de reconnexion effectuées
   */
  const retryCount = ref(0)
  
  /**
   * AbortController pour annuler les requêtes fetch
   */
  let abortController = null
  
  /**
   * Timeout pour le heartbeat
   */
  let heartbeatTimer = null
  
  // ===========================================================================
  // HELPERS
  // ===========================================================================
  
  /**
   * Récupérer le token d'authentification.
   * 
   * @returns {string|null} Token JWT ou null
   */
  function getAuthToken() {
    return localStorage.getItem('access_token')
  }
  
  /**
   * Réinitialiser le timer heartbeat.
   */
  function resetHeartbeatTimer() {
    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer)
    }
    
    heartbeatTimer = setTimeout(() => {
      console.warn('⚠️ SSE heartbeat timeout')
      error.value = { type: 'timeout', message: 'Connexion perdue (timeout)' }
    }, config.heartbeatTimeout)
  }
  
  /**
   * Parser une ligne de données SSE.
   * 
   * @param {string} line - Ligne à parser
   * @returns {Object|null} Données parsées ou null
   */
  function parseSSELine(line) {
    if (!line || line.startsWith(':')) {
      // Commentaire SSE (heartbeat)
      return null
    }
    
    if (line.startsWith('data:')) {
      const dataStr = line.slice(5).trim()
      
      if (!dataStr || dataStr === '[DONE]') {
        return { type: 'done' }
      }
      
      try {
        return JSON.parse(dataStr)
      } catch (e) {
        console.warn('⚠️ Erreur parsing SSE:', e)
        return { type: 'raw', data: dataStr }
      }
    }
    
    if (line.startsWith('event:')) {
      return { type: 'event', name: line.slice(6).trim() }
    }
    
    return null
  }
  
  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /**
   * Établir une connexion SSE vers une URL.
   * 
   * @param {string} url - URL de l'endpoint SSE
   * @param {Object} callbacks - Callbacks pour les événements
   * @param {Function} callbacks.onMessage - Appelé pour chaque message reçu
   * @param {Function} callbacks.onError - Appelé en cas d'erreur
   * @param {Function} callbacks.onClose - Appelé à la fermeture de la connexion
   * @param {Function} callbacks.onOpen - Appelé à l'ouverture de la connexion
   * @param {Object} fetchOptions - Options supplémentaires pour fetch
   * @returns {Promise<boolean>} Succès de la connexion
   */
  async function connectSSE(url, callbacks = {}, fetchOptions = {}) {
    const { onMessage, onError, onClose, onOpen } = callbacks
    
    // Fermer toute connexion existante
    closeSSE()
    
    isConnecting.value = true
    error.value = null
    
    try {
      const token = getAuthToken()
      
      // Créer l'AbortController
      abortController = new AbortController()
      
      // Préparer les headers
      const headers = {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        ...fetchOptions.headers
      }
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      // Effectuer la requête
      const response = await fetch(url, {
        method: fetchOptions.method || 'GET',
        headers,
        body: fetchOptions.body,
        signal: abortController.signal
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      // Marquer comme connecté
      isConnected.value = true
      isConnecting.value = false
      retryCount.value = 0
      
      if (onOpen) {
        onOpen()
      }
      
      console.log('✅ SSE connecté:', url)
      
      // Lire le stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      resetHeartbeatTimer()
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          console.log('📡 SSE stream terminé')
          break
        }
        
        // Réinitialiser le heartbeat à chaque réception
        resetHeartbeatTimer()
        
        // Décoder et buffer
        buffer += decoder.decode(value, { stream: true })
        
        // Parser les lignes complètes
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          const parsed = parseSSELine(line)
          
          if (parsed && onMessage) {
            onMessage(parsed)
          }
          
          if (parsed?.type === 'done') {
            break
          }
        }
      }
      
      // Fermeture normale
      isConnected.value = false
      
      if (onClose) {
        onClose()
      }
      
      return true
      
    } catch (err) {
      isConnecting.value = false
      isConnected.value = false
      
      if (err.name === 'AbortError') {
        console.log('⚠️ SSE connexion annulée')
        return false
      }
      
      error.value = {
        type: 'connection',
        message: err.message
      }
      
      console.error('❌ Erreur SSE:', err)
      
      if (onError) {
        onError(err)
      }
      
      // Tentative de reconnexion
      if (retryCount.value < config.maxRetries) {
        retryCount.value++
        console.log(`🔄 Reconnexion SSE (${retryCount.value}/${config.maxRetries})...`)
        
        await new Promise(resolve => setTimeout(resolve, config.retryDelay))
        return connectSSE(url, callbacks, fetchOptions)
      }
      
      return false
    } finally {
      if (heartbeatTimer) {
        clearTimeout(heartbeatTimer)
        heartbeatTimer = null
      }
    }
  }
  
  /**
   * Établir une connexion SSE avec POST (pour envoyer des données).
   * 
   * @param {string} url - URL de l'endpoint SSE
   * @param {Object} data - Données à envoyer
   * @param {Object} callbacks - Callbacks pour les événements
   * @returns {Promise<boolean>} Succès de la connexion
   */
  async function connectSSEPost(url, data, callbacks = {}) {
    return connectSSE(url, callbacks, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
  }
  
  /**
   * Fermer la connexion SSE.
   */
  function closeSSE() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    
    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer)
      heartbeatTimer = null
    }
    
    isConnected.value = false
    isConnecting.value = false
    
    console.log('🔌 SSE déconnecté')
  }
  
  /**
   * Réinitialiser le compteur de reconnexions.
   */
  function resetRetryCount() {
    retryCount.value = 0
  }
  
  // ===========================================================================
  // LIFECYCLE
  // ===========================================================================
  
  // Fermer la connexion quand le composant est démonté
  onUnmounted(() => {
    closeSSE()
  })
  
  // ===========================================================================
  // RETURN
  // ===========================================================================
  
  return {
    // State
    eventSource,
    isConnected,
    isConnecting,
    error,
    retryCount,
    
    // Actions
    connectSSE,
    connectSSEPost,
    closeSSE,
    resetRetryCount
  }
}

export default useSSE