/**
 * Store Pinia pour la gestion des utilisateurs (admin)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usersService } from '../services/api/users'
import { ElMessage } from 'element-plus'

export const useUsersStore = defineStore('users', () => {
  // State
  const users = ref([])
  const currentUser = ref(null)
  const stats = ref({
    total: 0,
    active: 0,
    inactive: 0,
    recent_connections: 0
  })
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  const isLoading = ref(false)
  const error = ref(null)

  // Filtres
  const filters = ref({
    search: '',
    role: null,
    is_active: null
  })

  // Getters
  const hasUsers = computed(() => users.value.length > 0)
  const usersCount = computed(() => users.value.length)
  const activeUsersCount = computed(() => users.value.filter(u => u.is_active).length)
  const inactiveUsersCount = computed(() => users.value.filter(u => !u.is_active).length)

  // Actions

  /**
   * Récupérer la liste des utilisateurs
   */
  async function fetchUsers(options = {}) {
    isLoading.value = true
    error.value = null

    const params = {
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value,
      ...filters.value,
      ...options
    }

    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === undefined || params[key] === '') {
        delete params[key]
      }
    })

    try {
      const data = await usersService.getUsers(params)

      users.value = data.users || []
      total.value = data.total || 0
      totalPages.value = data.total_pages || 0
      page.value = data.page || 1
      pageSize.value = data.page_size || 20

      console.log('✅ Users loaded:', users.value.length)
      console.log('✅ Total users:', total.value)
      
    } catch (err) {
      console.error('❌ Error loading users:', err)
      error.value = err.response?.data?.detail || 'Erreur lors de la récupération des utilisateurs'
      ElMessage.error(error.value)
      users.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Créer un nouvel utilisateur
   * 🔥 AMÉLIORATION : Messages d'erreur explicites pour validation email
   */
  async function createUser(userData) {
    isLoading.value = true
    error.value = null

    try {
      const newUser = await usersService.createUser(userData)
      users.value.unshift(newUser)
      total.value++

      ElMessage.success('Utilisateur créé avec succès')
      return true
    } catch (err) {
      // 🔥 NOUVEAU : Détection spécifique erreur validation email
      const errorDetail = err.response?.data?.detail
      
      if (typeof errorDetail === 'string') {
        // Erreur simple (string)
        if (errorDetail.includes('@beac.int') || errorDetail.includes('email') || errorDetail.includes('domaine')) {
          error.value = '❌ L\'adresse email doit appartenir au domaine @beac.int (ex: prenom.nom@beac.int)'
        } else {
          error.value = errorDetail
        }
      } else if (Array.isArray(errorDetail)) {
        // Erreur de validation Pydantic (array)
        const emailError = errorDetail.find(e => 
          e.loc && e.loc.includes('email') && 
          (e.msg.includes('@beac.int') || e.msg.includes('domaine'))
        )
        
        if (emailError) {
          error.value = '❌ L\'adresse email doit appartenir au domaine @beac.int (ex: prenom.nom@beac.int)'
        } else {
          error.value = errorDetail[0]?.msg || 'Erreur lors de la création de l\'utilisateur'
        }
      } else {
        error.value = 'Erreur lors de la création de l\'utilisateur'
      }
      
      ElMessage.error({
        message: error.value,
        duration: 5000,
        showClose: true
      })
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Récupérer les détails d'un utilisateur
   */
  async function fetchUser(userId) {
    isLoading.value = true
    error.value = null

    try {
      const user = await usersService.getUser(userId)
      currentUser.value = user
      return user
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors de la récupération de l\'utilisateur'
      ElMessage.error(error.value)
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Mettre à jour un utilisateur
   * 🔥 AMÉLIORATION : Messages d'erreur explicites pour validation email
   */
  async function updateUser(userId, userData) {
    isLoading.value = true
    error.value = null

    try {
      const updatedUser = await usersService.updateUser(userId, userData)

      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value[index] = updatedUser
      }

      if (currentUser.value?.id === userId) {
        currentUser.value = updatedUser
      }

      ElMessage.success('Utilisateur mis à jour avec succès')
      return true
    } catch (err) {
      // 🔥 NOUVEAU : Détection spécifique erreur validation email
      const errorDetail = err.response?.data?.detail
      
      if (typeof errorDetail === 'string') {
        if (errorDetail.includes('@beac.int') || errorDetail.includes('email') || errorDetail.includes('domaine')) {
          error.value = '❌ L\'adresse email doit appartenir au domaine @beac.int (ex: prenom.nom@beac.int)'
        } else {
          error.value = errorDetail
        }
      } else if (Array.isArray(errorDetail)) {
        const emailError = errorDetail.find(e => 
          e.loc && e.loc.includes('email') && 
          (e.msg.includes('@beac.int') || e.msg.includes('domaine'))
        )
        
        if (emailError) {
          error.value = '❌ L\'adresse email doit appartenir au domaine @beac.int (ex: prenom.nom@beac.int)'
        } else {
          error.value = errorDetail[0]?.msg || 'Erreur lors de la mise à jour de l\'utilisateur'
        }
      } else {
        error.value = 'Erreur lors de la mise à jour de l\'utilisateur'
      }
      
      ElMessage.error({
        message: error.value,
        duration: 5000,
        showClose: true
      })
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Supprimer un utilisateur
   * 🔥 AMÉLIORATION : Message explicite pour auto-suppression
   */
  async function deleteUser(userId) {
    isLoading.value = true
    error.value = null

    try {
      await usersService.deleteUser(userId)
      users.value = users.value.filter(u => u.id !== userId)
      total.value--

      ElMessage.success('Utilisateur supprimé avec succès')
      return true
    } catch (err) {
      // 🔥 NOUVEAU : Détection spécifique auto-suppression
      const errorDetail = err.response?.data?.detail || ''
      
      if (errorDetail.includes('propre compte') || errorDetail.includes('auto-suppression') || errorDetail.includes('yourself')) {
        error.value = '❌ Vous ne pouvez pas supprimer votre propre compte. Veuillez demander à un autre administrateur de le faire.'
      } else if (errorDetail.includes('dernier administrateur')) {
        error.value = '❌ Impossible de supprimer le dernier administrateur actif. Il doit toujours y avoir au moins un administrateur.'
      } else {
        error.value = errorDetail || 'Erreur lors de la suppression de l\'utilisateur'
      }
      
      ElMessage.error({
        message: error.value,
        duration: 5000,
        showClose: true
      })
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Télécharger le template Excel
   */
  async function downloadTemplate() {
    isLoading.value = true
    error.value = null

    try {
      const blob = await usersService.downloadTemplate()

      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'template_import_utilisateurs.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      ElMessage.success('Template téléchargé avec succès')
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors du téléchargement du template'
      ElMessage.error(error.value)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Importer des utilisateurs depuis Excel
   * 🔥 AMÉLIORATION : Messages détaillés pour erreurs validation
   */
  async function importExcel(file) {
    isLoading.value = true
    error.value = null

    try {
      const result = await usersService.importExcel(file)

      await fetchUsers()
      await fetchStats()

      if (result.error_count === 0) {
        ElMessage.success(`${result.success_count} utilisateur(s) importé(s) avec succès`)
      } else {
        // 🔥 NOUVEAU : Afficher détails des erreurs
        const hasEmailErrors = result.errors?.some(e => 
          e.error && (e.error.includes('@beac.int') || e.error.includes('email') || e.error.includes('domaine'))
        )
        
        if (hasEmailErrors) {
          ElMessage.warning({
            message: `Import terminé : ${result.success_count} succès, ${result.error_count} erreur(s).\n⚠️ Certains emails ne sont pas du domaine @beac.int`,
            duration: 7000,
            showClose: true,
            dangerouslyUseHTMLString: false
          })
        } else {
          ElMessage.warning(
            `Import terminé : ${result.success_count} succès, ${result.error_count} erreur(s)`
          )
        }
        
        // Afficher les erreurs dans la console pour debug
        if (result.errors && result.errors.length > 0) {
          console.warn('📋 Erreurs d\'import détaillées:', result.errors)
        }
      }

      return result
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors de l\'import Excel'
      ElMessage.error({
        message: error.value,
        duration: 5000,
        showClose: true
      })
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Réinitialiser le mot de passe d'un utilisateur
   */
  async function resetPassword(userId, newPassword, forceChange = true) {
    isLoading.value = true
    error.value = null

    try {
      await usersService.resetPassword(userId, newPassword, forceChange)

      ElMessage.success('Mot de passe réinitialisé avec succès')
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erreur lors de la réinitialisation du mot de passe'
      ElMessage.error(error.value)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Récupérer les statistiques des utilisateurs
   * CORRECTION : Mapper correctement les noms de propriétés de l'API
   */
  async function fetchStats() {
    try {
      const data = await usersService.getStats()
      
      // L'API retourne : total_users, active_users, inactive_users, recent_logins
      // On mappe vers : total, active, inactive, recent_connections
      stats.value = {
        total: data.total_users || 0,
        active: data.active_users || 0,
        inactive: data.inactive_users || 0,
        recent_connections: data.recent_logins || 0
      }
      
      console.log('✅ Stats loaded from API:', stats.value)
      console.log('📊 API Response:', data)
      return true
    } catch (err) {
      console.error('❌ Error loading stats:', err)
      
      // Fallback : calculer localement
      try {
        console.warn('⚠️ Calculating stats locally...')
        const allUsersData = await usersService.getUsers({ skip: 0, limit: 1000 })
        const allUsers = allUsersData.users || []
        
        const active = allUsers.filter(u => u.is_active).length
        const inactive = allUsers.filter(u => !u.is_active).length
        
        const sevenDaysAgo = new Date()
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
        const recentConnections = allUsers.filter(u => {
          if (!u.last_login) return false
          const lastLogin = new Date(u.last_login)
          return lastLogin >= sevenDaysAgo
        }).length
        
        stats.value = {
          total: allUsersData.total || allUsers.length,
          active: active,
          inactive: inactive,
          recent_connections: recentConnections
        }
        
        console.log('✅ Stats calculated locally:', stats.value)
        return true
      } catch (fetchErr) {
        console.error('❌ Error calculating stats:', fetchErr)
        stats.value = {
          total: total.value || 0,
          active: 0,
          inactive: 0,
          recent_connections: 0
        }
        return false
      }
    }
  }

  /**
   * Changer de page
   */
  async function changePage(newPage) {
    page.value = newPage
    await fetchUsers()
  }

  /**
   * Changer la taille de page
   */
  async function changePageSize(newSize) {
    pageSize.value = newSize
    page.value = 1
    await fetchUsers()
  }

  /**
   * Appliquer les filtres
   */
  async function applyFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
    await fetchUsers()
  }

  /**
   * Réinitialiser les filtres
   */
  async function resetFilters() {
    filters.value = {
      search: '',
      role: null,
      is_active: null
    }
    page.value = 1
    await fetchUsers()
  }

  /**
   * Rechercher des utilisateurs
   */
  async function search(searchTerm) {
    filters.value.search = searchTerm
    page.value = 1
    await fetchUsers()
  }

  return {
    // State
    users,
    currentUser,
    stats,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    error,
    filters,

    // Getters
    hasUsers,
    usersCount,
    activeUsersCount,
    inactiveUsersCount,

    // Actions
    fetchUsers,
    createUser,
    fetchUser,
    updateUser,
    deleteUser,
    downloadTemplate,
    importExcel,
    resetPassword,
    fetchStats,
    changePage,
    changePageSize,
    applyFilters,
    resetFilters,
    search
  }
})