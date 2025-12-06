// ==============================================================================
// STORE NOTIFICATIONS - SPRINT 14
// ==============================================================================
// Gestion centralisée des notifications avec Pinia
// ==============================================================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElNotification } from 'element-plus'
import { notificationsService } from '../services/api/notifications'

/**
 * Types de notifications
 */
export const NotificationType = {
  DOCUMENT_UPLOADED: 'DOCUMENT_UPLOADED',
  DOCUMENT_PROCESSING: 'DOCUMENT_PROCESSING',
  DOCUMENT_COMPLETED: 'DOCUMENT_COMPLETED',
  DOCUMENT_FAILED: 'DOCUMENT_FAILED',
  FEEDBACK_RECEIVED: 'FEEDBACK_RECEIVED',
  FEEDBACK_NEGATIVE: 'FEEDBACK_NEGATIVE',
  USER_CREATED: 'USER_CREATED',
  USER_UPDATED: 'USER_UPDATED',
  USER_DELETED: 'USER_DELETED',
  USER_ACTIVATED: 'USER_ACTIVATED',
  USER_DEACTIVATED: 'USER_DEACTIVATED',
  USER_PASSWORD_RESET: 'USER_PASSWORD_RESET',
  SYSTEM_INFO: 'SYSTEM_INFO',
  SYSTEM_WARNING: 'SYSTEM_WARNING',
  SYSTEM_ERROR: 'SYSTEM_ERROR',
  STATS_UPDATE: 'STATS_UPDATE'
}

/**
 * Priorités des notifications
 */
export const NotificationPriority = {
  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
  URGENT: 'URGENT'
}

/**
 * Configuration des icônes par type
 */
const iconMap = {
  [NotificationType.DOCUMENT_UPLOADED]: 'Upload',
  [NotificationType.DOCUMENT_PROCESSING]: 'Loading',
  [NotificationType.DOCUMENT_COMPLETED]: 'SuccessFilled',
  [NotificationType.DOCUMENT_FAILED]: 'CircleCloseFilled',
  [NotificationType.FEEDBACK_RECEIVED]: 'ChatLineSquare',
  [NotificationType.FEEDBACK_NEGATIVE]: 'WarningFilled',
  [NotificationType.USER_CREATED]: 'UserFilled',
  [NotificationType.USER_UPDATED]: 'Edit',
  [NotificationType.USER_DELETED]: 'Delete',
  [NotificationType.USER_ACTIVATED]: 'CircleCheckFilled',
  [NotificationType.USER_DEACTIVATED]: 'CircleCloseFilled',
  [NotificationType.USER_PASSWORD_RESET]: 'Lock',
  [NotificationType.SYSTEM_INFO]: 'InfoFilled',
  [NotificationType.SYSTEM_WARNING]: 'WarningFilled',
  [NotificationType.SYSTEM_ERROR]: 'CircleCloseFilled',
  [NotificationType.STATS_UPDATE]: 'TrendCharts'
}

/**
 * Configuration des couleurs par type/priorité
 */
const colorMap = {
  [NotificationType.DOCUMENT_COMPLETED]: '#10b981',
  [NotificationType.DOCUMENT_FAILED]: '#ef4444',
  [NotificationType.FEEDBACK_NEGATIVE]: '#f59e0b',
  [NotificationType.USER_CREATED]: '#10b981',
  [NotificationType.USER_ACTIVATED]: '#10b981',
  [NotificationType.USER_DELETED]: '#ef4444',
  [NotificationType.USER_DEACTIVATED]: '#f59e0b',
  [NotificationType.SYSTEM_ERROR]: '#ef4444',
  [NotificationType.SYSTEM_WARNING]: '#f59e0b',
  default: '#3b82f6'
}

const priorityColorMap = {
  [NotificationPriority.URGENT]: '#ef4444',
  [NotificationPriority.HIGH]: '#f59e0b'
}

/**
 * Store Pinia pour les notifications
 */
