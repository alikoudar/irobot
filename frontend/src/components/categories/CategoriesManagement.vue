<template>
  <div class="categories-management">
    <!-- En-tête -->
    <div class="page-header">
      <div class="header-left">
        <h1>
          <el-icon><Folder /></el-icon>
          Gestion des Catégories
        </h1>
        <p class="header-subtitle">
          Gérer les catégories de documents
        </p>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          Nouvelle catégorie
        </el-button>
      </div>
    </div>

    <!-- Filtres et recherche -->
    <el-card class="filters-card" shadow="never">
      <el-form :inline="true" @submit.prevent="handleSearch">
        <el-form-item>
          <el-input
            v-model="searchQuery"
            placeholder="Rechercher une catégorie..."
            :prefix-icon="Search"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
            style="width: 300px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            Rechercher
          </el-button>
        </el-form-item>
        <el-form-item>
          <el-button :icon="RefreshRight" @click="handleRefresh">
            Actualiser
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Statistiques -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
  <el-col :xs="24" :sm="8">
    <StatCard
      title="Total catégories"
      :value="categoriesStore.total"
      :icon="Folder"
      icon-color="#3498db"
    />
  </el-col>
  
  <el-col :xs="24" :sm="8">
    <StatCard
      title="Avec documents"
      :value="categoriesWithDocs"
      :icon="Document"
      icon-color="#67C23A"
    />
  </el-col>
  
  <el-col :xs="24" :sm="8">
    <StatCard
      title="Sans documents"
      :value="categoriesWithoutDocs"
      :icon="FolderOpened"
      icon-color="#F56C6C"
    />
  </el-col>
</el-row>

    <!-- Table des catégories -->
    <el-card class="table-card" shadow="never">
      <el-table
        v-loading="categoriesStore.isLoading"
        :data="categoriesStore.categories"
        stripe
        style="width: 100%"
      >
        <!-- Couleur -->
        <el-table-column label="Couleur" width="80" align="center">
          <template #default="{ row }">
            <div
              class="color-badge"
              :style="{ backgroundColor: row.color || '#CCCCCC' }"
            />
          </template>
        </el-table-column>

        <!-- Nom -->
        <el-table-column prop="name" label="Nom" min-width="200">
          <template #default="{ row }">
            <div class="category-name">
              <strong>{{ row.name }}</strong>
            </div>
          </template>
        </el-table-column>

        <!-- Description -->
        <el-table-column prop="description" label="Description" min-width="250">
          <template #default="{ row }">
            <span class="description-text">{{ row.description || 'Aucune description' }}</span>
          </template>
        </el-table-column>

        <!-- Documents -->
        <el-table-column label="Documents" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.document_count > 0 ? 'success' : 'info'">
              {{ row.document_count || 0 }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- Date création -->
        <el-table-column label="Créé le" width="150">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <!-- Actions -->
        <el-table-column label="Actions" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                size="small"
                :icon="Edit"
                @click="openEditDialog(row)"
              />
              <el-button
                size="small"
                type="danger"
                :icon="Delete"
                @click="handleDelete(row)"
              />
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="categoriesStore.page"
          v-model:page-size="categoriesStore.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="categoriesStore.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- Dialog Créer/Modifier -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditMode ? 'Modifier la catégorie' : 'Nouvelle catégorie'"
      width="600px"
      :close-on-click-modal="false"
      @closed="handleDialogClosed"
    >
      <CategoryForm
        ref="categoryFormRef"
        :category="selectedCategory"
        :is-loading="isSubmitting"
        @submit="handleSubmit"
        @cancel="dialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCategoriesStore } from '@/stores/categories'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import {
  Folder,
  FolderOpened,
  Document,
  Plus,
  Search,
  RefreshRight,
  Edit,
  Delete
} from '@element-plus/icons-vue'
import CategoryForm from '@/components/forms/CategoryForm.vue'
import StatCard from '@/components/common/StatCard.vue'


// Stores
const categoriesStore = useCategoriesStore()
const authStore = useAuthStore()

// Refs
const searchQuery = ref('')
const dialogVisible = ref(false)
const selectedCategory = ref(null)
const isSubmitting = ref(false)
const categoryFormRef = ref(null)

// Computed
const isEditMode = computed(() => !!selectedCategory.value)

const categoriesWithDocs = computed(() => {
  return categoriesStore.categories.filter(cat => cat.document_count > 0).length
})

const categoriesWithoutDocs = computed(() => {
  return categoriesStore.categories.filter(cat => cat.document_count === 0).length
})

// Lifecycle
onMounted(async () => {
  await categoriesStore.fetchCategories()
})

// Méthodes

/**
 * Ouvrir le dialog de création
 */
function openCreateDialog() {
  selectedCategory.value = null
  dialogVisible.value = true
}

/**
 * Ouvrir le dialog d'édition
 */
function openEditDialog(category) {
  selectedCategory.value = { ...category }
  dialogVisible.value = true
}

/**
 * Gérer la fermeture du dialog
 */
function handleDialogClosed() {
  selectedCategory.value = null
  categoryFormRef.value?.resetForm()
}

/**
 * Gérer la soumission du formulaire
 */
async function handleSubmit(formData) {
  isSubmitting.value = true

  try {
    if (isEditMode.value) {
      await categoriesStore.updateCategory(selectedCategory.value.id, formData)
    } else {
      await categoriesStore.createCategory(formData)
    }

    dialogVisible.value = false
    await categoriesStore.fetchCategories()
  } catch (error) {
    console.error('Error submitting form:', error)
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Gérer la suppression
 */
async function handleDelete(category) {
  try {
    await ElMessageBox.confirm(
      `Êtes-vous sûr de vouloir supprimer la catégorie "${category.name}" ?`,
      'Confirmation',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    await categoriesStore.deleteCategory(category.id)
    await categoriesStore.fetchCategories()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Error deleting category:', error)
    }
  }
}

/**
 * Gérer la recherche
 */
async function handleSearch() {
  await categoriesStore.searchCategories(searchQuery.value)
}

/**
 * Gérer le rafraîchissement
 */
async function handleRefresh() {
  searchQuery.value = ''
  categoriesStore.resetFilters()
  await categoriesStore.refreshCategories()
}

/**
 * Gérer le changement de page
 */
async function handlePageChange(newPage) {
  await categoriesStore.changePage(newPage)
}

/**
 * Gérer le changement de taille de page
 */
async function handleSizeChange(newSize) {
  await categoriesStore.changePageSize(newSize)
}

/**
 * Formater une date
 */
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}
</script>

<style scoped lang="scss">
.categories-management {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;

  .header-left {
    h1 {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 0 0 8px 0;
      font-size: 24px;
      color: var(--el-text-color-primary);

      .el-icon {
        color: var(--el-color-primary);
        font-size: 28px;
      }
    }

    .header-subtitle {
      margin: 0;
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }
  }
}

.filters-card {
  margin-bottom: 16px;
}

.stats-row {
  margin-bottom: 16px;
}

.table-card {
  .color-badge {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    margin: 0 auto;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.3);
  }

  .category-name {
    strong {
      color: var(--el-text-color-primary);
    }
  }

  .description-text {
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-lighter);
  }
}
</style>