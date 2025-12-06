// ==============================================================================
// COMPOSABLE USE SSE - SPRINT 14
// ==============================================================================
// Gestion réutilisable des connexions SSE
// ==============================================================================

import { ref, onMounted, onUnmounted, watch } from 'vue'

/**
 * Composable pour gérer une connexion SSE
 * 
 * @param {string} endpoint - URL de l'endpoint SSE (sans le token)
 * @param {Object} options - Options de configuration
 * @param {boolean} options.autoConnect - Connexion automatique au montage (défaut: true)
 * @param {boolean} options.autoReconnect - Reconnexion automatique (défaut: true)
 * @param {number} options.reconnectDelay - Délai de reconnexion en ms (défaut: 5000)
 * @param {number} options.maxRetries - Nombre max de tentatives (défaut: 5)
 * @param {Object} options.eventHandlers - Map des handlers par type d'événement
 * 
 * @example
 * const { connected, connect, disconnect, lastEvent } = useSSE('/notifications/stream', {
 *   eventHandlers: {
 *     notification: (data) => console.log('New notification:', data),
 *     heartbeat: () => console.log('Connection alive')
 *   }
 * })
 */
export function useSSE(endpoint, options = {}) {
  // Options avec valeurs par défaut
  const {
    autoConnect = true,
    autoReconnect = true,
    reconnectDelay = 5000,
    maxRetries = 5,
    eventHandlers = {}
  } = options
  
  // ==========================================================================
  // STATE
  // ==========================================================================
  
  /** Connexion active */
  const connected = ref(false)
  
  /** En cours de connexion */
  const connecting = ref(false)
  
  /** Dernier événement reçu */
  const lastEvent = ref(null)
  
  /** Dernière erreur */
  const error = ref(null)
  
  /** Nombre de tentatives de reconnexion */
  const retryCount = ref(0)
  
  /** EventSource instance */
  let eventSource = null
  
  /** Timer de reconnexion */
  let reconnectTimer = null
  
  // ==========================================================================
  // MÉTHODES
  // ==========================================================================
  
  /**
   * Établir la connexion SSE
   */
  function connect() {
    // Éviter les connexions multiples
    if (eventSource || connecting.value) {
      return
    }
    
    connecting.value = true
    error.value = null
    
    const token = localStorage.getItem('access_token')
    if (!token) {
      error.value = 'Token non disponible'
      connecting.value = false
      return
    }
    
    const baseUrl = import.meta.env.VITE_API_URL || ''
    const url = `${baseUrl}/api/v1${endpoint}?token=${token}`
    
    try {
      eventSource = new EventSource(url)
      
      // Événement d'ouverture
      eventSource.onopen = () => {
        connected.value = true
        connecting.value = false
        retryCount.value = 0
        console.log(`SSE [${endpoint}]: Connecté`)
      }
      
      // Événement d'erreur
      eventSource.onerror = (event) => {
        console.error(`SSE [${endpoint}]: Erreur`, event)
        
        connected.value = false
        connecting.value = false
        
        // Fermer la connexion actuelle
        if (eventSource) {
          eventSource.close()
          eventSource = null
        }
        
        // Reconnexion automatique si activée
        if (autoReconnect && retryCount.value < maxRetries) {
          retryCount.value++
          error.value = `Reconnexion (${retryCount.value}/${maxRetries})...`
          
          reconnectTimer = setTimeout(() => {
            console.log(`SSE [${endpoint}]: Tentative de reconnexion ${retryCount.value}`)
            connect()
          }, reconnectDelay * retryCount.value) // Backoff exponentiel
        } else if (retryCount.value >= maxRetries) {
          error.value = 'Nombre maximum de tentatives atteint'
        }
      }
      
      // Événement message générique (sans type spécifié)
      eventSource.onmessage = (event) => {
        handleEvent('message', event.data)
      }
      
      // Enregistrer les handlers d'événements personnalisés
      for (const [eventType, handler] of Object.entries(eventHandlers)) {
        eventSource.addEventListener(eventType, (event) => {
          handleEvent(eventType, event.data)
          if (handler) {
            try {
              const data = JSON.parse(event.data)
              handler(data)
            } catch (e) {
              handler(event.data)
            }
          }
        })
      }
      
      // Handler pour 'connected' (événement standard)
      if (!eventHandlers.connected) {
        eventSource.addEventListener('connected', (event) => {
          handleEvent('connected', event.data)
        })
      }
      
      // Handler pour 'heartbeat' (événement standard)
      if (!eventHandlers.heartbeat) {
        eventSource.addEventListener('heartbeat', (event) => {
          // Silencieux pour les heartbeats
          lastEvent.value = { type: 'heartbeat', timestamp: new Date() }
        })
      }
      
    } catch (e) {
      error.value = e.message
      connecting.value = false
      console.error(`SSE [${endpoint}]: Erreur création`, e)
    }
  }
  
  /**
   * Fermer la connexion SSE
   */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    
    connected.value = false
    connecting.value = false
    console.log(`SSE [${endpoint}]: Déconnecté`)
  }
  
  /**
   * Gérer un événement reçu
   */
  function handleEvent(type, rawData) {
    try {
      const data = JSON.parse(rawData)
      lastEvent.value = {
        type,
        data,
        timestamp: new Date()
      }
    } catch (e) {
      lastEvent.value = {
        type,
        data: rawData,
        timestamp: new Date()
      }
    }
  }
  
  /**
   * Réinitialiser le compteur de retry et reconnecter
   */
  function reconnect() {
    disconnect()
    retryCount.value = 0
    connect()
  }
  
  // ==========================================================================
  // LIFECYCLE
  // ==========================================================================
  
  onMounted(() => {
    if (autoConnect) {
      connect()
    }
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  // ==========================================================================
  // EXPORTS
  // ==========================================================================
  
  return {
    // State
    connected,
    connecting,
    lastEvent,
    error,
    retryCount,
    
    // Methods
    connect,
    disconnect,
    reconnect
  }
}

/**
 * Composable spécialisé pour le suivi du status d'un document
 * 
 * @param {string} documentId - ID du document à suivre
 * @param {Object} options - Options de configuration
 * 
 * @example
 * const { status, progress, stage, connect, disconnect } = useDocumentStatusSSE(documentId)
 */
export function useDocumentStatusSSE(documentId, options = {}) {
  const status = ref('PENDING')
  const progress = ref(0)
  const stage = ref(null)
  const errorMessage = ref(null)
  const totalChunks = ref(null)
  const processingTime = ref(null)
  const isComplete = ref(false)
  const isFailed = ref(false)
  
  const { connected, connect, disconnect, lastEvent } = useSSE(
    `/documents/${documentId}/status`,
    {
      autoConnect: options.autoConnect ?? true,
      eventHandlers: {
        status: (data) => {
          status.value = data.status
          progress.value = data.progress || 0
          stage.value = data.stage
          errorMessage.value = data.error_message
          totalChunks.value = data.total_chunks
          processingTime.value = data.processing_time
          
          if (data.status === 'COMPLETED') {
            isComplete.value = true
          } else if (data.status === 'FAILED') {
            isFailed.value = true
          }
          
          // Callback optionnel
          if (options.onStatusChange) {
            options.onStatusChange(data)
          }
        },
        complete: (data) => {
          isComplete.value = true
          if (options.onComplete) {
            options.onComplete(data)
          }
          // Auto-déconnexion
          disconnect()
        },
        error: (data) => {
          isFailed.value = true
          errorMessage.value = data.error_message
          if (options.onError) {
            options.onError(data)
          }
          disconnect()
        }
      }
    }
  )
  
  return {
    // State
    status,
    progress,
    stage,
    errorMessage,
    totalChunks,
    processingTime,
    isComplete,
    isFailed,
    connected,
    lastEvent,
    
    // Methods
    connect,
    disconnect
  }
}

/**
 * Composable pour les événements admin
 * 
 * @example
 * const { feedbacks, documents, connect } = useAdminEventsSSE()
 */
export function useAdminEventsSSE(options = {}) {
  const feedbacks = ref([])
  const documents = ref([])
  
  const { connected, connect, disconnect, lastEvent } = useSSE(
    '/notifications/admin/events/stream',
    {
      autoConnect: options.autoConnect ?? false,
      eventHandlers: {
        feedback: (data) => {
          feedbacks.value.unshift(data)
          // Garder les 50 derniers
          if (feedbacks.value.length > 50) {
            feedbacks.value = feedbacks.value.slice(0, 50)
          }
          if (options.onFeedback) {
            options.onFeedback(data)
          }
        },
        document_status: (data) => {
          const index = documents.value.findIndex(d => d.document_id === data.document_id)
          if (index !== -1) {
            documents.value[index] = data
          } else {
            documents.value.unshift(data)
          }
          if (options.onDocumentStatus) {
            options.onDocumentStatus(data)
          }
        },
        notification: (data) => {
          if (options.onNotification) {
            options.onNotification(data)
          }
        }
      }
    }
  )
  
  return {
    feedbacks,
    documents,
    connected,
    lastEvent,
    connect,
    disconnect
  }
}

/**
 * Composable pour les stats dashboard en temps réel
 * 
 * @example
 * const { stats, connect } = useDashboardStatsSSE()
 */
export function useDashboardStatsSSE(options = {}) {
  const stats = ref(null)
  const lastUpdate = ref(null)
  
  const { connected, connect, disconnect, lastEvent } = useSSE(
    '/notifications/dashboard/stream',
    {
      autoConnect: options.autoConnect ?? false,
      eventHandlers: {
        dashboard_update: (data) => {
          stats.value = data
          lastUpdate.value = new Date()
          if (options.onUpdate) {
            options.onUpdate(data)
          }
        }
      }
    }
  )
  
  return {
    stats,
    lastUpdate,
    connected,
    lastEvent,
    connect,
    disconnect
  }
}

export default useSSE