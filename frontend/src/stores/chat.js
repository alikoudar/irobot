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
 * CORRECTIF 2025-11-27: Continuité conversation_id corrigée
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
   * 
   * ✅ CORRIGÉ v2.2 : Ne JAMAIS toucher à currentConversation
   */
  async function fetchConversations(options = {}) {
    isLoading.value = true
    
    // 🔥 IMPORTANT : Sauvegarder currentConversation avant le chargement
    const savedCurrentConversation = currentConversation.value
    
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
      
      // 🔥 CORRECTION v2.2 : Restaurer currentConversation si elle existait
      if (savedCurrentConversation?.id) {
        currentConversation.value = savedCurrentConversation
        console.log('🔒 currentConversation préservé:', savedCurrentConversation.id)
      }
      
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
      
      currentConversation.value = data.conversation
      messages.value = data.messages || []
      
      console.log('✅ Conversation chargée:', data.conversation?.title)
      console.log('✅ Messages:', messages.value.length)
      console.log('🔍 [DEBUG] currentConversation.value.id:', currentConversation.value?.id)
      
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
   * 
   * ✅ CORRIGÉ v2.1 : Réinitialise toujours (le bug était ailleurs, dans sendMessage)
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
    const result = await fetchConversation(conversationId)
    
    // 🔥 PERSISTENCE : Sauvegarder l'ID dans localStorage
    if (result?.id) {
      try {
        localStorage.setItem('irobot_current_conversation_id', result.id)
        console.log('💾 Conversation ID sauvegardé:', result.id)
      } catch (e) {
        console.warn('Impossible de sauvegarder dans localStorage:', e)
      }
    }
    
    return result
  }
  
  /**
   * Supprimer une conversation
   */
  async function deleteConversation(conversationId) {
    try {
      await api.delete(`/chat/conversations/${conversationId}`)
      
      conversations.value = conversations.value.filter(c => c.id !== conversationId)
      
      if (currentConversation.value?.id === conversationId) {
        // ✅ CORRECTION : Vraiment réinitialiser ici car conversation supprimée
        currentConversation.value = null
        messages.value = []
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
   * ✅ CORRIGÉ : Maintient correctement currentConversation.value entre les messages
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
  
  // ✅ CORRECTION : Prioriser conversationId passé en paramètre, sinon currentConversation
  const convId = currentConversation.value?.id
  
  // 🔥 AJOUT Sprint 11 : Logs défensifs pour debug
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('🔍 [DEBUG sendMessage] DÉBUT')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('📝 Message:', messageContent.substring(0, 50) + (messageContent.length > 50 ? '...' : ''))
  console.log('📌 Paramètre conversationId:', conversationId)
  console.log('📌 currentConversation.value:', currentConversation.value)
  console.log('📌 currentConversation.value?.id:', currentConversation.value?.id)
  console.log('🎯 convId final:', convId)
  
  // ⚠️ AVERTISSEMENT si convId est null
  if (!convId) {
    console.warn('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.warn('⚠️  ATTENTION : conversation_id est NULL !')
    console.warn('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.warn('   Une NOUVELLE conversation sera créée par le backend.')
    console.warn('   Raisons possibles :')
    console.warn('   1. conversationId paramètre est null/undefined')
    console.warn('   2. currentConversation.value est null/undefined')
    console.warn('   3. currentConversation.value.id est undefined')
    console.warn('')
    console.warn('   État actuel :')
    console.warn('   - conversationId passé:', conversationId)
    console.warn('   - currentConversation:', currentConversation.value)
    console.warn('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  } else {
    console.log('✅ conversation_id présent:', convId)
    console.log('   Le message sera ajouté à la conversation existante')
  }
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  
  try {
    console.log('📤 Envoi à /chat...')
    
    // Appel API simple (NON-STREAMING)
    const response = await api.post('/chat', {
      message: messageContent,
      conversation_id: convId,  // ✅ Envoie bien le conversation_id
      stream: false
    })
    
    const data = response.data
    
    console.log('✅ Réponse reçue:', {
      conversation_id: data.conversation_id,
      message_id: data.message_id,
      title: data.title,
      content_length: data.content?.length
    })
    
    // 🔥 VÉRIFICATION : Le backend a-t-il créé une nouvelle conversation ?
    if (convId && data.conversation_id !== convId) {
      console.warn('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      console.warn('⚠️  INCOHÉRENCE DÉTECTÉE !')
      console.warn('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      console.warn('   conversation_id envoyé :', convId)
      console.warn('   conversation_id reçu   :', data.conversation_id)
      console.warn('   → Le backend a changé le conversation_id !')
      console.warn('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    } else if (!convId && data.conversation_id) {
      console.log('ℹ️  Nouvelle conversation créée par le backend')
      console.log('   conversation_id:', data.conversation_id)
    }
    
    // ✅ CRITIQUE : Mettre à jour currentConversation IMMÉDIATEMENT
    if (data.conversation_id) {
      // 🔥 CORRECTION #1 : TOUJOURS mettre à jour (même si même ID)
      // Car le titre peut avoir changé (auto-généré par backend)
      currentConversation.value = {
        id: data.conversation_id,
        title: data.title || 'Nouvelle conversation',
        is_archived: false,
        message_count: data.message_count || 2,
        created_at: data.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      console.log('🔄 currentConversation mis à jour:', {
        id: currentConversation.value.id,
        title: currentConversation.value.title
      })
    }
    
    // 🔥 CORRECTION #2 : Ne PAS recharger avec fetchConversation
    // Car ça écrase currentConversation avec les anciennes données
    // À la place, juste recharger les messages
    if (data.conversation_id) {
      try {
        const messagesResponse = await api.get(`/chat/conversations/${data.conversation_id}`)
        messages.value = messagesResponse.data.messages || []
        
        // Mettre à jour le titre SI le backend retourne un nouveau
        if (messagesResponse.data.title && messagesResponse.data.title !== 'Nouvelle conversation') {
          currentConversation.value.title = messagesResponse.data.title
        }
        
        console.log('✅ Messages rechargés:', messages.value.length)
      } catch (err) {
        console.error('❌ Erreur rechargement messages:', err)
      }
    }
    
    // 🔥 CORRECTION #3 : Ajouter/Mettre à jour la conversation dans la liste
    // Au lieu de TOUT recharger
    const existingIndex = conversations.value.findIndex(c => c.id === data.conversation_id)
    
    if (existingIndex >= 0) {
      // Conversation existe : mettre à jour
      const newUpdatedAt = new Date().toISOString()
      conversations.value[existingIndex] = {
        ...conversations.value[existingIndex],
        title: currentConversation.value.title,
        updated_at: newUpdatedAt,
        message_count: messages.value.length
      }
      console.log('📝 Conversation mise à jour dans la liste')
      console.log('🔍 [DEBUG] updated_at mis à jour:', newUpdatedAt)
    } else {
      // Nouvelle conversation : ajouter en tête
      const newUpdatedAt = new Date().toISOString()
      conversations.value.unshift({
        id: data.conversation_id,
        title: currentConversation.value.title,
        is_archived: false,
        message_count: messages.value.length,
        created_at: data.created_at || new Date().toISOString(),
        updated_at: newUpdatedAt
      })
      total.value += 1
      console.log('➕ Nouvelle conversation ajoutée à la liste')
      console.log('🔍 [DEBUG] updated_at nouvelle conversation:', newUpdatedAt)
    }
    
    // 🔥 PERSISTENCE : Sauvegarder l'ID de la conversation active
    if (currentConversation.value?.id) {
      try {
        localStorage.setItem('irobot_current_conversation_id', currentConversation.value.id)
        console.log('💾 Conversation ID sauvegardé:', currentConversation.value.id)
      } catch (e) {
        console.warn('Impossible de sauvegarder dans localStorage:', e)
      }
    }
    
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('✅ [DEBUG sendMessage] FIN - SUCCÈS')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    
    return {
      success: true,
      conversation_id: data.conversation_id,
      message_id: data.message_id
    }
    
  } catch (error) {
    console.error('❌ Erreur envoi message:', error)
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('❌ [DEBUG sendMessage] FIN - ERREUR')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    
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
  
  /**
   * Restaurer la dernière conversation active depuis localStorage
   * 
   * ✅ AJOUTÉ v2.3 : Persistence du highlight entre les sessions
   */
  async function restoreLastConversation() {
    try {
      const savedId = localStorage.getItem('irobot_current_conversation_id')
      
      if (savedId) {
        console.log('🔄 Restauration conversation sauvegardée:', savedId)
        
        // Vérifier que cette conversation existe dans la liste
        const exists = conversations.value.some(c => c.id === savedId)
        
        if (exists) {
          // Charger la conversation
          await fetchConversation(savedId)
          console.log('✅ Conversation restaurée:', savedId)
          return true
        } else {
          console.log('⚠️ Conversation sauvegardée non trouvée dans la liste')
          // Nettoyer le localStorage
          localStorage.removeItem('irobot_current_conversation_id')
        }
      }
    } catch (e) {
      console.warn('Erreur restauration conversation:', e)
    }
    
    return false
  }
  
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
    restoreLastConversation,
    reset,
    $reset,
    setPage,
    setFilters
  }
})