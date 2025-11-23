<template>
  <div class="documents-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>Gestion des documents</h1>
        <p>Uploadez et gérez les documents de la base de connaissances</p>
      </div>
      <div class="header-actions">
        <el-button @click="refreshDocuments" :loading="documentsStore.isLoading">
          <el-icon><Refresh /></el-icon>
          Actualiser
        </el-button>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          Uploader des documents
        </el-button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon total-icon">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="stat-content">
          <p>Total documents</p>
          <h3>{{ documentsStore.total }}</h3>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon pending-icon">
          <el-icon :size="24"><Clock /></el-icon>
        </div>
        <div class="stat-content">
          <p>En traitement</p>
          <h3>{{ documentsStore.pendingDocuments.length }}</h3>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon success-icon">
          <el-icon :size="24"><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <p>Terminés</p>
          <h3>{{ documentsStore.completedDocuments.length }}</h3>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon error-icon">
          <el-icon :size="24"><CircleClose /></el-icon>
        </div>
        <div class="stat-content">
          <p>En erreur</p>
          <h3>{{ documentsStore.failedDocuments.length }}</h3>
        </div>
      </div>
    </div>

    <!-- Filtres -->
    <div class="filters-bar">
      <el-input
        v-model="searchTerm"
        placeholder="Rechercher un document..."
        prefix-icon="Search"
        clearable
        class="search-input"
        @input="handleSearch"
      />
      
      <el-select
        v-model="statusFilter"
        placeholder="Statut"
        clearable
        @change="handleFilterChange"
      >
        <el-option label="En attente" value="PENDING" />
        <el-option label="En cours" value="PROCESSING" />
        <el-option label="Terminé" value="COMPLETED" />
        <el-option label="Échec" value="FAILED" />
      </el-select>
      
      <el-select
        v-model="categoryFilter"
        placeholder="Catégorie"
        clearable
        filterable
        @change="handleFilterChange"
      >
        <el-option
          v-for="cat in documentsStore.categories"
          :key="cat.id"
          :label="cat.name"
          :value="cat.id"
        />
      </el-select>
      
      <!-- Filtre par type de fichier -->
      <el-select
        v-model="fileTypeFilter"
        placeholder="Type de fichier"
        clearable
        multiple
        collapse-tags
        collapse-tags-tooltip
        @change="handleFilterChange"
      >
        <el-option label="PDF" value="pdf">
          <el-icon class="option-icon"><DocumentCopy /></el-icon>
          <span>PDF</span>
        </el-option>
        <el-option label="Word (DOCX)" value="docx">
          <el-icon class="option-icon"><Document /></el-icon>
          <span>Word (DOCX)</span>
        </el-option>
        <el-option label="Excel (XLSX)" value="xlsx">
          <el-icon class="option-icon"><Grid /></el-icon>
          <span>Excel (XLSX)</span>
        </el-option>
        <el-option label="PowerPoint (PPTX)" value="pptx">
          <el-icon class="option-icon"><Tickets /></el-icon>
          <span>PowerPoint (PPTX)</span>
        </el-option>
        <el-option label="Images" value="image">
          <el-icon class="option-icon"><Picture /></el-icon>
          <span>Images (PNG, JPG)</span>
        </el-option>
        <el-option label="Texte" value="txt">
          <el-icon class="option-icon"><Document /></el-icon>
          <span>Texte (TXT, MD)</span>
        </el-option>
      </el-select>
      
      <!-- Filtre par plage de dates -->
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="à"
        start-placeholder="Date début"
        end-placeholder="Date fin"
        format="DD/MM/YYYY"
        value-format="YYYY-MM-DD"
        clearable
        :shortcuts="dateShortcuts"
        @change="handleFilterChange"
      />
      
      <el-button
        v-if="hasActiveFilters"
        text
        type="primary"
        @click="resetFilters"
      >
        Réinitialiser les filtres
      </el-button>
    </div>

    <!-- Table des documents -->
    <div class="documents-table-container">
      <el-table
        :data="documentsStore.documents"
        v-loading="documentsStore.isLoading"
        stripe
        class="documents-table"
        @row-click="handleRowClick"
      >
        <!-- Icône type -->
        <el-table-column width="60" align="center">
          <template #default="{ row }">
            <div class="file-type-icon" :class="row.file_extension">
              <el-icon :size="20">
                <component :is="getFileIcon(row.file_extension)" />
              </el-icon>
            </div>
          </template>
        </el-table-column>
        
        <!-- Nom du fichier -->
        <el-table-column label="Document" min-width="250">
          <template #default="{ row }">
            <div class="document-name">
              <span class="name">{{ row.original_filename }}</span>
              <span class="meta">
                {{ documentsStore.formatFileSize(row.file_size_bytes) }}
                <template v-if="row.page_count">
                  • {{ row.page_count }} pages
                </template>
              </span>
            </div>
          </template>
        </el-table-column>
        
        <!-- Catégorie -->
        <el-table-column label="Catégorie" width="180">
          <template #default="{ row }">
            <el-tag size="small" type="info">
              {{ getCategoryName(row.category_id) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- Statut -->
        <el-table-column label="Statut" width="160">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag
                :type="documentsStore.getStatusColor(row.status)"
                size="small"
              >
                <el-icon v-if="row.status === 'PROCESSING'" class="is-loading">
                  <Loading />
                </el-icon>
                {{ documentsStore.getStatusLabel(row.status) }}
              </el-tag>
              <span v-if="row.status === 'PROCESSING'" class="stage-hint">
                {{ documentsStore.getStageLabel(row.processing_stage) }}
              </span>
            </div>
          </template>
        </el-table-column>
        
        <!-- Chunks -->
        <el-table-column label="Chunks" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.total_chunks" class="chunk-count">
              {{ row.total_chunks }}
            </span>
            <span v-else class="no-data">-</span>
          </template>
        </el-table-column>
        
        <!-- Date -->
        <el-table-column label="Uploadé" width="140">
          <template #default="{ row }">
            <span class="date">{{ formatDate(row.uploaded_at) }}</span>
          </template>
        </el-table-column>
        
        <!-- Actions -->
        <el-table-column label="Actions" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <div class="actions-cell">
              <el-tooltip content="Voir les détails" placement="top">
                <el-button
                  text
                  size="small"
                  @click.stop="viewDocument(row)"
                >
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              
              <el-tooltip
                v-if="row.status === 'FAILED'"
                content="Relancer le traitement"
                placement="top"
              >
                <el-button
                  text
                  size="small"
                  type="warning"
                  @click.stop="retryDocument(row)"
                >
                  <el-icon><RefreshRight /></el-icon>
                </el-button>
              </el-tooltip>
              
              <el-tooltip content="Supprimer" placement="top">
                <el-button
                  text
                  size="small"
                  type="danger"
                  @click.stop="deleteDocument(row)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- Pagination -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="documentsStore.page"
          v-model:page-size="documentsStore.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="documentsStore.total"
          layout="sizes, prev, pager, next, total"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- Dialog Upload -->
    <el-dialog
      v-model="showUploadDialog"
      title="Uploader des documents"
      width="700px"
      :close-on-click-modal="!documentsStore.isUploading"
      :close-on-press-escape="!documentsStore.isUploading"
      :show-close="!documentsStore.isUploading"
    >
      <DocumentUpload
        :default-category="categoryFilter"
        @success="handleUploadSuccess"
        @cancel="showUploadDialog = false"
      />
    </el-dialog>

    <!-- Dialog Détails -->
    <el-dialog
      v-model="showDetailsDialog"
      title="Détails du document"
      width="600px"
    >
      <DocumentDetails
        v-if="selectedDocument"
        :document="selectedDocument"
        @retry="retryDocument"
        @delete="deleteDocument"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Upload,
  Refresh,
  Document,
  Clock,
  CircleCheck,
  CircleClose,
  Search,
  View,
  Delete,
  RefreshRight,
  Loading,
  DocumentCopy,
  Grid,
  PictureFilled,
  Tickets,
  Picture
} from '@element-plus/icons-vue'
import { useDocumentsStore } from '@/stores/documents'
import { ElMessageBox, ElMessage } from 'element-plus'
import DocumentUpload from '@/components/documents/DocumentUpload.vue'
import DocumentDetails from '@/components/documents/DocumentDetails.vue'

// Store
const documentsStore = useDocumentsStore()

// State
const showUploadDialog = ref(false)
const showDetailsDialog = ref(false)
const selectedDocument = ref(null)
const searchTerm = ref('')
const statusFilter = ref(null)
const categoryFilter = ref(null)
const fileTypeFilter = ref([])  // Filtre par type de fichier (multiple)
const dateRange = ref(null)     // Filtre par plage de dates [startDate, endDate]

// Raccourcis pour le date picker
const dateShortcuts = [
  {
    text: "Aujourd'hui",
    value: () => {
      const today = new Date()
      return [today, today]
    }
  },
  {
    text: '7 derniers jours',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return [start, end]
    }
  },
  {
    text: '30 derniers jours',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      return [start, end]
    }
  },
  {
    text: 'Ce mois',
    value: () => {
      const end = new Date()
      const start = new Date(end.getFullYear(), end.getMonth(), 1)
      return [start, end]
    }
  },
  {
    text: 'Mois dernier',
    value: () => {
      const end = new Date()
      end.setDate(0) // Dernier jour du mois précédent
      const start = new Date(end.getFullYear(), end.getMonth(), 1)
      return [start, end]
    }
  }
]

