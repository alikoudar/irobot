<template>
  <div class="change-password-page">
    <div class="change-password-card">
      <!-- Bouton fermer -->
      <el-button
        link
        class="close-btn"
        @click="handleClose"
      >
        <el-icon :size="20"><Close /></el-icon>
      </el-button>

      <!-- Icône cadenas -->
      <div class="icon-container">
        <el-icon :size="48" color="#005ca9">
          <Lock />
        </el-icon>
      </div>

      <!-- Titre -->
      <h2>Changement de mot de passe</h2>
      <p class="subtitle">Pour votre sécurité, changez régulièrement votre mot de passe</p>

      <!-- Formulaire -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleSubmit"
        label-position="top"
      >
        <el-form-item label="Mot de passe actuel" prop="currentPassword">
          <el-input
            v-model="form.currentPassword"
            type="password"
            placeholder="Entrez votre mot de passe actuel"
            show-password
            size="large"
          />
        </el-form-item>

        <el-form-item label="Nouveau mot de passe" prop="newPassword">
          <el-input
            v-model="form.newPassword"
            type="password"
            placeholder="Entrez le nouveau mot de passe"
            show-password
            size="large"
            @input="checkPasswordStrength"
          />
          <!-- Force du mot de passe -->
          <div v-if="form.newPassword" class="password-strength">
            <div class="strength-bar" :class="`strength-${passwordStrength.level}`">
              <div class="strength-fill"></div>
            </div>
            <span class="strength-text" :style="{ color: passwordStrength.color }">
              {{ passwordStrength.label }}
            </span>
          </div>
        </el-form-item>

        <el-form-item label="Confirmer le nouveau mot de passe" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="Confirmez le nouveau mot de passe"
            show-password
            size="large"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <!-- Critères de validation -->
        <div class="password-criteria">
          <p class="criteria-title">Le mot de passe doit contenir :</p>
          <div class="criteria-list">
            <div class="criteria-item" :class="{ valid: hasMinLength }">
              <el-icon :size="16">
                <CircleCheck v-if="hasMinLength" />
                <CircleClose v-else />
              </el-icon>
              <span>Au moins 10 caractères</span>
            </div>
            <div class="criteria-item" :class="{ valid: hasUppercase }">
              <el-icon :size="16">
                <CircleCheck v-if="hasUppercase" />
                <CircleClose v-else />
              </el-icon>
              <span>Au moins une majuscule</span>
            </div>
            <div class="criteria-item" :class="{ valid: hasLowercase }">
              <el-icon :size="16">
                <CircleCheck v-if="hasLowercase" />
                <CircleClose v-else />
              </el-icon>
              <span>Au moins une minuscule</span>
            </div>
            <div class="criteria-item" :class="{ valid: hasNumber }">
              <el-icon :size="16">
                <CircleCheck v-if="hasNumber" />
                <CircleClose v-else />
              </el-icon>
              <span>Au moins un chiffre</span>
            </div>
          </div>
        </div>

        <!-- Boutons -->
        <div class="form-actions">
          <el-button size="large" @click="handleClose">
            Annuler
          </el-button>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.isLoading"
            native-type="submit"
            :disabled="!isFormValid || authStore.isLoading"
          >
            Changer le mot de passe
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, Close, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)

// Formulaire
const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// Règles de validation
const rules = {
  currentPassword: [
    { required: true, message: 'Le mot de passe actuel est requis', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: 'Le nouveau mot de passe est requis', trigger: 'blur' },
    { min: 10, message: 'Le mot de passe doit contenir au moins 10 caractères', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: 'Veuillez confirmer le mot de passe', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.newPassword) {
          callback(new Error('Les mots de passe ne correspondent pas'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// Validation du mot de passe
const hasMinLength = computed(() => form.newPassword.length >= 10)
const hasUppercase = computed(() => /[A-Z]/.test(form.newPassword))
const hasLowercase = computed(() => /[a-z]/.test(form.newPassword))
const hasNumber = computed(() => /[0-9]/.test(form.newPassword))

const isFormValid = computed(() => {
  return hasMinLength.value && hasUppercase.value && hasLowercase.value && hasNumber.value && 
         form.currentPassword && form.newPassword === form.confirmPassword
})

// Force du mot de passe
const passwordStrength = computed(() => {
  const password = form.newPassword
  if (!password) return { level: 'weak', label: '', color: '#9ca3af' }

  let score = 0
  if (hasMinLength.value) score++
  if (hasUppercase.value) score++
  if (hasLowercase.value) score++
  if (hasNumber.value) score++
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++

  if (score <= 2) return { level: 'weak', label: 'Faible', color: '#ef4444' }
  if (score <= 4) return { level: 'medium', label: 'Moyen', color: '#f59e0b' }
  return { level: 'strong', label: 'Fort', color: '#10b981' }
})

function checkPasswordStrength() {
  // Force la réactivité
}

// Soumettre
async function handleSubmit() {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    const success = await authStore.changePassword(
      form.currentPassword,
      form.newPassword
    )

    if (success) {
      ElMessage.success('Mot de passe changé avec succès')
      router.push('/admin/users')
    }
  } catch (error) {
    console.error('Erreur validation:', error)
  }
}

function handleClose() {
  router.back()
}
</script>

<style scoped lang="scss">
.change-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  position: relative;
}

.change-password-card {
  background: white;
  border-radius: 16px;
  padding: 48px 40px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;

  .close-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    color: #6b7280;
    
    &:hover {
      color: #1f2937;
    }
  }

  .icon-container {
    width: 80px;
    height: 80px;
    margin: 0 auto 24px;
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  h2 {
    text-align: center;
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 8px 0;
    color: #1f2937;
  }

  .subtitle {
    text-align: center;
    color: #6b7280;
    margin: 0 0 32px 0;
    font-size: 14px;
  }

  :deep(.el-form-item__label) {
    color: #1f2937;
    font-weight: 500;
  }

  // Critères de validation
  .password-criteria {
    margin-top: 16px;
    padding: 16px;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;

    .criteria-title {
      margin: 0 0 12px 0;
      font-size: 13px;
      font-weight: 500;
      color: #1f2937;
    }

    .criteria-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .criteria-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #6b7280;
      transition: all 0.3s ease;

      .el-icon {
        color: #9ca3af;
        transition: all 0.3s ease;
      }

      // État valide (vert avec icône check)
      &.valid {
        color: #10b981;
        font-weight: 500;

        .el-icon {
          color: #10b981;
        }
      }
    }
  }

  // Barre de force du mot de passe
  .password-strength {
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 12px;

    .strength-bar {
      flex: 1;
      height: 6px;
      background: #f3f4f6;
      border-radius: 3px;
      overflow: hidden;
      position: relative;

      .strength-fill {
        height: 100%;
        border-radius: 3px;
        transition: all 0.3s ease;
      }

      &.strength-weak .strength-fill {
        width: 33%;
        background: #ef4444;
      }

      &.strength-medium .strength-fill {
        width: 66%;
        background: #f59e0b;
      }

      &.strength-strong .strength-fill {
        width: 100%;
        background: #10b981;
      }
    }

    .strength-text {
      font-size: 12px;
      font-weight: 600;
      min-width: 50px;
    }
  }

  .form-actions {
    display: flex;
    gap: 12px;
    margin-top: 32px;

    .el-button {
      flex: 1;
    }
  }
}
</style>