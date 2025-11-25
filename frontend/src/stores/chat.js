/**
 * Store Pinia pour la gestion du chat.
 * 
 * Gère :
 * - Liste des conversations de l'utilisateur
 * - Conversation courante et ses messages
 * - Envoi de messages avec streaming SSE
 * - Feedbacks sur les messages
 * - Archivage et suppression de conversations
 * 
 * Sprint 8 - Phase 1 : Stores & Composables
 * CORRECTIONS V2 :
 * - Utilise /api/v1/chat/stream (pas /chat/send)
 * - Support streaming SSE correct
 * - Fallback machine à écrire si pas de streaming
 * - Roles en MAJUSCULE (USER, ASSISTANT)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api/auth'
import { ElMessage, ElNotification } from 'element-plus'

// Alias pour compatibilité
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
  const isStreaming = ref(false)
  
  // Streaming state
  const streamingContent = ref('')
  const streamingSources = ref([])
  const streamingMessageId = ref(null)
  
  // SSE connection
  let eventSource = null
  let abortController = null
  
  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /**
   * Conversations non archivées triées par date (plus récente en premier)
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
   * Messages de la conversation courante triés chronologiquement
   */
  const sortedMessages = computed(() => {
    return [...messages.value].sort(
      (a, b) => new Date(a.created_at) - new Date(b.created_at)
    )
  })
  
  /**
   * Dernier message de l'assistant
   * CORRIGÉ : Supporte role en majuscule (ASSISTANT)
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
    return !isSending.value && !isStreaming.value
  })
  
  // ===========================================================================
  // ACTIONS - CONVERSATIONS
  // ===========================================================================
  
  /**
   * Récupérer la liste des conversations de l'utilisateur.
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
   * Récupérer les détails d'une conversation avec ses messages.
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
   * Créer une nouvelle conversation.
   */
  function createConversation() {
    currentConversation.value = null
    messages.value = []
    streamingContent.value = ''
    streamingSources.value = []
    streamingMessageId.value = null
    
    console.log('✅ Nouvelle conversation initialisée')
  }
  
  /**
   * Sélectionner une conversation
   */
  async function selectConversation(conversationId) {
    return fetchConversation(conversationId)
  }
  
  /**
   * Supprimer une conversation.
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
   * Archiver ou désarchiver une conversation.
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
      console.log('✅ Conversation', archive ? 'archivée' : 'désarchivée')
      
      return true
      
    } catch (error) {
      console.error('❌ Erreur archivage:', error)
      ElMessage.error('Erreur lors de l\'archivage')
      return false
    }
  }
  
  /**
   * Mettre à jour le titre d'une conversation.
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
  
  /**
   * Mettre à jour une conversation (alias)
   */
  async function updateConversation(conversationId, data) {
    if (data.title) {
      return updateConversationTitle(conversationId, data.title)
    }
    return false
  }
  
  // ===========================================================================
  // ACTIONS - MESSAGES
  // ===========================================================================
  
  /**
   * Envoyer un message et recevoir la réponse.
   * 
   * CORRIGÉ V2 :
   * - Utilise /api/v1/chat/stream pour le streaming
   * - Fallback sur /api/v1/chat (sync) si streaming échoue
   * - Support SSE correct avec ReadableStream
   * 
   * @param {string} messageContent - Contenu du message
   * @param {string|null} conversationId - ID de la conversation (optionnel)
   * @returns {Promise<Object|null>} Résultat de l'envoi
   */
  async function sendMessage(messageContent, conversationId = null) {
    if (!messageContent?.trim() || isSending.value || isStreaming.value) {
      return null
    }
    
    isSending.value = true
    isStreaming.value = true
    streamingContent.value = ''
    streamingSources.value = []
    streamingMessageId.value = null
    
    // Ajouter le message utilisateur localement immédiatement
    // CORRIGÉ : Utilise 'USER' en majuscule pour cohérence avec backend
    const userMessage = {
      id: `temp-user-${Date.now()}`,
      role: 'USER',
      content: messageContent,
      created_at: new Date().toISOString()
    }
    messages.value.push(userMessage)
    
    // Préparer le message assistant en attente
    // CORRIGÉ : Utilise 'ASSISTANT' en majuscule
    const assistantMessage = {
      id: `temp-assistant-${Date.now()}`,
      role: 'ASSISTANT',
      content: '',
      sources: [],
      created_at: new Date().toISOString(),
      isStreaming: true
    }
    messages.value.push(assistantMessage)
    
    try {
      const token = localStorage.getItem('access_token')
      const convId = conversationId || currentConversation.value?.id
      
      // Créer l'AbortController pour pouvoir annuler
      abortController = new AbortController()
      
      // =====================================================================
      // CORRIGÉ V2 : Utiliser le BON endpoint /api/v1/chat/stream
      // =====================================================================
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({
          message: messageContent,
          conversation_id: convId
        }),
        signal: abortController.signal
      })
      
      if (!response.ok) {
        // Si l'endpoint stream échoue, essayer l'endpoint sync
        console.warn('⚠️ Endpoint stream a échoué, essai de l\'endpoint sync...')
        return await sendMessageSync(messageContent, conversationId, assistantMessage, userMessage)
      }
      
      // Vérifier le type de contenu pour savoir si c'est du streaming
      const contentType = response.headers.get('content-type')
      console.log('📡 Content-Type reçu:', contentType)
      
      if (contentType?.includes('text/event-stream')) {
        // Streaming SSE
        await handleSSEStream(response, assistantMessage)
      } else if (contentType?.includes('application/json')) {
        // Réponse JSON standard (fallback)
        const data = await response.json()
        await handleJSONWithTypingEffect(data, assistantMessage, userMessage)
      } else {
        // Tenter de parser comme SSE quand même
        await handleSSEStream(response, assistantMessage)
      }
      
      // Marquer le streaming comme terminé
      // CORRECTION V4 : Utiliser findIndex avec l'ID temporaire
      const msgIndex = messages.value.findIndex(m => m.id === assistantMessage.id)
      if (msgIndex !== -1) {
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          isStreaming: false
        }
      }
      
      console.log('✅ Message envoyé avec succès')
      
      // Recharger les conversations pour avoir les mises à jour
      if (!convId) {
        await fetchConversations()
      }
      
      return {
        success: true,
        conversation_id: currentConversation.value?.id,
        message_id: streamingMessageId.value
      }
      
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('⚠️ Streaming annulé')
        ElMessage.warning('Génération annulée')
      } else {
        console.error('❌ Erreur envoi message:', error)
        ElMessage.error('Erreur lors de l\'envoi du message')
      }
      
      // Retirer le message assistant en erreur
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg?.role?.toUpperCase() === 'ASSISTANT' && lastMsg?.isStreaming) {
        messages.value.pop()
      }
      
      return null
    } finally {
      isSending.value = false
      isStreaming.value = false
      abortController = null
    }
  }
  
  /**
   * Envoyer un message en mode synchrone (fallback)
   */
  async function sendMessageSync(messageContent, conversationId, assistantMessage, userMessage) {
    try {
      const token = localStorage.getItem('access_token')
      const convId = conversationId || currentConversation.value?.id
      
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: messageContent,
          conversation_id: convId
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      await handleJSONWithTypingEffect(data, assistantMessage, userMessage)
      
      // Marquer comme terminé
      // CORRECTION V4 : Utiliser findIndex avec l'ID temporaire
      const msgIndex = messages.value.findIndex(m => m.id === assistantMessage.id)
      if (msgIndex !== -1) {
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          isStreaming: false
        }
      }
      
      if (!convId) {
        await fetchConversations()
      }
      
      return {
        success: true,
        conversation_id: currentConversation.value?.id,
        message_id: streamingMessageId.value
      }
      
    } catch (error) {
      console.error('❌ Erreur sync:', error)
      throw error
    }
  }
  
  /**
   * Gérer un stream SSE avec ReadableStream
   */
  async function handleSSEStream(response, assistantMessage) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    console.log('📡 Démarrage du streaming SSE...')
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        console.log('📡 Stream terminé')
        break
      }
      
      buffer += decoder.decode(value, { stream: true })
      
      // Parser les événements SSE (format: "data: {...}\n\n")
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        // Ignorer les lignes vides et les commentaires
        if (!line || line.startsWith(':')) continue
        
        // Ignorer les lignes "event:"
        if (line.startsWith('event:')) continue
        
        if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim()
          
          // Fin du stream
          if (dataStr === '[DONE]') {
            console.log('📡 Reçu [DONE]')
            continue
          }
          
          // Ignorer les données vides
          if (!dataStr) continue
          
          try {
            const data = JSON.parse(dataStr)
            processStreamEvent(data, assistantMessage)
          } catch (e) {
            console.warn('⚠️ Erreur parsing SSE:', e, 'Data:', dataStr)
          }
        }
      }
    }
  }
  
  /**
   * Traiter un événement du stream
   * 
   * CORRIGÉ V4 : Utilise findIndex() avec l'ID temporaire qui NE CHANGE JAMAIS.
   * Force la réactivité Vue en remplaçant l'objet dans l'array.
   * 
   * IMPORTANT : On garde l'ID temporaire (temp-assistant-xxx) tout au long du streaming.
   * L'ID serveur est stocké dans server_message_id pour référence future.
   */
  function processStreamEvent(data, assistantMessage) {
    const eventType = data.event || data.type
    
    // CORRECTION V4 : Utiliser findIndex() avec l'ID temporaire qui ne change JAMAIS
    // Pinia wrappe les objets dans des Proxies, donc indexOf() ne fonctionne pas
    const msgIndex = messages.value.findIndex(m => m.id === assistantMessage.id)
    
    if (msgIndex === -1) {
      console.warn('⚠️ Message assistant introuvable:', assistantMessage.id)
      return
    }
    
    switch (eventType) {
      case 'start':
        // Début du streaming
        if (data.conversation_id) {
          if (!currentConversation.value) {
            currentConversation.value = {
              id: data.conversation_id,
              title: data.title || 'Nouvelle conversation',
              is_archived: false
            }
          }
        }
        streamingMessageId.value = data.message_id
        
        // CORRECTION V4 : Stocker l'ID serveur via messages.value[msgIndex]
        // Ne JAMAIS modifier assistantMessage.id (on garde l'ID temporaire)
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          server_message_id: data.message_id
        }
        
        console.log('📡 Stream start:', data.conversation_id)
        break
        
      case 'token':
      case 'content':
        // Nouveau token de contenu
        const tokenContent = data.content || data.token || ''
        streamingContent.value += tokenContent
        
        // CORRECTION : Forcer la réactivité Vue en créant un nouvel objet
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          content: streamingContent.value
        }
        
        // Debug: afficher les premiers tokens
        if (streamingContent.value.length < 50) {
          console.log('🔤 Token reçu, contenu actuel:', streamingContent.value.substring(0, 50))
        }
        break
        
      case 'sources':
        // Sources de la réponse
        streamingSources.value = data.sources || []
        
        // CORRECTION : Forcer la réactivité Vue
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          sources: streamingSources.value
        }
        console.log('📚 Sources:', streamingSources.value.length)
        break
        
      case 'metadata':
        // Métadonnées finales
        // CORRECTION : Forcer la réactivité Vue
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          token_count_input: data.token_count_input,
          token_count_output: data.token_count_output,
          cost_usd: data.cost_usd,
          cost_xaf: data.cost_xaf,
          cache_hit: data.cache_hit,
          response_time_seconds: data.response_time_seconds,
          model_used: data.model_used
        }
        break
        
      case 'done':
      case 'end':
        // Fin du streaming
        // CORRECTION : Forcer la réactivité Vue
        messages.value[msgIndex] = {
          ...messages.value[msgIndex],
          isStreaming: false
        }
        console.log('✅ Stream done')
        break
        
      case 'error':
        console.error('❌ Stream error:', data.error || data.message)
        ElMessage.error(data.error || data.message || 'Erreur lors de la génération')
        break
        
      default:
        // Pour les événements sans type, vérifier s'il y a du contenu
        if (data.content || data.token) {
          const content = data.content || data.token || ''
          streamingContent.value += content
          
          // CORRECTION : Forcer la réactivité Vue
          messages.value[msgIndex] = {
            ...messages.value[msgIndex],
            content: streamingContent.value
          }
        }
        // Vérifier s'il y a des sources
        if (data.sources && Array.isArray(data.sources)) {
          streamingSources.value = data.sources
          
          // CORRECTION : Forcer la réactivité Vue
          messages.value[msgIndex] = {
            ...messages.value[msgIndex],
            sources: streamingSources.value
          }
        }
    }
  }
  
  /**
   * Gérer une réponse JSON avec effet machine à écrire
   * 
   * CORRIGÉ V4 : Utilise findIndex() avec les IDs temporaires qui ne changent jamais.
   * Force la réactivité Vue en créant de nouveaux objets.
   */
  async function handleJSONWithTypingEffect(data, assistantMessage, userMessage) {
    // Mettre à jour l'ID du message utilisateur
    if (data.user_message_id) {
      const userMsgIndex = messages.value.findIndex(m => m.id === userMessage.id)
      if (userMsgIndex !== -1) {
        // Stocker l'ID serveur sans modifier l'ID temporaire
        messages.value[userMsgIndex] = {
          ...messages.value[userMsgIndex],
          server_message_id: data.user_message_id
        }
      }
    }
    
    // Mettre à jour la conversation
    if (data.conversation_id) {
      if (!currentConversation.value) {
        currentConversation.value = {
          id: data.conversation_id,
          title: data.title || 'Nouvelle conversation',
          is_archived: false
        }
      }
    }
    
    // Récupérer le contenu complet
    const fullContent = data.content || data.message || data.response || ''
    const sources = data.sources || []
    
    // Trouver le message assistant avec findIndex
    const msgIndex = messages.value.findIndex(m => m.id === assistantMessage.id)
    if (msgIndex === -1) return
    
    // Effet machine à écrire
    const chunkSize = 3
    const baseDelay = fullContent.length > 500 ? 5 : 12
    
    for (let i = 0; i < fullContent.length; i += chunkSize) {
      if (abortController?.signal.aborted) break
      
      const chunk = fullContent.substring(0, i + chunkSize)
      
      // CORRECTION : Forcer la réactivité Vue
      messages.value[msgIndex] = {
        ...messages.value[msgIndex],
        content: chunk
      }
      streamingContent.value = chunk
      
      await new Promise(resolve => setTimeout(resolve, baseDelay))
    }
    
    // S'assurer que tout le contenu est affiché
    streamingContent.value = fullContent
    
    // Ajouter les sources et métadonnées avec réactivité forcée
    messages.value[msgIndex] = {
      ...messages.value[msgIndex],
      content: fullContent,
      server_message_id: data.message_id || data.id,
      sources: sources,
      token_count_input: data.token_count_input,
      token_count_output: data.token_count_output,
      cost_usd: data.cost_usd,
      cost_xaf: data.cost_xaf,
      cache_hit: data.cache_hit,
      response_time_seconds: data.response_time_seconds,
      model_used: data.model_used
    }
    
    streamingMessageId.value = data.message_id || data.id
    streamingSources.value = sources
  }
  
  /**
   * Annuler le streaming en cours.
   */
  function cancelStreaming() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isStreaming.value = false
    isSending.value = false
    
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg?.isStreaming) {
      lastMsg.isStreaming = false
      lastMsg.content += '\n\n_(Génération annulée)_'
    }
  }
  
  // ===========================================================================
  // ACTIONS - FEEDBACKS
  // ===========================================================================
  
  /**
   * Ajouter ou mettre à jour un feedback sur un message.
   */
  async function addFeedback(messageId, rating, comment = null) {
    try {
      const response = await api.post(`/chat/messages/${messageId}/feedback`, {
        message_id: messageId,
        rating,
        comment
      })
      
      const message = messages.value.find(m => m.id === messageId)
      if (message) {
        message.feedback = {
          rating,
          comment,
          created_at: new Date().toISOString()
        }
      }
      
      ElMessage.success('Feedback enregistré')
      console.log('✅ Feedback ajouté:', rating)
      
      return true
      
    } catch (error) {
      console.error('❌ Erreur ajout feedback:', error)
      ElMessage.error('Erreur lors de l\'enregistrement du feedback')
      return false
    }
  }
  
  /**
   * Envoyer un feedback (alias)
   */
  async function sendFeedback(messageId, rating, comment = null) {
    return addFeedback(messageId, rating, comment)
  }
  
  /**
   * Supprimer un feedback sur un message.
   */
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
  
  /**
   * Réinitialiser l'état du store.
   */
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
    isStreaming.value = false
    streamingContent.value = ''
    streamingSources.value = []
    streamingMessageId.value = null
    
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    
    console.log('🔄 Chat store réinitialisé')
  }
  
  function $reset() {
    reset()
  }
  
  function closeSSE() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
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
    isStreaming,
    streamingContent,
    streamingSources,
    streamingMessageId,
    
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
    cancelStreaming,
    closeSSE,
    
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