// Auto-refresh interval
let refreshInterval = null

// Computed
const hasActiveFilters = computed(() => {
  return searchTerm.value || 
         statusFilter.value || 
         categoryFilter.value || 
         fileTypeFilter.value.length > 0 || 
         dateRange.value
})

// Methods
const getFileIcon = (extension) => {
  const icons = {
    pdf: DocumentCopy,
    docx: Document,
    doc: Document,
    xlsx: Grid,
    xls: Grid,
    pptx: PictureFilled,
    ppt: PictureFilled,
    txt: Tickets,
    md: Tickets,
    png: Picture,
    jpg: Picture,
    jpeg: Picture,
    webp: Picture
  }
  return icons[extension?.toLowerCase()] || Document
}

const getCategoryName = (categoryId) => {
  const category = documentsStore.categories.find(c => c.id === categoryId)
  return category?.name || 'Non classé'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(dateString))
}

const refreshDocuments = () => {
  documentsStore.fetchDocuments()
}

const handleSearch = () => {
  documentsStore.search(searchTerm.value)
}

const handleFilterChange = () => {
  documentsStore.applyFilters({
    status: statusFilter.value,
    category_id: categoryFilter.value,
    file_types: fileTypeFilter.value.length > 0 ? fileTypeFilter.value : null,
    date_from: dateRange.value ? dateRange.value[0] : null,
    date_to: dateRange.value ? dateRange.value[1] : null
  })
}

