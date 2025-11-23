/**
 * Store Pinia pour la gestion des documents.
 * 
 * Gère :
 * - Upload de documents (max 10 simultanément)
 * - Liste des documents avec filtres et pagination
 * - Suivi du statut de traitement (SSE)
 * - Retry des documents en erreur
 * - Suppression de documents
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api/auth'
import { ElMessage, ElNotification } from 'element-plus'

// Alias pour compatibilité
const api = apiClient

export const useDocumentsStore = defineStore('documents', () => {
  // ==========================================================================
  // STATE
  // ==========================================================================
  
  const documents = ref([])
  const currentDocument = ref(null)
  const categories = ref([])
  
  // Pagination
  const page = ref(1)
  const pageSize = ref(20)  // Aligné avec le backend par défaut
  const total = ref(0)
  const totalPagesFromServer = ref(1)  // Stocke la valeur du serveur
  
  // Filtres
  const filters = ref({
    status: null,
    category_id: null,
    search: '',
    file_types: null,      // Types de fichiers (array ou null)
    date_from: null,       // Date de début
    date_to: null          // Date de fin
  })
  
  // Loading states
  const isLoading = ref(false)
  const isUploading = ref(false)
  const uploadProgress = ref(0)
  
  // Upload tracking
  const uploadingFiles = ref([])  // { file, progress, status, error }
  
  // SSE connection for real-time status updates
  let eventSource = null
  
  // ==========================================================================
  // GETTERS
  // ==========================================================================
  
  const totalPages = computed(() => totalPagesFromServer.value)
  
  const pendingDocuments = computed(() => 
    documents.value.filter(d => d.status === 'PENDING' || d.status === 'PROCESSING')
  )
  
  const completedDocuments = computed(() => 
    documents.value.filter(d => d.status === 'COMPLETED')
  )
  
  const failedDocuments = computed(() => 
    documents.value.filter(d => d.status === 'FAILED')
  )
  
  const hasActiveUploads = computed(() => 
    uploadingFiles.value.some(f => f.status === 'uploading' || f.status === 'processing')
  )
  
  // ==========================================================================
  // ACTIONS - FETCH
  // ==========================================================================
  
  /**
   * Récupérer la liste des documents avec filtres et pagination.
   */
  async function fetchDocuments() {
    isLoading.value = true
    try {
      const params = {
        page: page.value,
        limit: pageSize.value  // Backend utilise 'limit', pas 'page_size'
      }
      
      // Ajouter les filtres non null
      if (filters.value.status) {
        params.status = filters.value.status
      }
      if (filters.value.category_id) {
        params.category_id = filters.value.category_id
      }
      if (filters.value.search) {
        params.search = filters.value.search
      }
      
      // Filtre par types de fichiers (convertir array en string séparée par virgules)
      if (filters.value.file_types && filters.value.file_types.length > 0) {
        params.file_types = filters.value.file_types.join(',')
      }
      
      // Filtres de date
      if (filters.value.date_from) {
        params.date_from = filters.value.date_from
      }
      if (filters.value.date_to) {
        params.date_to = filters.value.date_to
      }
      
      const response = await api.get('/documents', { params })
      documents.value = response.data.items || response.data
      total.value = response.data.total || documents.value.length
      totalPagesFromServer.value = response.data.pages || 1  // Utiliser la valeur du serveur
      
      return true
    } catch (error) {
      console.error('Erreur chargement documents:', error)
      ElMessage.error('Erreur lors du chargement des documents')
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Récupérer un document par ID.
   */
  async function fetchDocument(documentId) {
    isLoading.value = true
    try {
      const response = await api.get(`/documents/${documentId}`)
      currentDocument.value = response.data
      return response.data
    } catch (error) {
      console.error('Erreur chargement document:', error)
      ElMessage.error('Document non trouvé')
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Récupérer les catégories disponibles.
   */
  async function fetchCategories() {
    try {
      const response = await api.get('/categories')
      categories.value = response.data.items || response.data
      return categories.value
    } catch (error) {
      console.error('Erreur chargement catégories:', error)
      return []
    }
  }
  
  // ==========================================================================
  // ACTIONS - UPLOAD
  // ==========================================================================
  
  /**
   * Uploader plusieurs documents.
   * 
   * @param {File[]} files - Liste des fichiers à uploader
   * @param {string} categoryId - ID de la catégorie
   * @returns {Promise<Object>} Résultat de l'upload
   */
  async function uploadDocuments(files, categoryId) {
    if (!files || files.length === 0) {
      ElMessage.warning('Aucun fichier sélectionné')
      return null
    }
    
    if (files.length > 10) {
      ElMessage.error('Maximum 10 fichiers par upload')
      return null
    }
    
    if (!categoryId) {
      ElMessage.warning('Veuillez sélectionner une catégorie')
      return null
    }
    
    isUploading.value = true
    uploadProgress.value = 0
    
    // Initialiser le tracking des fichiers
    uploadingFiles.value = files.map(file => ({
      file,
      name: file.name,
      size: file.size,
      progress: 0,
      status: 'pending',  // pending, uploading, processing, completed, failed
      error: null,
      documentId: null
    }))
    
    try {
      // Créer le FormData
      const formData = new FormData()
      formData.append('category_id', categoryId)
      
      files.forEach(file => {
        formData.append('files', file)
      })
      
      // Mettre à jour le status
      uploadingFiles.value.forEach(f => f.status = 'uploading')
      
      // Upload avec suivi de progression
      const response = await api.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          uploadProgress.value = progress
          uploadingFiles.value.forEach(f => {
            if (f.status === 'uploading') {
              f.progress = progress
            }
          })
        }
      })
      
      const result = response.data
      
      // Mettre à jour le status des fichiers
      if (result.documents) {
        result.documents.forEach(doc => {
          const fileTrack = uploadingFiles.value.find(
            f => f.name === doc.original_filename
          )
          if (fileTrack) {
            fileTrack.status = 'processing'
            fileTrack.documentId = doc.id
            fileTrack.progress = 100
          }
        })
      }
      
      // Marquer les erreurs
      if (result.errors) {
        result.errors.forEach(err => {
          const fileTrack = uploadingFiles.value.find(
            f => f.name === err.filename
          )
          if (fileTrack) {
            fileTrack.status = 'failed'
            fileTrack.error = err.error
          }
        })
      }
      
      // Notification de succès
      const successCount = result.uploaded || result.documents?.length || 0
      const errorCount = result.errors?.length || 0
      
      if (successCount > 0) {
        ElNotification({
          title: 'Upload réussi',
          message: `${successCount} document(s) envoyé(s) au traitement`,
          type: 'success',
          duration: 5000
        })
      }
      
      if (errorCount > 0) {
        ElNotification({
          title: 'Erreurs upload',
          message: `${errorCount} fichier(s) n'ont pas pu être uploadés`,
          type: 'warning',
          duration: 5000
        })
      }
      
      // Rafraîchir la liste
      await fetchDocuments()
      
      return result
      
    } catch (error) {
      console.error('Erreur upload:', error)
      
      // Marquer tous les fichiers en erreur
      uploadingFiles.value.forEach(f => {
        if (f.status === 'uploading' || f.status === 'pending') {
          f.status = 'failed'
          f.error = error.response?.data?.detail || 'Erreur lors de l\'upload'
        }
      })
      
      ElMessage.error(error.response?.data?.detail || 'Erreur lors de l\'upload')
      return null
      
    } finally {
      isUploading.value = false
    }
  }
  
  // ==========================================================================
  // ACTIONS - SSE (Real-time status updates)
  // ==========================================================================
  
  /**
   * S'abonner aux mises à jour de statut d'un document via SSE.
   * 
   * @param {string} documentId - ID du document à suivre
   */
  function subscribeToDocumentStatus(documentId) {
    // Fermer la connexion existante
    if (eventSource) {
      eventSource.close()
    }
    
    const token = localStorage.getItem('access_token')
    const url = `${import.meta.env.VITE_API_URL || ''}/api/v1/documents/${documentId}/status?token=${token}`
    
    eventSource = new EventSource(url)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Mettre à jour le document dans la liste
        const index = documents.value.findIndex(d => d.id === documentId)
        if (index !== -1) {
          documents.value[index] = { ...documents.value[index], ...data }
        }
        
        // Mettre à jour le tracking d'upload
        const fileTrack = uploadingFiles.value.find(f => f.documentId === documentId)
        if (fileTrack) {
          if (data.status === 'COMPLETED') {
            fileTrack.status = 'completed'
          } else if (data.status === 'FAILED') {
            fileTrack.status = 'failed'
            fileTrack.error = data.error_message
          } else {
            fileTrack.status = 'processing'
            fileTrack.stage = data.processing_stage
          }
        }
        
        // Notification si terminé
        if (data.status === 'COMPLETED') {
          ElNotification({
            title: 'Traitement terminé',
            message: `Le document "${data.original_filename}" est prêt`,
            type: 'success'
          })
          eventSource.close()
        } else if (data.status === 'FAILED') {
          ElNotification({
            title: 'Échec du traitement',
            message: `Erreur: ${data.error_message}`,
            type: 'error'
          })
          eventSource.close()
        }
        
      } catch (e) {
        console.error('Erreur parsing SSE:', e)
      }
    }
    
    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      eventSource.close()
    }
  }
  
  /**
   * Fermer la connexion SSE.
   */
  function unsubscribeFromStatus() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }
  
  // ==========================================================================
  // ACTIONS - RETRY / DELETE
  // ==========================================================================
  
  /**
   * Relancer le traitement d'un document en erreur.
   * 
   * @param {string} documentId - ID du document
   * @param {string} fromStage - Étape à partir de laquelle relancer
   */
  async function retryDocument(documentId, fromStage = 'EXTRACTION') {
    try {
      const response = await api.post(`/documents/${documentId}/retry`, {
        from_stage: fromStage
      })
      
      ElMessage.success('Traitement relancé')
      
      // Rafraîchir la liste
      await fetchDocuments()
      
      // S'abonner aux mises à jour
      subscribeToDocumentStatus(documentId)
      
      return response.data
      
    } catch (error) {
      console.error('Erreur retry:', error)
      ElMessage.error(error.response?.data?.detail || 'Erreur lors du retry')
      return null
    }
  }
  
  /**
   * Supprimer un document.
   * 
   * @param {string} documentId - ID du document
   */
  async function deleteDocument(documentId) {
    try {
      await api.delete(`/documents/${documentId}`)
      
      ElMessage.success('Document supprimé')
      
      // Retirer de la liste locale
      documents.value = documents.value.filter(d => d.id !== documentId)
      total.value -= 1
      
      return true
      
    } catch (error) {
      console.error('Erreur suppression:', error)
      ElMessage.error(error.response?.data?.detail || 'Erreur lors de la suppression')
      return false
    }
  }
  
  // ==========================================================================
  // ACTIONS - PAGINATION & FILTERS
  // ==========================================================================
  
  function changePage(newPage) {
    page.value = newPage
    fetchDocuments()
  }
  
  function changePageSize(newSize) {
    pageSize.value = newSize
    page.value = 1
    fetchDocuments()
  }
  
  function applyFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
    fetchDocuments()
  }
  
  function resetFilters() {
    filters.value = {
      status: null,
      category_id: null,
      search: '',
      file_types: null,
      date_from: null,
      date_to: null
    }
    page.value = 1
    fetchDocuments()
  }
  
  function search(term) {
    filters.value.search = term
    page.value = 1
    fetchDocuments()
  }
  
  // ==========================================================================
  // ACTIONS - UTILS
  // ==========================================================================
  
  /**
   * Formater la taille d'un fichier.
   */
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
  
  /**
   * Obtenir l'icône selon le type de fichier.
   */
  function getFileIcon(extension) {
    const icons = {
      pdf: 'DocumentCopy',
      docx: 'Document',
      doc: 'Document',
      xlsx: 'Grid',
      xls: 'Grid',
      pptx: 'PictureFilled',
      ppt: 'PictureFilled',
      txt: 'Tickets',
      md: 'Tickets',
      png: 'Picture',
      jpg: 'Picture',
      jpeg: 'Picture',
      webp: 'Picture'
    }
    return icons[extension?.toLowerCase()] || 'Document'
  }
  
  /**
   * Obtenir la couleur du statut.
   */
  function getStatusColor(status) {
    const colors = {
      PENDING: 'info',
      PROCESSING: 'warning',
      COMPLETED: 'success',
      FAILED: 'danger'
    }
    return colors[status] || 'info'
  }
  
  /**
   * Obtenir le label du statut.
   */
  function getStatusLabel(status) {
    const labels = {
      PENDING: 'En attente',
      PROCESSING: 'En cours',
      COMPLETED: 'Terminé',
      FAILED: 'Échec'
    }
    return labels[status] || status
  }
  
  /**
   * Obtenir le label de l'étape de traitement.
   */
  function getStageLabel(stage) {
    const labels = {
      VALIDATION: 'Validation',
      EXTRACTION: 'Extraction',
      CHUNKING: 'Découpage',
      EMBEDDING: 'Embedding',
      INDEXING: 'Indexation'
    }
    return labels[stage] || stage
  }
  
  // ==========================================================================
  // CLEANUP
  // ==========================================================================
  
  function $reset() {
    documents.value = []
    currentDocument.value = null
    page.value = 1
    total.value = 0
    filters.value = { status: null, category_id: null, search: '' }
    isLoading.value = false
    isUploading.value = false
    uploadProgress.value = 0
    uploadingFiles.value = []
    unsubscribeFromStatus()
  }
  
  // ==========================================================================
  // RETURN
  // ==========================================================================
  
  return {
    // State
    documents,
    currentDocument,
    categories,
    page,
    pageSize,
    total,
    filters,
    isLoading,
    isUploading,
    uploadProgress,
    uploadingFiles,
    
    // Getters
    totalPages,
    pendingDocuments,
    completedDocuments,
    failedDocuments,
    hasActiveUploads,
    
    // Actions
    fetchDocuments,
    fetchDocument,
    fetchCategories,
    uploadDocuments,
    subscribeToDocumentStatus,
    unsubscribeFromStatus,
    retryDocument,
    deleteDocument,
    changePage,
    changePageSize,
    applyFilters,
    resetFilters,
    search,
    
    // Utils
    formatFileSize,
    getFileIcon,
    getStatusColor,
    getStatusLabel,
    getStageLabel,
    
    // Reset
    $reset
  }
})