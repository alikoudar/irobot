/**
 * Store Pinia pour la gestion du chat - VERSION SIMPLIFIÉE SANS STREAMING
 * 
 * Gère :
 * - Liste des conversations de l'utilisateur
 * - Conversation courante et ses messages
 * - Envoi de messages SANS streaming (endpoint /chat au lieu de /chat/stream)
 * - Feedbacks sur les messages
 * - Archivage et suppression de conversations
 * 
 * AVANTAGES DE CETTE VERSION :
 * - ✅ Plus de problème d'IDs temporaires
 * - ✅ UUIDs réels dès la réception
 * - ✅ Code 10x plus simple
 * - ✅ Boutons feedback fonctionnent immédiatement
 * - ✅ Pas de gestion SSE complexe
 * 
 * Sprint 9 - Correction: Utilisation endpoint non-streaming
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api/auth'
import { ElMessage } from 'element-plus'

const api = apiClient

export const useChatStore = defineStore('chat', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  // Conversations
  const conversations = ref([])
  const currentConversation = ref(null)
  const messages = ref([])
  
  // Pagination conversations
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const totalPages = ref(1)
  
  // Filtres
  const filters = ref({
    search: '',
    include_archived: false
  })
  
  // Loading states
  const isLoading = ref(false)
  const isLoadingMessages = ref(false)
  const isSending = ref(false)
  const isGenerating = ref(false)  // Nouveau: pendant génération backend
  
  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /**
   * Conversations non archivées triées par date
   */
  const activeConversations = computed(() => {
    return conversations.value
      .filter(c => !c.is_archived)
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
  })
  
  /**
   * Conversations archivées
   */
  const archivedConversations = computed(() => {
    return conversations.value.filter(c => c.is_archived)
  })
  
  /**
   * Indique si une conversation est en cours
   */
  const hasCurrentConversation = computed(() => !!currentConversation.value)
  
  /**
   * Messages triés chronologiquement
   */
  const sortedMessages = computed(() => {
    return [...messages.value].sort(
      (a, b) => new Date(a.created_at) - new Date(b.created_at)
    )
  })
  
  /**
   * Dernier message de l'assistant
   */
  const lastAssistantMessage = computed(() => {
    return [...messages.value]
      .filter(m => m.role?.toUpperCase() === 'ASSISTANT')
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]
  })
  
  /**
   * Indique si on peut envoyer un message
   */
  const canSendMessage = computed(() => {
    return !isSending.value && !isGenerating.value
  })
  
  // ===========================================================================
  // ACTIONS - CONVERSATIONS
  // ===========================================================================
  
  /**
   * Récupérer la liste des conversations
   */
  async function fetchConversations(options = {}) {
    isLoading.value = true
    
    try {
      const params = {
        page: options.page || page.value,
        page_size: options.page_size || pageSize.value,
        include_archived: options.include_archived ?? filters.value.include_archived
      }
      
      if (filters.value.search) {
        params.search = filters.value.search
      }
      
      const response = await api.get('/chat/conversations', { params })
      const data = response.data
      
      conversations.value = data.items || data.conversations || []
      total.value = data.total || 0
      totalPages.value = data.total_pages || 1
      page.value = data.page || 1
      
      console.log('✅ Conversations chargées:', conversations.value.length)
      return conversations.value
      
    } catch (error) {
      console.error('❌ Erreur chargement conversations:', error)
      ElMessage.error('Erreur lors du chargement des conversations')
      return []
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Récupérer une conversation avec ses messages
   */
  async function fetchConversation(conversationId) {
    if (!conversationId) return null
    
    isLoadingMessages.value = true
    
    try {
      const response = await api.get(`/chat/conversations/${conversationId}`)
      const data = response.data
      
      currentConversation.value = data
      messages.value = data.messages || []
      
      console.log('✅ Conversation chargée:', data.title)
      console.log('✅ Messages:', messages.value.length)
      
      return data
      
    } catch (error) {
      console.error('❌ Erreur chargement conversation:', error)
      
      if (error.response?.status === 404) {
        ElMessage.warning('Conversation non trouvée')
      } else {
        ElMessage.error('Erreur lors du chargement de la conversation')
      }
      
      return null
    } finally {
      isLoadingMessages.value = false
    }
  }
  
  /**
   * Créer une nouvelle conversation
   */
  function createConversation() {
    currentConversation.value = null
    messages.value = []
    
    console.log('✅ Nouvelle conversation initialisée')
  }
  
  /**
   * Sélectionner une conversation
   */
  async function selectConversation(conversationId) {
    return fetchConversation(conversationId)
  }
  
  /**
   * Supprimer une conversation
   */
  async function deleteConversation(conversationId) {
    try {
      await api.delete(`/chat/conversations/${conversationId}`)
      
      conversations.value = conversations.value.filter(c => c.id !== conversationId)
      
      if (currentConversation.value?.id === conversationId) {
        createConversation()
      }
      
      total.value = Math.max(0, total.value - 1)
      
      ElMessage.success('Conversation supprimée')
      console.log('✅ Conversation supprimée:', conversationId)
      
      return true
      
    } catch (error) {
      console.error('❌ Erreur suppression conversation:', error)
      ElMessage.error('Erreur lors de la suppression')
      return false
    }
  }
  
  /**
   * Archiver ou désarchiver une conversation
   */
  async function archiveConversation(conversationId, archive = true) {
    try {
      await api.put(`/chat/conversations/${conversationId}/archive`, {
        is_archived: archive
      })
      
      const conversation = conversations.value.find(c => c.id === conversationId)
      if (conversation) {
        conversation.is_archived = archive
      }
      
      if (currentConversation.value?.id === conversationId) {
        currentConversation.value.is_archived = archive
      }
      
      ElMessage.success(archive ? 'Conversation archivée' : 'Conversation désarchivée')
      
      return true
      
    } catch (error) {
      console.error('❌ Erreur archivage:', error)
      ElMessage.error('Erreur lors de l\'archivage')
      return false
    }
  }
  
  /**
   * Mettre à jour le titre
   */
  async function updateConversationTitle(conversationId, title) {
    try {
      await api.patch(`/chat/conversations/${conversationId}`, { title })
      
      const conversation = conversations.value.find(c => c.id === conversationId)
      if (conversation) {
        conversation.title = title
      }
      
      if (currentConversation.value?.id === conversationId) {
        currentConversation.value.title = title
      }
      
      console.log('✅ Titre mis à jour:', title)
      return true
      
    } catch (error) {
      console.error('❌ Erreur mise à jour titre:', error)
      ElMessage.error('Erreur lors de la mise à jour du titre')
      return false
    }
  }
  
  async function updateConversation(conversationId, data) {
    if (data.title) {
      return updateConversationTitle(conversationId, data.title)
    }
    return false
  }
  
  // ===========================================================================
  // ACTIONS - MESSAGES (VERSION SIMPLIFIÉE SANS STREAMING)
  // ===========================================================================
  
  /**
   * Envoyer un message et recevoir la réponse COMPLÈTE (sans streaming)
   * 
   * NOUVEAU : Utilise /api/v1/chat au lieu de /api/v1/chat/stream
   * 
   * AVANTAGES :
   * - Plus d'IDs temporaires
   * - UUIDs réels dès la réponse
   * - Code 10x plus simple
   * - Boutons feedback fonctionnent immédiatement
   * 
   * @param {string} messageContent - Contenu du message
   * @param {string|null} conversationId - ID de la conversation
   * @returns {Promise<Object|null>} Résultat
   */
  async function sendMessage(messageContent, conversationId = null) {
    if (!messageContent?.trim() || isSending.value || isGenerating.value) {
      return null
    }
    
    isSending.value = true
    isGenerating.value = true
    
    const convId = conversationId || currentConversation.value?.id
    
    try {
      console.log('📤 Envoi message:', messageContent.substring(0, 50))
      
      // Appel API simple (NON-STREAMING)
      const response = await api.post('/chat', {
        message: messageContent,
        conversation_id: convId,
        stream: false  // Explicite: pas de streaming
      })
      
      const data = response.data
      
      console.log('✅ Réponse reçue:', {
        conversation_id: data.conversation_id,
        message_id: data.message_id,
        content_length: data.content?.length
      })
      
      // Mettre à jour la conversation courante
      if (data.conversation_id) {
        if (!currentConversation.value || currentConversation.value.id !== data.conversation_id) {
          currentConversation.value = {
            id: data.conversation_id,
            title: 'Nouvelle conversation',
            is_archived: false
          }
        }
      }
      
      // Recharger les messages de la conversation
      // (le backend a créé les 2 messages: USER + ASSISTANT)
      if (data.conversation_id) {
        await fetchConversation(data.conversation_id)
      }
      
      // Recharger la liste des conversations si nouvelle
      if (!convId) {
        await fetchConversations()
      }
      
      return {
        success: true,
        conversation_id: data.conversation_id,
        message_id: data.message_id
      }
      
    } catch (error) {
      console.error('❌ Erreur envoi message:', error)
      
      let errorMessage = 'Erreur lors de l\'envoi du message'
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      ElMessage.error(errorMessage)
      
      return null
      
    } finally {
      isSending.value = false
      isGenerating.value = false
    }
  }
  
  // ===========================================================================
  // ACTIONS - FEEDBACKS
  // ===========================================================================
  
  /**
   * Ajouter un feedback sur un message
   */
  async function addFeedback(messageId, rating, comment = null) {
    try {
      console.log('📝 Ajout feedback:', { messageId, rating })
      
      const response = await api.post(`/chat/messages/${messageId}/feedback`, {
        message_id: messageId,
        rating,
        comment
      })
      
      // Mettre à jour le message dans la liste
      const message = messages.value.find(m => m.id === messageId)
      if (message) {
        message.feedback = {
          rating,
          comment,
          created_at: new Date().toISOString()
        }
      }
      
      ElMessage.success('Feedback enregistré')
      console.log('✅ Feedback ajouté')
      
      return true
      
    } catch (error) {
      console.error('❌ Erreur ajout feedback:', error)
      ElMessage.error('Erreur lors de l\'enregistrement du feedback')
      return false
    }
  }
  
  async function sendFeedback(messageId, rating, comment = null) {
    return addFeedback(messageId, rating, comment)
  }
  
  async function deleteFeedback(messageId) {
    try {
      await api.delete(`/chat/messages/${messageId}/feedback`)
      
      const message = messages.value.find(m => m.id === messageId)
      if (message) {
        message.feedback = null
      }
      
      console.log('✅ Feedback supprimé')
      return true
      
    } catch (error) {
      console.error('❌ Erreur suppression feedback:', error)
      return false
    }
  }
  
  // ===========================================================================
  // ACTIONS - UTILITAIRES
  // ===========================================================================
  
  function reset() {
    conversations.value = []
    currentConversation.value = null
    messages.value = []
    page.value = 1
    total.value = 0
    totalPages.value = 1
    filters.value = { search: '', include_archived: false }
    isLoading.value = false
    isLoadingMessages.value = false
    isSending.value = false
    isGenerating.value = false
    
    console.log('🔄 Chat store réinitialisé')
  }
  
  function $reset() {
    reset()
  }
  
  async function setPage(newPage) {
    page.value = newPage
    await fetchConversations()
  }
  
  async function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
    await fetchConversations()
  }
  
  // ===========================================================================
  // RETURN
  // ===========================================================================
  
  return {
    // State
    conversations,
    currentConversation,
    messages,
    page,
    pageSize,
    total,
    totalPages,
    filters,
    isLoading,
    isLoadingMessages,
    isSending,
    isGenerating,
    
    // Getters
    activeConversations,
    archivedConversations,
    hasCurrentConversation,
    sortedMessages,
    lastAssistantMessage,
    canSendMessage,
    
    // Actions - Conversations
    fetchConversations,
    fetchConversation,
    selectConversation,
    createConversation,
    deleteConversation,
    archiveConversation,
    updateConversationTitle,
    updateConversation,
    
    // Actions - Messages
    sendMessage,
    
    // Actions - Feedbacks
    addFeedback,
    sendFeedback,
    deleteFeedback,
    
    // Actions - Utilitaires
    reset,
    $reset,
    setPage,
    setFilters
  }
})