const resetFilters = () => {
  searchTerm.value = ''
  statusFilter.value = null
  categoryFilter.value = null
  fileTypeFilter.value = []
  dateRange.value = null
  documentsStore.resetFilters()
}

const handlePageChange = (page) => {
  documentsStore.changePage(page)
}

const handleSizeChange = (size) => {
  documentsStore.changePageSize(size)
}

const handleRowClick = (row) => {
  viewDocument(row)
}

const viewDocument = (doc) => {
  selectedDocument.value = doc
  showDetailsDialog.value = true
}

const retryDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(
      `Relancer le traitement du document "${doc.original_filename}" ?`,
      'Confirmation',
      {
        confirmButtonText: 'Relancer',
        cancelButtonText: 'Annuler',
        type: 'warning'
      }
    )
    
    await documentsStore.retryDocument(doc.id)
    showDetailsDialog.value = false
    
  } catch (error) {
    // Utilisateur a annulé
  }
}

const deleteDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(
      `Supprimer définitivement le document "${doc.original_filename}" ?\n\nCette action supprimera également tous les chunks et données associées.`,
      'Confirmation de suppression',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'danger'
      }
    )
    
    await documentsStore.deleteDocument(doc.id)
    showDetailsDialog.value = false
    
  } catch (error) {
    // Utilisateur a annulé
  }
}