export const useNotificationStore = defineStore('notifications', () => {
  // ==========================================================================
  // STATE
  // ==========================================================================
  
  /** Liste des notifications */
  const notifications = ref([])
  
  /** Nombre total de notifications */
  const total = ref(0)
  
  /** Nombre de notifications non lues */
  const unreadCount = ref(0)
  
  /** Pagination */
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  
  /** État de chargement */
  const loading = ref(false)
  
  /** Connexion SSE active */
  const sseConnected = ref(false)
  
  /** EventSource pour SSE */
  let eventSource = null
  
  /** Paramètres de notification */
  const settings = ref({
    soundEnabled: true,
    showPopups: true,
    popupDuration: 5000
  })
  
  // ==========================================================================
  // GETTERS (computed)
  // ==========================================================================
  
  /** Notifications triées par date (plus récentes en premier) */
  const sortedNotifications = computed(() => {
    return [...notifications.value].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    )
  })
  
  /** Notifications non lues */
  const unreadNotifications = computed(() => {
    return notifications.value.filter(n => !n.is_read)
  })
  
  /** A des notifications non lues */
  const hasUnread = computed(() => unreadCount.value > 0)
  
  /** Notifications par type */
  const notificationsByType = computed(() => {
    const grouped = {}
    for (const notif of notifications.value) {
      if (!grouped[notif.type]) {
        grouped[notif.type] = []
      }
      grouped[notif.type].push(notif)
    }
    return grouped
  })
  
  /** 5 dernières notifications pour le badge */
  const recentNotifications = computed(() => {
    return sortedNotifications.value.slice(0, 5)
  })
  
  // ==========================================================================
  // ACTIONS - API CALLS
  // ==========================================================================
  
  /**
   * Charger les notifications depuis l'API
   */
  async function fetchNotifications(options = {}) {
    loading.value = true
    
    try {
      const params = {
        skip: ((options.page || page.value) - 1) * (options.pageSize || pageSize.value),
        limit: options.pageSize || pageSize.value,
        unread_only: options.unreadOnly || false
      }
      
      const data = await notificationsService.getNotifications(params)
      
      notifications.value = data.items || data.notifications || []
      total.value = data.total || 0
      unreadCount.value = data.unread_count || 0
      page.value = data.page || 1
      pageSize.value = data.page_size || 20
      totalPages.value = data.total_pages || Math.ceil(total.value / pageSize.value)
      
      return data
    } catch (error) {
      console.error('Erreur chargement notifications:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Charger uniquement le compteur de non lus
   */
  async function fetchUnreadCount() {
    try {
      const data = await notificationsService.getUnreadCount()
      unreadCount.value = data.count || data.unread_count || 0
      return unreadCount.value
    } catch (error) {
      console.error('Erreur chargement compteur:', error)
      return 0
    }
  }
  
  /**
   * Marquer une notification comme lue
   */
  async function markAsRead(notificationId) {
    try {
      const updated = await notificationsService.markAsRead(notificationId)
      
      // Mettre à jour localement
      const index = notifications.value.findIndex(n => n.id === notificationId)
      if (index !== -1) {
        notifications.value[index] = updated
      }
      
      // Décrémenter le compteur
      if (unreadCount.value > 0) {
        unreadCount.value--
      }
      
      return updated
    } catch (error) {
      console.error('Erreur marquage notification:', error)
      throw error
    }
  }
  
  /**
   * Marquer toutes les notifications comme lues
   */
  async function markAllAsRead() {
    try {
      const result = await notificationsService.markAllAsRead()
      
      // Mettre à jour localement
      notifications.value = notifications.value.map(n => ({
        ...n,
        is_read: true,
        read_at: new Date().toISOString()
      }))
      
      unreadCount.value = 0
      
      return result
    } catch (error) {
      console.error('Erreur marquage toutes notifications:', error)
      throw error
    }
  }
  
  /**
   * Rejeter une notification
   */
  async function dismissNotification(notificationId) {
    try {
      await notificationsService.dismiss(notificationId)
      
      // Supprimer localement
      const notif = notifications.value.find(n => n.id === notificationId)
      notifications.value = notifications.value.filter(n => n.id !== notificationId)
      
      // Décrémenter les compteurs
      if (total.value > 0) {
        total.value--
      }
      if (notif && !notif.is_read && unreadCount.value > 0) {
        unreadCount.value--
      }
      
    } catch (error) {
      console.error('Erreur rejet notification:', error)
      throw error
    }
  }
  
  /**
   * Rejeter toutes les notifications
   */
  async function dismissAll() {
    try {
      const result = await notificationsService.dismissAll()
      
      // Vider la liste localement
      notifications.value = []
      total.value = 0
      unreadCount.value = 0
      
      return result
    } catch (error) {
      console.error('Erreur rejet toutes notifications:', error)
      throw error
    }
  }
  
  /**
   * Supprimer toutes les notifications lues
   */
  async function deleteAllRead() {
    try {
      const result = await notificationsService.deleteAllRead()
      
      // Garder uniquement les non lues localement
      notifications.value = notifications.value.filter(n => !n.is_read)
      total.value = notifications.value.length
      
      return result
    } catch (error) {
      console.error('Erreur suppression notifications lues:', error)
      throw error
    }
  }
  
  // ==========================================================================
  // ACTIONS - SSE
  // ==========================================================================
  
  // Variable pour le polling interval
  let pollingInterval = null
  
  /**
   * Connecter au stream SSE des notifications
   */
  function connectSSE() {
    // Fermer la connexion existante
    if (eventSource) {
      eventSource.close()
    }
    
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.warn('SSE: Pas de token, connexion impossible')
      return
    }
    
    // Construire l'URL SSE correctement
    // VITE_API_URL contient déjà /api/v1, donc on ajoute juste /notifications/stream
    const baseUrl = import.meta.env.VITE_API_URL || '/api/v1'
    const url = `${baseUrl}/notifications/stream?token=${token}`
    
    console.log('SSE Notifications: Connexion à', url)
    eventSource = new EventSource(url)
    
    // DEBUG: Log tous les messages bruts
    eventSource.onmessage = (event) => {
      console.log('SSE: Message brut reçu:', event.data)
    }
    
    // Événement de connexion
    eventSource.addEventListener('connected', (event) => {
      sseConnected.value = true
      console.log('SSE Notifications: Connecté', event.data)
      
      try {
        const data = JSON.parse(event.data)
        // NE PAS écraser unreadCount ici car fetchNotifications le fait déjà
        // Cela évite une race condition entre les deux appels
        // On met à jour seulement si unreadCount est encore à 0 (pas encore initialisé)
        if (unreadCount.value === 0 && data.unread_count > 0) {
          unreadCount.value = data.unread_count
          console.log('SSE: unreadCount initialisé depuis connected:', unreadCount.value)
        } else {
          console.log('SSE: unreadCount déjà initialisé:', unreadCount.value, '(SSE:', data.unread_count, ')')
        }
      } catch (e) {
        console.error('SSE: Erreur parsing connected:', e)
      }
    })
    
    // Nouvelle notification
    eventSource.addEventListener('notification', (event) => {
      console.log('SSE: Événement notification reçu !', event.data)
      try {
        const notification = JSON.parse(event.data)
        console.log('SSE: Notification parsée:', notification)
        handleNewNotification(notification)
      } catch (e) {
        console.error('SSE: Erreur parsing notification:', e)
      }
    })
    
    // Heartbeat (maintien connexion)
    eventSource.addEventListener('heartbeat', (event) => {
      console.log('SSE: Heartbeat reçu')
    })
    
    // Gestion des erreurs
    eventSource.onerror = (error) => {
      console.error('SSE Notifications: Erreur', error)
      console.log('SSE: readyState =', eventSource.readyState)
      sseConnected.value = false
      
      // Reconnexion automatique après 5 secondes
      setTimeout(() => {
        if (!sseConnected.value) {
          console.log('SSE Notifications: Tentative de reconnexion...')
          connectSSE()
        }
      }, 5000)
    }
    
    // Log l'état de la connexion
    eventSource.onopen = () => {
      console.log('SSE: Connexion ouverte, readyState =', eventSource.readyState)
    }
    
    // Démarrer le polling pour les notifications des workers Celery
    // (qui ne peuvent pas broadcaster via SSE)
    startPolling()
  }
  
  /**
   * Démarrer le polling périodique pour les nouvelles notifications
   * Nécessaire car les workers Celery ne peuvent pas broadcaster via SSE
   */
  function startPolling() {
    stopPolling() // Arrêter l'ancien polling s'il existe
    
    // Polling toutes les 10 secondes
    pollingInterval = setInterval(async () => {
      try {
        // Récupérer le nombre de non-lues depuis l'API
        const countResult = await notificationsService.getUnreadCount()
        const newUnreadCount = countResult.unread_count || countResult.count || 0
        
        console.log(`📊 Polling: unreadCount actuel=${unreadCount.value}, nouveau=${newUnreadCount}`)
        
        // Si le nombre a augmenté, recharger les notifications et afficher les nouvelles
        if (newUnreadCount > unreadCount.value) {
          const diff = newUnreadCount - unreadCount.value
          console.log(`📬 Polling: ${diff} nouvelle(s) notification(s) détectée(s)`)
          
          // Sauvegarder les IDs existants
          const existingIds = new Set(notifications.value.map(n => n.id))
          
          // Recharger les notifications
          await fetchNotifications()
          
          // Identifier les nouvelles notifications et afficher les popups
          const newNotifications = notifications.value.filter(n => !existingIds.has(n.id))
          for (const newNotif of newNotifications) {
            // Afficher popup et jouer son pour chaque nouvelle notification
            if (settings.value.showPopups) {
              showNotificationPopup(newNotif)
            }
            if (settings.value.soundEnabled) {
              playNotificationSound(newNotif.priority)
            }
          }
        }
        
        // Toujours mettre à jour le compteur (même s'il a diminué)
        unreadCount.value = newUnreadCount
      } catch (error) {
        console.error('Polling: Erreur récupération notifications:', error)
      }
    }, 10000) // 10 secondes
    
    console.log('📊 Polling notifications démarré (10s)')
  }
  
  /**
   * Arrêter le polling
   */
  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
      console.log('📊 Polling notifications arrêté')
    }
  }
  
  /**
   * Déconnecter du stream SSE
   */
  function disconnectSSE() {
    // Arrêter le polling
    stopPolling()
    
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    sseConnected.value = false
    console.log('SSE Notifications: Déconnecté')
  }
  
  /**
   * Gérer l'arrivée d'une nouvelle notification
   */
  function handleNewNotification(notification) {
    console.log('handleNewNotification appelée avec:', notification)
    
    // Ajouter en début de liste
    notifications.value.unshift(notification)
    console.log('Notifications après ajout:', notifications.value.length)
    
    // Incrémenter les compteurs
    if (!notification.is_read) {
      unreadCount.value++
      console.log('unreadCount incrémenté:', unreadCount.value)
    }
    total.value++
    
    // Afficher popup si activé
    if (settings.value.showPopups) {
      console.log('Affichage popup notification')
      showNotificationPopup(notification)
    } else {
      console.log('Popups désactivés')
    }
    
    // Jouer son si activé
    if (settings.value.soundEnabled) {
      playNotificationSound(notification.priority)
    }
  }
  
  /**
   * Afficher un popup Element Plus pour la notification
   */
  function showNotificationPopup(notification) {
    const typeMap = {
      [NotificationType.DOCUMENT_COMPLETED]: 'success',
      [NotificationType.DOCUMENT_FAILED]: 'error',
      [NotificationType.USER_CREATED]: 'success',
      [NotificationType.USER_ACTIVATED]: 'success',
      [NotificationType.USER_DELETED]: 'warning',
      [NotificationType.USER_DEACTIVATED]: 'warning',
      [NotificationType.SYSTEM_ERROR]: 'error',
      [NotificationType.SYSTEM_WARNING]: 'warning',
      [NotificationType.FEEDBACK_NEGATIVE]: 'warning'
    }
    
    const type = typeMap[notification.type] || 'info'
    
    ElNotification({
      title: notification.title,
      message: notification.message || '',
      type: type,
      duration: settings.value.popupDuration,
      position: 'top-right',
      onClick: () => {
        // Marquer comme lu au clic
        markAsRead(notification.id)
      }
    })
  }
  
  /**
   * Jouer un son de notification
   */
  function playNotificationSound(priority) {
    try {
      // Utiliser l'API Audio Web
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      // Fréquence selon la priorité
      const frequencies = {
        [NotificationPriority.URGENT]: 880,
        [NotificationPriority.HIGH]: 660,
        [NotificationPriority.MEDIUM]: 440,
        [NotificationPriority.LOW]: 330
      }
      
      oscillator.frequency.value = frequencies[priority] || 440
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.3)
    } catch (e) {
      // Ignorer les erreurs audio
    }
  }
  
  // ==========================================================================
  // ACTIONS - UTILITAIRES
  // ==========================================================================
  
  /**
   * Ajouter une notification locale (sans API)
   */
  function addLocalNotification(notification) {
    const newNotif = {
      id: `local-${Date.now()}`,
      type: notification.type || NotificationType.SYSTEM_INFO,
      priority: notification.priority || NotificationPriority.MEDIUM,
      title: notification.title,
      message: notification.message,
      data: notification.data || {},
      is_read: false,
      is_dismissed: false,
      created_at: new Date().toISOString(),
      icon: iconMap[notification.type] || 'Bell',
      color: getNotificationColor(notification)
    }
    
    handleNewNotification(newNotif)
    return newNotif
  }
  
  /**
   * Obtenir la couleur d'une notification
   */
  function getNotificationColor(notification) {
    // Priorité d'abord
    if (priorityColorMap[notification.priority]) {
      return priorityColorMap[notification.priority]
    }
    // Puis type
    return colorMap[notification.type] || colorMap.default
  }
  
  /**
   * Obtenir l'icône d'une notification
   */
  function getNotificationIcon(type) {
    return iconMap[type] || 'Bell'
  }
  
  /**
   * Formater le temps relatif
   */
  function formatRelativeTime(dateString) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffSeconds < 60) {
      return 'À l\'instant'
    } else if (diffMinutes < 60) {
      return `Il y a ${diffMinutes} min`
    } else if (diffHours < 24) {
      return `Il y a ${diffHours}h`
    } else if (diffDays < 7) {
      return `Il y a ${diffDays}j`
    } else {
      return date.toLocaleDateString('fr-FR')
    }
  }
  
  /**
   * Mettre à jour les paramètres
   */
  function updateSettings(newSettings) {
    settings.value = { ...settings.value, ...newSettings }
    // Sauvegarder en localStorage
    localStorage.setItem('notification_settings', JSON.stringify(settings.value))
  }
  
  /**
   * Charger les paramètres depuis localStorage
   */
  function loadSettings() {
    const saved = localStorage.getItem('notification_settings')
    if (saved) {
      try {
        settings.value = { ...settings.value, ...JSON.parse(saved) }
      } catch (e) {
        // Ignorer
      }
    }
  }
  
  /**
   * Réinitialiser le store
   */
  function reset() {
    disconnectSSE()
    notifications.value = []
    total.value = 0
    unreadCount.value = 0
    page.value = 1
  }
  
  // ==========================================================================
  // INITIALISATION
  // ==========================================================================
  
  // Charger les paramètres au démarrage
  loadSettings()
  
  // ==========================================================================
  // EXPORTS
  // ==========================================================================
  
  return {
    // State
    notifications,
    total,
    unreadCount,
    page,
    pageSize,
    totalPages,
    loading,
    sseConnected,
    settings,
    
    // Getters
    sortedNotifications,
    unreadNotifications,
    hasUnread,
    notificationsByType,
    recentNotifications,
    
    // Actions
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    dismissAll,
    deleteAllRead,
    connectSSE,
    disconnectSSE,
    addLocalNotification,
    getNotificationColor,
    getNotificationIcon,
    formatRelativeTime,
    updateSettings,
    reset
  }
})

export default useNotificationStore