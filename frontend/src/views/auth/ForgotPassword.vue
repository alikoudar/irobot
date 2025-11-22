<template>
  <div class="forgot-password-page">
    <div class="forgot-password-card">
      <!-- Logo et titre -->
      <div class="header">
        <div class="logo-circle">
          <el-icon :size="48" color="#005ca9">
            <Lock />
          </el-icon>
        </div>
        <h2>Mot de passe oublié ?</h2>
        <p class="subtitle">
          {{ !emailSent 
            ? 'Entrez votre matricule ou email pour réinitialiser votre mot de passe' 
            : 'Un email de réinitialisation a été envoyé'
          }}
        </p>
      </div>

      <!-- Formulaire (avant envoi) -->
      <el-form
        v-if="!emailSent"
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleSubmit"
        label-position="top"
      >
        <el-form-item label="Matricule ou Email" prop="identifier">
          <el-input
            v-model="form.identifier"
            placeholder="Ex: ADMIN001 ou email@beac.int"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="isLoading"
          :disabled="isLoading"
          class="submit-btn"
        >
          Envoyer le lien de réinitialisation
        </el-button>

        <div class="back-to-login">
          <router-link to="/login">
            <el-icon><ArrowLeft /></el-icon>
            Retour à la connexion
          </router-link>
        </div>
      </el-form>

      <!-- Message de confirmation (après envoi) -->
      <div v-else class="success-message">
        <el-result
          icon="success"
          title="Email envoyé !"
          sub-title="Consultez votre boîte mail et suivez les instructions pour réinitialiser votre mot de passe."
        >
          <template #extra>
            <div class="success-actions">
              <el-button type="primary" @click="handleResend" :loading="isLoading">
                Renvoyer l'email
              </el-button>
              <el-button @click="goToLogin">
                Retour à la connexion
              </el-button>
            </div>
          </template>
        </el-result>

        <div class="help-text">
          <p><strong>Vous n'avez pas reçu l'email ?</strong></p>
          <ul>
            <li>Vérifiez votre dossier spam/courrier indésirable</li>
            <li>Assurez-vous d'avoir entré le bon matricule ou email</li>
            <li>Contactez l'administrateur si le problème persiste</li>
          </ul>
        </div>
      </div>

      <!-- Support -->
      <div class="support-info">
        <el-divider />
        <p>
          <el-icon><QuestionFilled /></el-icon>
          Besoin d'aide ? Contactez le support : 
          <a href="mailto:support@beac.int">support@beac.int</a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, User, ArrowLeft, QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '@/services/api/auth'

const router = useRouter()
const formRef = ref(null)
const isLoading = ref(false)
const emailSent = ref(false)

const form = reactive({
  identifier: ''
})

const rules = {
  identifier: [
    { required: true, message: 'Le matricule ou l\'email est requis', trigger: 'blur' },
    { min: 3, message: 'Le matricule ou l\'email doit contenir au moins 3 caractères', trigger: 'blur' }
  ]
}

async function handleSubmit() {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    isLoading.value = true

    // Appeler l'API de réinitialisation
    await apiClient.post('/auth/forgot-password', {
      identifier: form.identifier
    })

    emailSent.value = true
    ElMessage.success('Email de réinitialisation envoyé')
  } catch (error) {
    console.error('Erreur:', error)
    
    // Message d'erreur adapté
    if (error.response?.status === 404) {
      ElMessage.error('Aucun utilisateur trouvé avec ce matricule ou email')
    } else if (error.response?.status === 403) {
      ElMessage.error('Votre compte est inactif. Contactez l\'administrateur.')
    } else {
      ElMessage.error('Erreur lors de l\'envoi de l\'email de réinitialisation')
    }
  } finally {
    isLoading.value = false
  }
}

async function handleResend() {
  isLoading.value = true
  
  try {
    await apiClient.post('/auth/forgot-password', {
      identifier: form.identifier
    })
    
    ElMessage.success('Email renvoyé avec succès')
  } catch (error) {
    ElMessage.error('Erreur lors du renvoi de l\'email')
  } finally {
    isLoading.value = false
  }
}

function goToLogin() {
  router.push('/login')
}
</script>

<style scoped lang="scss">
.forgot-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.forgot-password-card {
  background: white;
  border-radius: 16px;
  padding: 48px 40px;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);

  .header {
    text-align: center;
    margin-bottom: 32px;

    .logo-circle {
      width: 96px;
      height: 96px;
      margin: 0 auto 24px;
      background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    h2 {
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #1f2937;
    }

    .subtitle {
      color: #6b7280;
      font-size: 14px;
      margin: 0;
      line-height: 1.5;
    }
  }

  .submit-btn {
    width: 100%;
    margin-top: 8px;
  }

  .back-to-login {
    text-align: center;
    margin-top: 24px;

    a {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: #005ca9;
      text-decoration: none;
      font-size: 14px;
      font-weight: 500;
      transition: all 0.2s;

      &:hover {
        color: #004a8a;
        text-decoration: underline;
      }
    }
  }

  .success-message {
    .success-actions {
      display: flex;
      gap: 12px;
      justify-content: center;
      flex-wrap: wrap;
    }

    .help-text {
      margin-top: 32px;
      padding: 20px;
      background: #f9fafb;
      border-radius: 8px;
      border: 1px solid #e5e7eb;

      p {
        margin: 0 0 12px 0;
        font-size: 14px;
        color: #1f2937;

        strong {
          font-weight: 600;
        }
      }

      ul {
        margin: 0;
        padding-left: 20px;

        li {
          font-size: 13px;
          color: #6b7280;
          margin-bottom: 8px;
          line-height: 1.5;
        }
      }
    }
  }

  .support-info {
    margin-top: 32px;

    p {
      text-align: center;
      font-size: 13px;
      color: #6b7280;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;

      a {
        color: #005ca9;
        text-decoration: none;
        font-weight: 500;

        &:hover {
          text-decoration: underline;
        }
      }
    }
  }
}

// Responsive
@media (max-width: 576px) {
  .forgot-password-card {
    padding: 32px 24px;
  }

  .success-message .success-actions {
    flex-direction: column;

    .el-button {
      width: 100%;
    }
  }
}
</style>
