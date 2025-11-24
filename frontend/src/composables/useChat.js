/**
 * Composable pour la gestion du chat avec streaming SSE.
 * 
 * Fournit une interface haut niveau pour :
 * - Envoyer des messages avec streaming SSE
 * - Gérer l'état du streaming (typing indicator)
 * - Annuler une génération en cours
 * - Formatter les messages pour l'affichage
 * 
 * Sprint 8 - Phase 1 : Stores & Composables
 * 
 * Utilise le store chat.js et le composable useSSE.js
 */
import { ref, computed, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSSE } from '@/composables/useSSE'

/**
 * Configuration par défaut pour le chat.
 */
const DEFAULT_CONFIG = {
  maxMessageLength: 10000,
  typingDelay: 30,  // ms entre chaque caractère pour l'effet typing
  streamingEndpoint: '/api/v1/chat/stream'
}

/**
 * Composable pour gérer le chat et le streaming.
 * 
 * @param {Object} options - Options de configuration
 * @returns {Object} API du composable
 */
export function useChat(options = {}) {
  const config = { ...DEFAULT_CONFIG, ...options }
  
  // Stores et composables
  const chatStore = useChatStore()
  const { connectSSEPost, closeSSE, isConnected, error: sseError } = useSSE()
  
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  /**
   * Message en cours de saisie
   */
  const inputMessage = ref('')
  
  /**
   * Indique si un message est en cours d'envoi
   */
  const isSending = ref(false)
  
  /**
   * Indique si une réponse est en cours de streaming
   */
  const isStreaming = ref(false)
  
  /**
   * Contenu streamé en cours d'affichage
   */
  const streamedContent = ref('')
  
  /**
   * Sources de la réponse streamée
   */
  const streamedSources = ref([])
  
  /**
   * Métadonnées de la dernière réponse
   */
  const lastResponseMetadata = ref(null)
  
  /**
   * Erreur du dernier envoi
   */
  const sendError = ref(null)
  
  /**
   * AbortController pour annuler le streaming
   */
  let abortController = null
  
  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /**
   * Indique si un message peut être envoyé
   */
  const canSend = computed(() => {
    return inputMessage.value.trim().length > 0 &&
           inputMessage.value.length <= config.maxMessageLength &&
           !isSending.value &&
           !isStreaming.value
  })
  
  /**
   * Nombre de caractères restants
   */
  const remainingChars = computed(() => {
    return config.maxMessageLength - inputMessage.value.length
  })
  
  /**
   * Indique si le message est trop long
   */
  const isTooLong = computed(() => {
    return inputMessage.value.length > config.maxMessageLength
  })
  
  /**
   * Indique si une génération peut être annulée
   */
  const canCancel = computed(() => {
    return isStreaming.value
  })
  
  /**
   * Messages de la conversation courante (depuis le store)
   */
  const messages = computed(() => chatStore.sortedMessages)
  
  /**
   * Conversation courante (depuis le store)
   */
  const currentConversation = computed(() => chatStore.currentConversation)
  
  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /**
   * Envoyer un message.
   * 
   * @param {string} message - Message à envoyer (optionnel, utilise inputMessage si non fourni)
   * @param {string|null} conversationId - ID de la conversation (optionnel)
   * @returns {Promise<Object|null>} Résultat de l'envoi
   */
  async function sendMessage(message = null, conversationId = null) {
    const messageToSend = message || inputMessage.value
    
    if (!messageToSend?.trim() || isSending.value || isStreaming.value) {
      return null
    }
    
    if (messageToSend.length > config.maxMessageLength) {
      sendError.value = {
        type: 'validation',
        message: `Le message ne doit pas dépasser ${config.maxMessageLength} caractères`
      }
      return null
    }
    
    isSending.value = true
    isStreaming.value = true
    streamedContent.value = ''
    streamedSources.value = []
    lastResponseMetadata.value = null
    sendError.value = null
    
    // Vider l'input
    const originalInput = inputMessage.value
    inputMessage.value = ''
    
    try {
      // Déléguer au store
      const result = await chatStore.sendMessage(
        messageToSend,
        conversationId || currentConversation.value?.id
      )
      
      if (result) {
        streamedContent.value = chatStore.streamingContent
        streamedSources.value = chatStore.streamingSources
      }
      
      return result
      
    } catch (error) {
      console.error('❌ Erreur envoi message:', error)
      
      sendError.value = {
        type: 'network',
        message: error.message || 'Erreur lors de l\'envoi du message'
      }
      
      // Restaurer l'input en cas d'erreur
      inputMessage.value = originalInput
      
      return null
    } finally {
      isSending.value = false
      isStreaming.value = false
    }
  }
  
  /**
   * Annuler le streaming en cours.
   */
  function cancelStreaming() {
    chatStore.cancelStreaming()
    closeSSE()
    
    isSending.value = false
    isStreaming.value = false
    
    console.log('⚠️ Streaming annulé')
  }
  
  /**
   * Créer une nouvelle conversation.
   */
  function newConversation() {
    chatStore.createConversation()
    inputMessage.value = ''
    streamedContent.value = ''
    streamedSources.value = []
    lastResponseMetadata.value = null
    sendError.value = null
    
    console.log('✅ Nouvelle conversation')
  }
  
  /**
   * Charger une conversation existante.
   * 
   * @param {string} conversationId - ID de la conversation
   * @returns {Promise<Object|null>} Conversation chargée
   */
  async function loadConversation(conversationId) {
    inputMessage.value = ''
    streamedContent.value = ''
    streamedSources.value = []
    sendError.value = null
    
    return chatStore.fetchConversation(conversationId)
  }
  
  /**
   * Supprimer la conversation courante.
   * 
   * @returns {Promise<boolean>} Succès de la suppression
   */
  async function deleteCurrentConversation() {
    const convId = currentConversation.value?.id
    
    if (!convId) return false
    
    const success = await chatStore.deleteConversation(convId)
    
    if (success) {
      newConversation()
    }
    
    return success
  }
  
  /**
   * Ajouter un feedback sur un message.
   * 
   * @param {string} messageId - ID du message
   * @param {string} rating - 'thumbs_up' ou 'thumbs_down'
   * @param {string|null} comment - Commentaire optionnel
   * @returns {Promise<boolean>} Succès
   */
  async function addFeedback(messageId, rating, comment = null) {
    return chatStore.addFeedback(messageId, rating, comment)
  }
  
  /**
   * Formater un message pour l'affichage.
   * 
   * @param {Object} message - Message à formater
   * @returns {Object} Message formaté
   */
  function formatMessage(message) {
    return {
      ...message,
      formattedTime: formatMessageTime(message.created_at),
      isUser: message.role === 'user',
      isAssistant: message.role === 'assistant',
      hasSources: message.sources?.length > 0,
      hasFeedback: !!message.feedback
    }
  }
  
  /**
   * Formater l'heure d'un message.
   * 
   * @param {string} dateString - Date ISO
   * @returns {string} Heure formatée
   */
  function formatMessageTime(dateString) {
    if (!dateString) return ''
    
    const date = new Date(dateString)
    const now = new Date()
    const diff = now - date
    
    // Moins de 24h : afficher l'heure
    if (diff < 24 * 60 * 60 * 1000) {
      return date.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    
    // Moins d'une semaine : afficher le jour et l'heure
    if (diff < 7 * 24 * 60 * 60 * 1000) {
      return date.toLocaleDateString('fr-FR', {
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    
    // Plus d'une semaine : afficher la date complète
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  /**
   * Copier un message dans le presse-papier.
   * 
   * @param {string} content - Contenu à copier
   * @returns {Promise<boolean>} Succès
   */
  async function copyToClipboard(content) {
    try {
      await navigator.clipboard.writeText(content)
      console.log('✅ Contenu copié')
      return true
    } catch (error) {
      console.error('❌ Erreur copie:', error)
      return false
    }
  }
  
  /**
   * Régénérer la dernière réponse.
   * 
   * @returns {Promise<Object|null>} Résultat de la régénération
   */
  async function regenerateLastResponse() {
    // Trouver le dernier message utilisateur
    const userMessages = messages.value.filter(m => m.role === 'user')
    const lastUserMessage = userMessages[userMessages.length - 1]
    
    if (!lastUserMessage) {
      console.warn('⚠️ Aucun message utilisateur à régénérer')
      return null
    }
    
    // Supprimer le dernier message assistant
    const lastAssistant = chatStore.lastAssistantMessage
    if (lastAssistant) {
      // Note: On pourrait implémenter la suppression côté backend
      console.log('🔄 Régénération de la réponse...')
    }
    
    // Renvoyer le même message
    return sendMessage(lastUserMessage.content)
  }
  
  // ===========================================================================
  // WATCHERS
  // ===========================================================================
  
  // Synchroniser l'état de streaming avec le store
  watch(() => chatStore.isStreaming, (newValue) => {
    isStreaming.value = newValue
  })
  
  watch(() => chatStore.isSending, (newValue) => {
    isSending.value = newValue
  })
  
  watch(() => chatStore.streamingContent, (newValue) => {
    streamedContent.value = newValue
  })
  
  watch(() => chatStore.streamingSources, (newValue) => {
    streamedSources.value = newValue
  })
  
  // ===========================================================================
  // RETURN
  // ===========================================================================
  
  return {
    // State
    inputMessage,
    isSending,
    isStreaming,
    streamedContent,
    streamedSources,
    lastResponseMetadata,
    sendError,
    
    // Getters
    canSend,
    remainingChars,
    isTooLong,
    canCancel,
    messages,
    currentConversation,
    
    // Actions
    sendMessage,
    cancelStreaming,
    newConversation,
    loadConversation,
    deleteCurrentConversation,
    addFeedback,
    formatMessage,
    formatMessageTime,
    copyToClipboard,
    regenerateLastResponse,
    
    // Config
    maxMessageLength: config.maxMessageLength
  }
}

export default useChat