const handleUploadSuccess = (result) => {
  showUploadDialog.value = false
  
  // Rafraîchir après un court délai
  setTimeout(() => {
    documentsStore.fetchDocuments()
  }, 1000)
}

// Lifecycle
onMounted(async () => {
  // Charger les catégories et documents
  await Promise.all([
    documentsStore.fetchCategories(),
    documentsStore.fetchDocuments()
  ])
  
  // Auto-refresh toutes les 10 secondes pour les documents en traitement
  refreshInterval = setInterval(() => {
    if (documentsStore.pendingDocuments.length > 0) {
      documentsStore.fetchDocuments()
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  documentsStore.unsubscribeFromStatus()
})
</script>

<style scoped lang="scss">
.documents-page {
  padding: 24px;
  min-height: 100vh;
  background: var(--bg-color, #f5f7fa);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;

  h1 {
    font-size: 28px;
    font-weight: 700;
    margin: 0 0 4px 0;
    color: var(--text-primary, #1f2937);
  }

  p {
    color: var(--text-secondary, #6b7280);
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;

    &.total-icon {
      background: rgba(59, 130, 246, 0.1);
      color: #3b82f6;
    }

    &.pending-icon {
      background: rgba(245, 158, 11, 0.1);
      color: #f59e0b;
    }

    &.success-icon {
      background: rgba(16, 185, 129, 0.1);
      color: #10b981;
    }

    &.error-icon {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }
  }

  .stat-content {
    p {
      margin: 0;
      font-size: 14px;
      color: var(--text-secondary, #6b7280);
    }

    h3 {
      margin: 4px 0 0;
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary, #1f2937);
    }
  }
}

.filters-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;

  .search-input {
    width: 300px;
  }

  .el-select {
    width: 150px;
  }
}

.documents-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.documents-table {
  width: 100%;
  
  :deep(.el-table__row) {
    cursor: pointer;
  }
}

.file-type-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-light, #ecf5ff);
  color: var(--primary-color, #409eff);

  &.pdf {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  &.docx, &.doc {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }

  &.xlsx, &.xls {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
  }

  &.pptx, &.ppt {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
  }
}

.document-name {
  .name {
    display: block;
    font-weight: 500;
    color: var(--text-primary, #1f2937);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 250px;
  }

  .meta {
    font-size: 12px;
    color: var(--text-secondary, #6b7280);
  }
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .stage-hint {
    font-size: 11px;
    color: var(--text-muted, #9ca3af);
  }
}

.chunk-count {
  font-weight: 600;
  color: var(--primary-color, #409eff);
}

.no-data {
  color: var(--text-muted, #9ca3af);
}

.date {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
}

.actions-cell {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.pagination-container {
  padding: 16px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--border-color, #e5e7eb);
}

/* Style pour les icônes dans les options de select */
.option-icon {
  margin-right: 8px;
  vertical-align: middle;
}

/* Améliorer la barre de filtres pour les nouveaux éléments */
.filters-bar {
  :deep(.el-date-editor) {
    max-width: 260px;
  }
  
  :deep(.el-select--multiple .el-select__tags) {
    max-width: 150px;
  }
}
</style>
