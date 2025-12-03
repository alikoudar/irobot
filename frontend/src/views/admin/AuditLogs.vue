<template>
  <div class="audit-logs-page">
    <!-- En-tête de page -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-icon">
          <el-icon :size="28"><List /></el-icon>
        </div>
        <div class="header-text">
          <h1>Logs d'Audit</h1>
          <p>Historique des actions système</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button 
          :icon="Refresh" 
          @click="handleRefresh"
          :loading="store.loading"
        >
          Actualiser
        </el-button>
      </div>
    </div>

    <!-- Cartes de statistiques -->
    <div class="stats-cards" v-loading="store.loadingStats">
      <div class="stat-card">
        <div class="stat-icon total">
          <el-icon :size="24"><List /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNumber(store.stats.total_logs) }}</span>
          <span class="stat-label">Total logs</span>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon today">
          <el-icon :size="24"><Sunny /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNumber(store.stats.logs_today) }}</span>
          <span class="stat-label">Aujourd'hui</span>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon week">
          <el-icon :size="24"><Calendar /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNumber(store.stats.logs_this_week) }}</span>
          <span class="stat-label">Cette semaine</span>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon month">
          <el-icon :size="24"><DataAnalysis /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNumber(store.stats.logs_this_month) }}</span>
          <span class="stat-label">Ce mois</span>
        </div>
      </div>
    </div>

    <!-- Filtres -->
    <el-card class="filters-card" shadow="never">
      <div class="filters-header">
        <span class="filters-title">
          <el-icon><Filter /></el-icon>
          Filtres
        </span>
        <el-button 
          v-if="store.hasActiveFilters"
          type="danger" 
          text 
          @click="handleResetFilters"
        >
          <el-icon><Close /></el-icon>
          Réinitialiser
        </el-button>
      </div>
      
      <div class="filters-content">
        <el-row :gutter="16">
          <!-- Filtre par action -->
          <el-col :xs="24" :sm="12" :md="6">
            <el-select
              v-model="localFilters.action"
              placeholder="Action"
              clearable
              filterable
              @change="handleFilterChange"
              style="width: 100%"
            >
              <el-option-group
                v-for="(actions, category) in store.actionsByCategory"
                :key="category"
                :label="getCategoryLabel(category)"
              >
                <el-option
                  v-for="action in actions"
                  :key="action.value"
                  :label="action.label"
                  :value="action.value"
                />
              </el-option-group>
            </el-select>
          </el-col>
          
          <!-- Filtre par type d'entité -->
          <el-col :xs="24" :sm="12" :md="6">
            <el-select
              v-model="localFilters.entity_type"
              placeholder="Type d'entité"
              clearable
              @change="handleFilterChange"
              style="width: 100%"
            >
              <el-option
                v-for="type in store.filterOptions.entity_types"
                :key="type.value"
                :label="`${type.icon} ${type.label}`"
                :value="type.value"
              />
            </el-select>
          </el-col>
          
          <!-- Filtre par période -->
          <el-col :xs="24" :sm="12" :md="6">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="→"
              start-placeholder="Début"
              end-placeholder="Fin"
              format="DD/MM/YYYY"
              value-format="YYYY-MM-DD"
              @change="handleDateChange"
              style="width: 100%"
              :shortcuts="dateShortcuts"
            />
          </el-col>
          
          <!-- Recherche -->
          <el-col :xs="24" :sm="12" :md="6">
            <el-input
              v-model="localFilters.search"
              placeholder="Rechercher dans les détails..."
              clearable
              @keyup.enter="handleFilterChange"
              @clear="handleFilterChange"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- Tableau des logs -->
    <el-card class="logs-table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <span class="table-title">
            Historique des actions
            <el-tag type="info" size="small" style="margin-left: 8px">
              {{ store.total }} résultat{{ store.total > 1 ? 's' : '' }}
            </el-tag>
          </span>
        </div>
      </template>
      
      <el-table
        :data="store.logs"
        v-loading="store.loading"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
        row-class-name="clickable-row"
      >
        <!-- Date/Heure -->
        <el-table-column
          prop="created_at"
          label="Date/Heure"
          width="170"
          sortable
        >
          <template #default="{ row }">
            <div class="datetime-cell">
              <span class="date">{{ formatDate(row.created_at) }}</span>
              <span class="time">{{ formatTime(row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>
        
        <!-- Utilisateur -->
        <el-table-column
          label="Utilisateur"
          min-width="180"
        >
          <template #default="{ row }">
            <div v-if="row.user" class="user-cell">
              <el-avatar :size="32" class="user-avatar">
                {{ getInitials(row.user) }}
              </el-avatar>
              <div class="user-info">
                <span class="user-name">{{ row.user.prenom }} {{ row.user.nom }}</span>
                <span class="user-matricule">{{ row.user.matricule }}</span>
              </div>
            </div>
            <span v-else class="no-user">Système</span>
          </template>
        </el-table-column>
        
        <!-- Action -->
        <el-table-column
          prop="action"
          label="Action"
          width="200"
        >
          <template #default="{ row }">
            <el-tag 
              :type="getActionTagType(row.action)"
              effect="light"
            >
              {{ getActionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- Type d'entité -->
        <el-table-column
          prop="entity_type"
          label="Entité"
          width="140"
        >
          <template #default="{ row }">
            <span class="entity-badge">
              {{ getEntityIcon(row.entity_type) }}
              {{ row.entity_type || '-' }}
            </span>
          </template>
        </el-table-column>
        
        <!-- Détails (résumé) -->
        <el-table-column
          label="Détails"
          min-width="250"
        >
          <template #default="{ row }">
            <span class="details-summary">
              {{ getDetailsSummary(row.details) }}
            </span>
          </template>
        </el-table-column>
        
        <!-- IP -->
        <el-table-column
          prop="ip_address"
          label="IP"
          width="130"
        >
          <template #default="{ row }">
            <el-tooltip 
              v-if="row.user_agent" 
              :content="row.user_agent" 
              placement="top"
            >
              <span class="ip-address">{{ row.ip_address || '-' }}</span>
            </el-tooltip>
            <span v-else class="ip-address">{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>
        
        <!-- Actions -->
        <el-table-column
          label=""
          width="60"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              text
              size="small"
              @click.stop="showLogDetails(row)"
            >
              <el-icon><View /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- Pagination -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="store.page"
          v-model:page-size="store.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="store.total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- Modal détails du log -->
    <el-dialog
      v-model="detailsDialogVisible"
      title="Détails du log"
      width="600px"
      destroy-on-close
    >
      <div v-if="selectedLogDetails" class="log-details">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="ID">
            <code>{{ selectedLogDetails.id }}</code>
          </el-descriptions-item>
          
          <el-descriptions-item label="Date/Heure">
            {{ formatDateTime(selectedLogDetails.created_at) }}
          </el-descriptions-item>
          
          <el-descriptions-item label="Utilisateur">
            <template v-if="selectedLogDetails.user">
              {{ selectedLogDetails.user.prenom }} {{ selectedLogDetails.user.nom }}
              ({{ selectedLogDetails.user.matricule }})
            </template>
            <template v-else>Système</template>
          </el-descriptions-item>
          
          <el-descriptions-item label="Action">
            <el-tag :type="getActionTagType(selectedLogDetails.action)">
              {{ getActionLabel(selectedLogDetails.action) }}
            </el-tag>
          </el-descriptions-item>
          
          <el-descriptions-item label="Type d'entité">
            {{ getEntityIcon(selectedLogDetails.entity_type) }}
            {{ selectedLogDetails.entity_type || '-' }}
          </el-descriptions-item>
          
          <el-descriptions-item label="ID Entité">
            <code v-if="selectedLogDetails.entity_id">
              {{ selectedLogDetails.entity_id }}
            </code>
            <span v-else>-</span>
          </el-descriptions-item>
          
          <el-descriptions-item label="Adresse IP">
            {{ selectedLogDetails.ip_address || '-' }}
          </el-descriptions-item>
          
          <el-descriptions-item label="User Agent">
            <div class="user-agent-text">
              {{ selectedLogDetails.user_agent || '-' }}
            </div>
          </el-descriptions-item>
        </el-descriptions>
        
        <!-- Détails JSON -->
        <div v-if="selectedLogDetails.details" class="json-details">
          <h4>Détails complets</h4>
          <el-scrollbar max-height="300px">
            <pre class="json-content">{{ JSON.stringify(selectedLogDetails.details, null, 2) }}</pre>
          </el-scrollbar>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useAuditLogsStore } from '@/stores/auditLogs'
import { 
  List, 
  Sunny, 
  Calendar, 
  DataAnalysis,
  Filter,
  Search,
  Refresh,
  View,
  Close
} from '@element-plus/icons-vue'

// Store
const store = useAuditLogsStore()

// État local
const detailsDialogVisible = ref(false)
const selectedLogDetails = ref(null)

// Filtres locaux (pour éviter les appels API à chaque frappe)
const localFilters = reactive({
  action: null,
  entity_type: null,
  search: ''
})

// Plage de dates
const dateRange = ref(null)

// Raccourcis de dates
const dateShortcuts = [
  {
    text: 'Aujourd\'hui',
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
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
      return [start, now]
    }
  }
]

// Labels des catégories
const categoryLabels = {
  AUTH: 'Authentification',
  USER: 'Utilisateurs',
  DOCUMENT: 'Documents',
  CATEGORY: 'Catégories',
  CONFIG: 'Configuration'
}

// Labels des actions
const actionLabels = {
  LOGIN_SUCCESS: 'Connexion réussie',
  LOGIN_FAILED: 'Connexion échouée',
  PROFILE_UPDATE: 'Mise à jour profil',
  PASSWORD_RESET_REQUEST: 'Demande réinit. MDP',
  CATEGORY_CREATED: 'Catégorie créée',
  CATEGORY_UPDATED: 'Catégorie modifiée',
  CATEGORY_DELETED: 'Catégorie supprimée',
  DOCUMENT_CREATED: 'Document créé',
  RETRY: 'Réessai traitement',
  USER_CREATED: 'Utilisateur créé',
  USER_UPDATED: 'Utilisateur modifié',
  USER_DELETED: 'Utilisateur supprimé',
  PASSWORD_CHANGED: 'Mot de passe changé',
  PASSWORD_RESET: 'Mot de passe réinitialisé',
  USERS_IMPORTED: 'Utilisateurs importés',
  CONFIG_UPDATE: 'Configuration modifiée'
}

// Icônes des entités
const entityIcons = {
  AUTH: '🔐',
  USER: '👤',
  DOCUMENT: '📄',
  CATEGORY: '📁',
  CONFIG: '⚙️'
}

// ===========================================================================
// MÉTHODES
// ===========================================================================

/**
 * Initialisation au montage
 */
onMounted(async () => {
  await store.initialize()
})

/**
 * Gère le changement de filtres
 */
function handleFilterChange() {
  store.updateFilters({
    action: localFilters.action,
    entity_type: localFilters.entity_type,
    search: localFilters.search
  })
}

/**
 * Gère le changement de dates
 */
function handleDateChange(value) {
  if (value && value.length === 2) {
    store.updateFilters({
      start_date: value[0],
      end_date: value[1]
    })
  } else {
    store.updateFilters({
      start_date: null,
      end_date: null
    })
  }
}

/**
 * Réinitialise les filtres
 */
function handleResetFilters() {
  localFilters.action = null
  localFilters.entity_type = null
  localFilters.search = ''
  dateRange.value = null
  store.resetFilters()
}

/**
 * Actualise les données
 */
async function handleRefresh() {
  await Promise.all([
    store.fetchStats(),
    store.fetchLogs()
  ])
}

/**
 * Gère le changement de page
 */
function handlePageChange(newPage) {
  store.changePage(newPage)
}

/**
 * Gère le changement de taille de page
 */
function handlePageSizeChange(newSize) {
  store.changePageSize(newSize)
}

/**
 * Gère le clic sur une ligne
 */
function handleRowClick(row) {
  showLogDetails(row)
}

/**
 * Affiche les détails d'un log
 */
function showLogDetails(log) {
  selectedLogDetails.value = log
  detailsDialogVisible.value = true
}

// ===========================================================================
// FORMATAGE
// ===========================================================================

function formatNumber(num) {
  return num?.toLocaleString('fr-FR') || '0'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('fr-FR')
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('fr-FR')
}

function getInitials(user) {
  if (!user) return '?'
  return `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase()
}

function getCategoryLabel(category) {
  return categoryLabels[category] || category
}

function getActionLabel(action) {
  return actionLabels[action] || action
}

function getEntityIcon(entityType) {
  return entityIcons[entityType] || '📋'
}

function getActionTagType(action) {
  if (!action) return 'info'
  
  if (action.includes('SUCCESS') || action.includes('CREATED')) return 'success'
  if (action.includes('FAILED') || action.includes('DELETED')) return 'danger'
  if (action.includes('UPDATED') || action.includes('CHANGED') || action.includes('UPDATE')) return 'warning'
  if (action.includes('IMPORTED')) return 'success'
  
  return 'info'
}

function getDetailsSummary(details) {
  if (!details) return '-'
  
  // Extraire les infos importantes
  const parts = []
  
  if (details.message) {
    parts.push(details.message)
  } else {
    if (details.matricule) parts.push(`Matricule: ${details.matricule}`)
    if (details.email) parts.push(`Email: ${details.email}`)
    if (details.role) parts.push(`Rôle: ${details.role}`)
    if (details.key) parts.push(`Clé: ${details.key}`)
    if (details.name) parts.push(`Nom: ${details.name}`)
    if (details.filename) parts.push(`Fichier: ${details.filename}`)
  }
  
  return parts.join(' | ') || JSON.stringify(details).substring(0, 100) + '...'
}
</script>

<style scoped lang="scss">
// Variables
$primary-color: #005ca9;
$success-color: #67c23a;
$warning-color: #e6a23c;
$danger-color: #f56c6c;
$info-color: #909399;

.audit-logs-page {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

// En-tête
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  .header-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  .header-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    background: linear-gradient(135deg, $primary-color, lighten($primary-color, 15%));
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }
  
  .header-text {
    h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: #303133;
    }
    
    p {
      margin: 4px 0 0;
      color: #909399;
      font-size: 14px;
    }
  }
}

// Cartes de statistiques
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s, box-shadow 0.2s;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }
  
  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    
    &.total { background: linear-gradient(135deg, $primary-color, lighten($primary-color, 15%)); }
    &.today { background: linear-gradient(135deg, $success-color, lighten($success-color, 15%)); }
    &.week { background: linear-gradient(135deg, $warning-color, lighten($warning-color, 15%)); }
    &.month { background: linear-gradient(135deg, #9c27b0, lighten(#9c27b0, 15%)); }
  }
  
  .stat-content {
    display: flex;
    flex-direction: column;
    
    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #303133;
    }
    
    .stat-label {
      font-size: 13px;
      color: #909399;
    }
  }
}

// Carte des filtres
.filters-card {
  margin-bottom: 24px;
  
  :deep(.el-card__body) {
    padding: 16px 20px;
  }
  
  .filters-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .filters-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .filters-content {
    .el-col {
      margin-bottom: 12px;
      
      @media (min-width: 768px) {
        margin-bottom: 0;
      }
    }
  }
}

// Tableau
.logs-table-card {
  :deep(.el-card__header) {
    padding: 16px 20px;
    border-bottom: 1px solid #ebeef5;
  }
  
  .table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .table-title {
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
    }
  }
}

.clickable-row {
  cursor: pointer;
  
  &:hover {
    background-color: #f5f7fa;
  }
}

.datetime-cell {
  display: flex;
  flex-direction: column;
  
  .date {
    font-weight: 500;
    color: #303133;
  }
  
  .time {
    font-size: 12px;
    color: #909399;
  }
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .user-avatar {
    background: $primary-color;
    color: white;
    font-size: 12px;
    font-weight: 600;
  }
  
  .user-info {
    display: flex;
    flex-direction: column;
    
    .user-name {
      font-weight: 500;
      color: #303133;
    }
    
    .user-matricule {
      font-size: 12px;
      color: #909399;
    }
  }
}

.no-user {
  color: #909399;
  font-style: italic;
}

.entity-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.details-summary {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
  display: block;
}

.ip-address {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

// Pagination
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
}

// Modal détails
.log-details {
  .json-details {
    margin-top: 20px;
    
    h4 {
      margin: 0 0 12px;
      font-size: 14px;
      font-weight: 600;
      color: #303133;
    }
    
    .json-content {
      background: #f5f7fa;
      border-radius: 8px;
      padding: 16px;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 12px;
      line-height: 1.6;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
  
  .user-agent-text {
    font-size: 12px;
    word-break: break-all;
    max-width: 400px;
  }
}

// Responsive
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>