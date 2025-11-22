/**
 * Store Pinia pour la gestion des catégories
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

export const useCategoriesStore = defineStore('categories', () => {
  // State
  const categories = ref([])
  const currentCategory = ref(null)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  const isLoading = ref(false)
  const error = ref(null)

  // Filtres
  const filters = ref({
    search: ''
  })

  // Getters
  const hasCategories = computed(() => categories.value.length > 0)
  const categoriesCount = computed(() => categories.value.length)
  const sortedCategories = computed(() => {
    return [...categories.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  // Options pour select
  const categoryOptions = computed(() => {
    return sortedCategories.value.map(cat => ({
      label: cat.name,
      value: cat.id,
      color: cat.color
    }))
  })

  // Actions

  /**
   * Récupérer la liste des catégories
   */
  async function fetchCategories(options = {}) {
    isLoading.value = true
    error.value = null

    const params = {
      page: options.page || page.value,
      page_size: options.page_size || pageSize.value,
      ...filters.value
    }

    // Supprimer les paramètres vides
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === undefined || params[key] === '') {
        delete params[key]
      }
    })

    try {
      const token = localStorage.getItem('access_token')
      const response = await axios.get(`${API_BASE_URL}/categories`, {
        params,
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = response.data

      categories.value = data.items || []
      total.value = data.total || 0
      totalPages.value = data.total_pages || 0
      page.value = data.page || 1
      pageSize.value = data.page_size || 20

      console.log('✅ Categories loaded:', categories.value.length)
      return categories.value
    } catch (err) {
      console.error('❌ Error loading categories:', err)
      error.value = err.response?.data?.detail || 'Erreur lors de la récupération des catégories'
      ElMessage.error(error.value)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Récupérer une catégorie par ID
   */
  async function fetchCategoryById(categoryId) {
    isLoading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('access_token')
      const response = await axios.get(`${API_BASE_URL}/categories/${categoryId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      currentCategory.value = response.data
      console.log('✅ Category loaded:', currentCategory.value.name)
      return currentCategory.value
    } catch (err) {
      console.error('❌ Error loading category:', err)
      error.value = err.response?.data?.detail || 'Erreur lors de la récupération de la catégorie'
      ElMessage.error(error.value)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Créer une nouvelle catégorie
   */
  async function createCategory(categoryData) {
    isLoading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('access_token')
      const response = await axios.post(
        `${API_BASE_URL}/categories`,
        categoryData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      const newCategory = response.data

      // Ajouter à la liste locale
      categories.value.push(newCategory)
      total.value++

      ElMessage.success('Catégorie créée avec succès')
      console.log('✅ Category created:', newCategory.name)
      
      return newCategory
    } catch (err) {
      console.error('❌ Error creating category:', err)
      const errorMessage = err.response?.data?.detail || 'Erreur lors de la création de la catégorie'
      error.value = errorMessage
      
      // Afficher le message d'erreur
      if (Array.isArray(err.response?.data?.detail)) {
        // Erreur de validation Pydantic
        const validationErrors = err.response.data.detail
        const firstError = validationErrors[0]
        ElMessage.error(`${firstError.loc[1]}: ${firstError.msg}`)
      } else {
        ElMessage.error(errorMessage)
      }
      
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Mettre à jour une catégorie
   */
  async function updateCategory(categoryId, categoryData) {
    isLoading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('access_token')
      const response = await axios.put(
        `${API_BASE_URL}/categories/${categoryId}`,
        categoryData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      const updatedCategory = response.data

      // Mettre à jour dans la liste locale
      const index = categories.value.findIndex(cat => cat.id === categoryId)
      if (index !== -1) {
        categories.value[index] = updatedCategory
      }

      // Mettre à jour la catégorie courante si c'est celle-ci
      if (currentCategory.value?.id === categoryId) {
        currentCategory.value = updatedCategory
      }

      ElMessage.success('Catégorie modifiée avec succès')
      console.log('✅ Category updated:', updatedCategory.name)
      
      return updatedCategory
    } catch (err) {
      console.error('❌ Error updating category:', err)
      const errorMessage = err.response?.data?.detail || 'Erreur lors de la modification de la catégorie'
      error.value = errorMessage
      
      // Afficher le message d'erreur
      if (Array.isArray(err.response?.data?.detail)) {
        // Erreur de validation Pydantic
        const validationErrors = err.response.data.detail
        const firstError = validationErrors[0]
        ElMessage.error(`${firstError.loc[1]}: ${firstError.msg}`)
      } else {
        ElMessage.error(errorMessage)
      }
      
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Supprimer une catégorie
   */
  async function deleteCategory(categoryId) {
    isLoading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('access_token')
      await axios.delete(`${API_BASE_URL}/categories/${categoryId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      // Retirer de la liste locale
      categories.value = categories.value.filter(cat => cat.id !== categoryId)
      total.value--

      // Réinitialiser la catégorie courante si c'est celle-ci
      if (currentCategory.value?.id === categoryId) {
        currentCategory.value = null
      }

      ElMessage.success('Catégorie supprimée avec succès')
      console.log('✅ Category deleted:', categoryId)
      
      return true
    } catch (err) {
      console.error('❌ Error deleting category:', err)
      error.value = err.response?.data?.detail || 'Erreur lors de la suppression de la catégorie'
      ElMessage.error(error.value)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Rechercher des catégories
   */
  function searchCategories(searchTerm) {
    filters.value.search = searchTerm
    page.value = 1 // Réinitialiser la pagination
    return fetchCategories()
  }

  /**
   * Réinitialiser les filtres
   */
  function resetFilters() {
    filters.value = {
      search: ''
    }
    page.value = 1
  }

  /**
   * Changer de page
   */
  function changePage(newPage) {
    page.value = newPage
    return fetchCategories()
  }

  /**
   * Changer la taille de page
   */
  function changePageSize(newPageSize) {
    pageSize.value = newPageSize
    page.value = 1 // Réinitialiser à la première page
    return fetchCategories()
  }

  /**
   * Rafraîchir les catégories
   */
  function refreshCategories() {
    return fetchCategories()
  }

  return {
    // State
    categories,
    currentCategory,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    error,
    filters,

    // Getters
    hasCategories,
    categoriesCount,
    sortedCategories,
    categoryOptions,

    // Actions
    fetchCategories,
    fetchCategoryById,
    createCategory,
    updateCategory,
    deleteCategory,
    searchCategories,
    resetFilters,
    changePage,
    changePageSize,
    refreshCategories
  }
})