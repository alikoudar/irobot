<template>
  <div class="users-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>Gestion des utilisateurs</h1>
        <p>Administrez les utilisateurs et leurs permissions</p>
      </div>
      <div class="header-actions">
        <el-button @click="handleDownloadTemplate" :loading="usersStore.isLoading">
          <el-icon><Download /></el-icon>
          Template Excel
        </el-button>
        <el-upload
          ref="uploadRef"
          action="#"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleImportExcel"
          accept=".xlsx,.xls"
        >
          <el-button :loading="usersStore.isLoading">
            <el-icon><Upload /></el-icon>
            Importer
          </el-button>
        </el-upload>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          Nouvel utilisateur
        </el-button>
      </div>
    </div>

    <!-- Stats Cards -->
    <!-- Stats Cards - Harmonisées avec animation -->
<el-row :gutter="20" style="margin-bottom: 20px;">
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Total utilisateurs"
      :value="usersStore.total || 0"
      :icon="User"
      icon-color="#3498db"
    >
      <template #extra>
        <div style="margin-top: 8px; color: #67C23A; font-size: 12px;">+12%</div>
      </template>
    </StatCard>
  </el-col>
  
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Actifs"
      :value="usersStore.stats?.active || 0"
      :icon="CircleCheck"
      icon-color="#67C23A"
    />
  </el-col>
  
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Inactifs"
      :value="usersStore.stats?.inactive || 0"
      :icon="CircleClose"
      icon-color="#F56C6C"
    />
  </el-col>
  
  <el-col :xs="24" :sm="12" :md="6">
    <StatCard
      title="Connexions (7j)"
      :value="usersStore.stats?.recent_connections || 0"
      :icon="Connection"
      icon-color="#E6A23C"
    >
      <template #extra>
        <div style="margin-top: 8px; color: #67C23A; font-size: 12px;">+8%</div>
      </template>
    </StatCard>
  </el-col>
