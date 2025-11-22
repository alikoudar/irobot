<template>
  <div class="profile-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>Mon profil</h1>
        <p>Gérez vos informations personnelles</p>
      </div>
    </div>

    <div class="profile-container">
      <!-- Card Avatar et Info de base -->
      <div class="profile-card">
        <div class="profile-header">
          <el-avatar :size="120" class="profile-avatar">
            {{ authStore.currentUser?.prenom?.charAt(0) }}{{ authStore.currentUser?.nom?.charAt(0) }}
          </el-avatar>
          <div class="profile-info">
            <h2>{{ authStore.userFullName }}</h2>
            <p class="user-role">
              <el-tag :type="getRoleType(authStore.currentUser?.role)">
                {{ getRoleLabel(authStore.currentUser?.role) }}
              </el-tag>
            </p>
            <p class="user-matricule">
              <el-icon><Document /></el-icon>
              {{ authStore.currentUser?.matricule }}
            </p>
          </div>
        </div>
      </div>

      <!-- Formulaire d'édition -->
      <div class="profile-form-card">
        <div class="card-header">
          <h3>Informations personnelles</h3>
          <el-button 
            v-if="!isEditing" 
            type="primary" 
            @click="startEditing"
            :icon="Edit"
          >
            Modifier
          </el-button>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          :disabled="!isEditing"
        >
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="Nom" prop="nom">
                <el-input
                  v-model="form.nom"
                  placeholder="Votre nom"
                  size="large"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Prénom" prop="prenom">
                <el-input
                  v-model="form.prenom"
                  placeholder="Votre prénom"
                  size="large"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="Email" prop="email">
            <el-input
              v-model="form.email"
              type="email"
              placeholder="votre.email@beac.int"
              size="large"
            />
          </el-form-item>

          <el-form-item label="Matricule">
            <el-input
              v-model="form.matricule"
              disabled
              size="large"
            />
          </el-form-item>

          <el-form-item label="Rôle">
            <el-input
              :value="getRoleLabel(form.role)"
              disabled
              size="large"
            />
          </el-form-item>

          <!-- Boutons d'action (visible uniquement en mode édition) -->
          <div v-if="isEditing" class="form-actions">
            <el-button size="large" @click="cancelEditing">
              Annuler
            </el-button>
            <el-button
              type="primary"
              size="large"
              :loading="isLoading"
              @click="handleSubmit"
            >
              Enregistrer
            </el-button>
          </div>
        </el-form>
      </div>

      <!-- Card Mot de passe -->
      <div class="password-card">
        <div class="card-header">
          <div>
            <h3>Mot de passe</h3>
            <p>Changez votre mot de passe régulièrement pour plus de sécurité</p>
          </div>
          <el-button @click="goToChangePassword" :icon="Lock">
            Changer le mot de passe
          </el-button>
        </div>
      </div>

      <!-- Card Informations supplémentaires -->
      <div class="info-card">
        <h3>Informations du compte</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Statut">
            <el-tag :type="authStore.currentUser?.is_active ? 'success' : 'danger'">
              {{ authStore.currentUser?.is_active ? 'Actif' : 'Inactif' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Dernière connexion">
            {{ formatDate(authStore.currentUser?.last_login) || 'Jamais' }}
          </el-descriptions-item>
          <el-descriptions-item label="Date de création">
            {{ formatDate(authStore.currentUser?.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Dernière modification">
            {{ formatDate(authStore.currentUser?.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Edit, Lock, Document } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)

const isEditing = ref(false)
const isLoading = ref(false)

const form = reactive({
  nom: '',
  prenom: '',
  email: '',
  matricule: '',
  role: ''
})

const rules = {
  nom: [
    { required: true, message: 'Le nom est requis', trigger: 'blur' },
    { min: 2, message: 'Le nom doit contenir au moins 2 caractères', trigger: 'blur' }
  ],
  prenom: [
    { required: true, message: 'Le prénom est requis', trigger: 'blur' },
    { min: 2, message: 'Le prénom doit contenir au moins 2 caractères', trigger: 'blur' }
  ],
  email: [
    { required: true, message: 'L\'email est requis', trigger: 'blur' },
    { type: 'email', message: 'Email invalide', trigger: 'blur' }
  ]
}

// Charger les données du profil
function loadProfile() {
  if (authStore.currentUser) {
    form.nom = authStore.currentUser.nom || ''
    form.prenom = authStore.currentUser.prenom || ''
    form.email = authStore.currentUser.email || ''
    form.matricule = authStore.currentUser.matricule || ''
    form.role = authStore.currentUser.role || ''
  }
}

function startEditing() {
  isEditing.value = true
}

function cancelEditing() {
  isEditing.value = false
  loadProfile() // Recharger les données originales
}

async function handleSubmit() {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    isLoading.value = true

    // Appeler l'API pour mettre à jour le profil
    const success = await authStore.updateProfile({
      nom: form.nom,
      prenom: form.prenom,
      email: form.email
    })

    if (success) {
      ElMessage.success('Profil mis à jour avec succès')
      isEditing.value = false
    }
  } catch (error) {
    console.error('Erreur validation:', error)
  } finally {
    isLoading.value = false
  }
}

function goToChangePassword() {
  router.push('/change-password')
}

function getRoleLabel(role) {
  const labels = { ADMIN: 'Administrateur', MANAGER: 'Manager', USER: 'Utilisateur' }
  return labels[role] || role
}

function getRoleType(role) {
  const types = { ADMIN: 'danger', MANAGER: 'warning', USER: '' }
  return types[role] || ''
}

function formatDate(dateString) {
  if (!dateString) return null
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(dateString))
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped lang="scss">
.profile-page {
  padding: 24px;
  min-height: 100vh;
  background: #f5f7fa;
}

.page-header {
  margin-bottom: 24px;

  h1 {
    font-size: 28px;
    font-weight: 700;
    margin: 0 0 4px 0;
    color: #1f2937;
  }

  p {
    color: #6b7280;
    margin: 0;
  }
}

.profile-container {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-card {
  background: white;
  border-radius: 12px;
  padding: 32px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .profile-header {
    display: flex;
    align-items: center;
    gap: 24px;

    .profile-avatar {
      background: linear-gradient(135deg, #005ca9 0%, #004a8a 100%);
      color: white;
      font-size: 40px;
      font-weight: 700;
      flex-shrink: 0;
    }

    .profile-info {
      flex: 1;

      h2 {
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 8px 0;
        color: #1f2937;
      }

      .user-role {
        margin: 0 0 8px 0;
      }

      .user-matricule {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #6b7280;
        margin: 0;
        font-size: 14px;
      }
    }
  }
}

.profile-form-card,
.password-card,
.info-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;

  h3 {
    font-size: 18px;
    font-weight: 600;
    margin: 0;
    color: #1f2937;
  }

  p {
    font-size: 14px;
    color: #6b7280;
    margin: 4px 0 0 0;
  }
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.info-card {
  h3 {
    font-size: 18px;
    font-weight: 600;
    margin: 0 0 16px 0;
    color: #1f2937;
  }
}

// Responsive
@media (max-width: 768px) {
  .profile-card .profile-header {
    flex-direction: column;
    text-align: center;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
