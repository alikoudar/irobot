/**
 * Store Pinia pour l'authentification
 * 
 * CORRECTION : Reset du chat store lors de la connexion
 * pour éviter d'afficher les messages d'un autre utilisateur
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/api/auth'
import { ElMessage } from 'element-plus'
import { useChatStore } from './chat'


export const useAuthStore = defineStore('auth', () => {
  // State
  const currentUser = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!currentUser.value)
  const isAdmin = computed(() => currentUser.value?.role === 'ADMIN')
  const isManager = computed(() => currentUser.value?.role === 'MANAGER')
  const isUser = computed(() => currentUser.value?.role === 'USER')
  const userFullName = computed(() => {
    if (!currentUser.value) return ''
    return `${currentUser.value.prenom} ${currentUser.value.nom}`
  })
  const mustChangePassword = computed(() => currentUser.value?.must_change_password || false)

  // Actions

  /**
   * Obtenir la route par défaut selon le rôle de l'utilisateur
   * 
   * ADMIN → /admin/dashboard
   * MANAGER → /documents (Ingestion)
   * USER → /chat
   * 
   * @returns {string} Chemin de la route
   */
  function getDefaultRoute() {
    if (!currentUser.value) {
      return '/login'
    }
    
    const role = currentUser.value.role
    
    switch (role) {
      case 'ADMIN':
        return '/admin/dashboard'
      
      case 'MANAGER':
        return '/documents'  // Page d'ingestion
      
      case 'USER':
        return '/chat'
      
      default:
        // Fallback si le rôle est inconnu
        console.warn(`Rôle inconnu: ${role}, redirection vers /chat`)
        return '/chat'
    }
  }

  /**
   * Connexion utilisateur avec redirection automatique par rôle
   * @param {string} matricule - Matricule de l'utilisateur
   * @param {string} password - Mot de passe
   * @returns {Promise<{success: boolean, redirectTo?: string}>} Résultat avec route de redirection
   */
  async function login(matricule, password) {
    isLoading.value = true
    error.value = null

    try {
      const data = await authService.login(matricule, password)

      // Sauvegarder les tokens
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      // Sauvegarder l'utilisateur
      currentUser.value = data.user

      // =====================================================================
      // CORRECTION : Réinitialiser le chat store pour éviter d'afficher
      // les messages d'un autre utilisateur
      // =====================================================================
      const chatStore = useChatStore()
      chatStore.reset()
      console.log('🔄 Chat store réinitialisé après login')
      // =====================================================================

      // 🔥 NOUVEAU : Obtenir la route par défaut selon le rôle
      const redirectTo = getDefaultRoute()
      
      console.log(`✅ Connexion réussie - Rôle: ${data.user.role} - Redirection: ${redirectTo}`)
      ElMessage.success('Connexion réussie')
      
      // 🔥 NOUVEAU : Retourner success ET redirectTo
      return {
        success: true,
        redirectTo
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur de connexion'
      ElMessage.error(error.value)
      return {
        success: false
      }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Déconnexion utilisateur
   */
  async function logout() {
    isLoading.value = true

    try {
      await authService.logout()
    } catch (err) {
      console.error('Erreur lors de la déconnexion:', err)
    } finally {
      // Nettoyer le state local
      currentUser.value = null
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      isLoading.value = false

      // =====================================================================
      // CORRECTION : Réinitialiser aussi le chat store à la déconnexion
      // =====================================================================
      const chatStore = useChatStore()
      chatStore.reset()
      console.log('🔄 Chat store réinitialisé après logout')
      // =====================================================================

      ElMessage.info('Déconnexion réussie')
    }
  }

  /**
   * Rafraîchir le token d'accès
   * @returns {Promise<boolean>} Succès du refresh
   */
  async function refresh() {
    if (!refreshToken.value) {
      return false
    }

    try {
      const data = await authService.refreshToken(refreshToken.value)

      // Mettre à jour l'access token
      accessToken.value = data.access_token
      localStorage.setItem('access_token', data.access_token)

      return true
    } catch (err) {
      console.error('Erreur lors du refresh du token:', err)
      // Si le refresh échoue, déconnecter l'utilisateur
      await logout()
      return false
    }
  }

  /**
   * Récupérer les informations de l'utilisateur courant
   * @returns {Promise<boolean>} Succès de la récupération
   */
  async function fetchCurrentUser() {
    if (!accessToken.value) {
      return false
    }

    isLoading.value = true
    error.value = null

    try {
      const data = await authService.getCurrentUser()
      currentUser.value = data
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors de la récupération de l\'utilisateur'
      console.error(error.value)
      // Si l'utilisateur ne peut pas être récupéré, déconnecter
      await logout()
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Changer le mot de passe de l'utilisateur courant
   * @param {string} currentPassword - Mot de passe actuel
   * @param {string} newPassword - Nouveau mot de passe
   * @returns {Promise<boolean>} Succès du changement
   */
  async function changePassword(currentPassword, newPassword) {
    isLoading.value = true
    error.value = null

    try {
      await authService.changePassword(currentPassword, newPassword)

      // Mettre à jour le flag must_change_password
      if (currentUser.value) {
        currentUser.value.must_change_password = false
      }

      ElMessage.success('Mot de passe changé avec succès')
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors du changement de mot de passe'
      ElMessage.error(error.value)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Initialiser le store (à appeler au chargement de l'app)
   * Charge l'utilisateur courant si un token existe
   */
  async function initialize() {
    if (accessToken.value) {
      await fetchCurrentUser()
    }
  }

  /**
   * Vérifier si l'utilisateur a une permission donnée
   * @param {string|Array<string>} roles - Rôle(s) requis
   * @returns {boolean}
   */
  function hasRole(roles) {
    if (!currentUser.value) return false

    const rolesArray = Array.isArray(roles) ? roles : [roles]
    return rolesArray.includes(currentUser.value.role)
  }

  /**
   * Vérifier si l'utilisateur a accès à une fonctionnalité admin
   * @returns {boolean}
   */
  function canAccessAdmin() {
    return hasRole(['ADMIN'])
  }

  /**
   * Vérifier si l'utilisateur peut gérer les documents
   * @returns {boolean}
   */
  function canManageDocuments() {
    return hasRole(['ADMIN', 'MANAGER'])
  }

  /**
   * Mettre à jour le profil de l'utilisateur connecté
   * @param {Object} profileData - Données du profil à mettre à jour
   * @returns {Promise<boolean>} Succès de la mise à jour
   */
  async function updateProfile(profileData) {
    isLoading.value = true
    error.value = null

    try {
      const updatedUser = await authService.updateProfile(profileData)
      
      // Mettre à jour l'utilisateur courant
      currentUser.value = { ...currentUser.value, ...updatedUser }
      
      ElMessage.success('Profil mis à jour avec succès')
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors de la mise à jour du profil'
      ElMessage.error(error.value)
      return false
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    currentUser,
    accessToken,
    refreshToken,
    isLoading,
    error,

    // Getters
    isAuthenticated,
    isAdmin,
    isManager,
    isUser,
    userFullName,
    mustChangePassword,

    // Actions
    login,
    logout,
    refresh,
    fetchCurrentUser,
    changePassword,
    updateProfile,
    initialize,
    hasRole,
    canAccessAdmin,
    canManageDocuments,
    
    // 🔥 NOUVEAU : Route par défaut selon le rôle
    getDefaultRoute
  }
})