</el-row>

    <!-- Filters -->
    <div class="filters-section">
      <el-input
        v-model="searchTerm"
        placeholder="Rechercher par matricule, nom, prénom ou email..."
        clearable
        @input="handleSearch"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select
        v-model="roleFilter"
        placeholder="Rôle"
        clearable
        @change="handleFilterChange"
        class="filter-select"
      >
        <el-option label="Administrateur" value="ADMIN" />
        <el-option label="Manager" value="MANAGER" />
        <el-option label="Utilisateur" value="USER" />
      </el-select>

      <el-select
        v-model="statusFilter"
        placeholder="Statut"
        clearable
        @change="handleFilterChange"
        class="filter-select"
      >
        <el-option label="Actif" :value="true" />
        <el-option label="Inactif" :value="false" />
      </el-select>
    </div>

    <!-- Table -->
    <div class="table-container">
      <el-table
        v-loading="usersStore.isLoading"
        :data="usersStore.users"
        style="width: 100%"
        class="users-table"
      >
        <el-table-column label="Utilisateur" min-width="250">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="36" class="user-avatar">
                {{ row.prenom?.charAt(0) }}{{ row.nom?.charAt(0) }}
              </el-avatar>
              <div class="user-info">
                <div class="user-name">{{ row.prenom }} {{ row.nom }}</div>
                <div class="user-email">{{ row.email }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="matricule" label="Matricule" width="140" />

        <el-table-column label="Rôle" width="150">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)">
              {{ getRoleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Statut" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? 'Actif' : 'Inactif' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Dernière connexion" width="180">
          <template #default="{ row }">
            <span v-if="row.last_login" class="last-login">
              <el-icon><Clock /></el-icon>
              {{ formatDate(row.last_login) }}
            </span>
            <span v-else class="never-connected">Jamais</span>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="Modifier" placement="top">
                <el-button link @click="handleEdit(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="Réinitialiser mot de passe" placement="top">
                <el-button link type="warning" @click="handleResetPassword(row)">
                  <el-icon><Key /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="Supprimer" placement="top">
                <el-button link type="danger" @click="handleDelete(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pagination -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="usersStore.page"
        v-model:page-size="usersStore.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="usersStore.total"
        layout="sizes, prev, pager, next, total"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- UserForm Dialog -->
    <UserForm
      v-model="showUserForm"
      :user="selectedUser"
      :loading="usersStore.isLoading"
      @submit="handleSubmitUser"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  Plus, Search, Edit, Delete, Key, User, CircleCheck, CircleClose, 
  Clock, Download, Upload, Connection
} from '@element-plus/icons-vue'
import { useUsersStore } from '@/stores/users'
import { useAuthStore } from '@/stores/auth'  // 🔥 NOUVEAU : Pour vérifier auto-suppression
import UserForm from '@/components/forms/UserForm.vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import StatCard from '@/components/common/StatCard.vue'

const usersStore = useUsersStore()
const authStore = useAuthStore()  // 🔥 NOUVEAU : Store auth pour vérifier identité
const uploadRef = ref(null)

const showUserForm = ref(false)
const selectedUser = ref(null)
const searchTerm = ref('')
const roleFilter = ref(null)
const statusFilter = ref(null)

const handleCreate = () => {
  selectedUser.value = null
  showUserForm.value = true
}

const handleEdit = (user) => {
  selectedUser.value = user
  showUserForm.value = true
}

const handleSubmitUser = async (userData) => {
  let success = false
  if (selectedUser.value) {
    success = await usersStore.updateUser(selectedUser.value.id, userData)
  } else {
    success = await usersStore.createUser(userData)
  }
  if (success) {
    showUserForm.value = false
    await usersStore.fetchStats()
  }
}

const handleDelete = async (user) => {
  try {
    // 🔥 NOUVEAU : Vérifier auto-suppression AVANT l'appel backend
    if (authStore.currentUser && user.id === authStore.currentUser.id) {
      ElMessage.warning({
        message: '❌ Vous ne pouvez pas supprimer votre propre compte. Veuillez demander à un autre administrateur de le faire.',
        duration: 5000,
        showClose: true
      })
      return  // Arrêter ici, ne pas appeler le backend
    }
    
    await ElMessageBox.confirm(
      `Êtes-vous sûr de vouloir supprimer l'utilisateur ${user.prenom} ${user.nom} ?`,
      'Confirmation de suppression',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    const success = await usersStore.deleteUser(user.id)
    if (success) {
      await usersStore.fetchStats()
    }
  } catch (error) {
    // Utilisateur a annulé
  }
}

const handleResetPassword = async (user) => {
  try {
    const { value: newPassword } = await ElMessageBox.prompt(
      `Entrez le nouveau mot de passe pour ${user.prenom} ${user.nom}`,
      'Réinitialiser le mot de passe',
      {
        confirmButtonText: 'Réinitialiser',
        cancelButtonText: 'Annuler',
        inputType: 'password',
        inputPlaceholder: 'Nouveau mot de passe',
        inputValidator: (value) => {
          if (!value) return 'Le mot de passe est requis'
          if (value.length < 8) return 'Le mot de passe doit contenir au moins 8 caractères'
          return true
        }
      }
    )
    
    if (newPassword) {
      const success = await usersStore.resetPassword(user.id, newPassword, true)
      if (success) {
        ElMessage.success('Mot de passe réinitialisé avec succès')
      }
    }
  } catch (error) {
    // Utilisateur a annulé
  }
}

const handleDownloadTemplate = async () => {
  await usersStore.downloadTemplate()
}

const handleImportExcel = async (file) => {
  if (!file) return
  
  try {
    await ElMessageBox.confirm(
      'Êtes-vous sûr de vouloir importer ce fichier Excel ? Les utilisateurs existants ne seront pas modifiés.',
      'Confirmation d\'import',
      {
        confirmButtonText: 'Importer',
        cancelButtonText: 'Annuler',
        type: 'info'
      }
    )
    
    const result = await usersStore.importExcel(file.raw)
    if (result) {
      // Réinitialiser l'upload
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
    }
  } catch (error) {
    // Utilisateur a annulé ou erreur
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
  }
}

const handleSearch = () => {
  usersStore.search(searchTerm.value)
}

const handleFilterChange = () => {
  usersStore.applyFilters({
    role: roleFilter.value,
    is_active: statusFilter.value
  })
}

const handlePageChange = (page) => {
  usersStore.changePage(page)
}

const handleSizeChange = (size) => {
  usersStore.changePageSize(size)
}

const getRoleLabel = (role) => {
  const labels = { ADMIN: 'Admin', MANAGER: 'Manager', USER: 'Utilisateur' }
  return labels[role] || role
}

const getRoleType = (role) => {
  const types = { ADMIN: 'danger', MANAGER: 'warning', USER: 'info' }
  return types[role] || 'info'
}

const formatDate = (dateString) => {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(dateString))
}

onMounted(async () => {
  await usersStore.fetchUsers()
  await usersStore.fetchStats()
})
</script>

<style scoped lang="scss">
.users-page {
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

.filters-section {
  background: var(--card-bg, white);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
  border: 1px solid var(--border-color, #e5e7eb);

  .search-input {
    flex: 1;
  }

  .filter-select {
    width: 160px;
  }
}

.table-container {
  background: var(--card-bg, white);
  border-radius: 12px;
  border: 1px solid var(--border-color, #e5e7eb);
  overflow: hidden;
}

.users-table {
  :deep(.el-table__header) {
    background: var(--table-header-bg, #f9fafb);
  }

  :deep(.el-table__row) {
    &:hover {
      background: var(--hover-bg, #f9fafb);
    }
  }

  .user-cell {
    display: flex;
    align-items: center;
    gap: 12px;

    .user-avatar {
      background: #3b82f6;
      color: white;
      font-weight: 600;
    }

    .user-info {
      .user-name {
        font-weight: 600;
        color: var(--text-primary, #1f2937);
      }

      .user-email {
        font-size: 13px;
        color: var(--text-secondary, #6b7280);
      }
    }
  }

  .last-login {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--text-secondary, #6b7280);
  }

  .never-connected {
    color: var(--text-tertiary, #9ca3af);
  }

  .action-buttons {
    display: flex;
    gap: 4px;
  }
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  padding: 16px;
  background: var(--card-bg, white);
  border-radius: 12px;
  border: 1px solid var(--border-color, #e5e7eb);
}

// Dark mode support
:deep(.el-input__wrapper),
:deep(.el-select),
:deep(.el-table),
:deep(.el-pagination) {
  background-color: var(--input-bg, white) !important;
  color: var(--text-primary, #1f2937) !important;
}

:deep(.el-table__body tr) {
  background-color: var(--card-bg, white) !important;
}

:deep(.el-table__body tr:hover > td) {
  background-color: var(--hover-bg, #f9fafb) !important;
}

:deep(.el-pagination button),
:deep(.el-pager li) {
  background-color: var(--card-bg, white) !important;
  color: var(--text-primary, #1f2937) !important;
}
</style>