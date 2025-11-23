<template>
  <div class="login-page-irobot">
    <!-- Partie gauche - Branding IroBot BEAC -->
    <div class="left-panel">
      <div class="branding-content">
        <!-- Logo IroBot -->
        <div class="logo-irobot">
          <div class="logo-circle">
            <el-icon :size="80" color="#c2a712">
              <ChatDotRound />
            </el-icon>
          </div>
        </div>

        <!-- Texte -->
        <h1 class="title-irobot">IroBot</h1>
        <h2 class="subtitle-cap">L’IA au service de l’expertise interne.</h2>
      </div>
    </div>

    <!-- Partie droite - Formulaire -->
    <div class="right-panel">
      <div class="form-container">
        <!-- Logo en haut du formulaire -->
        <div class="form-header">
          <div class="logo-form">
            <el-icon :size="50" color="#005ca9">
              <ChatDotRound />
            </el-icon>
          </div>
          <h3>Connexion à IroBot – Espace Utilisateur</h3>
        </div>

        <!-- Formulaire de connexion -->
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="rules"
          @submit.prevent="handleLogin"
          class="login-form"
        >
          <el-form-item prop="matricule">
            <el-input
              v-model="loginForm.matricule"
              placeholder="Votre Matricule"
              size="large"
              class="irobot-input"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="Mot de passe"
              size="large"
              show-password
              class="irobot-input"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

           <div class="forgot-password">
            <router-link to="/forgot-password">Mot de passe oublié ?</router-link>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="authStore.isLoading"
            class="connexion-button"
            native-type="submit"
            :disabled="authStore.isLoading"
          >
            Connexion
          </el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ChatDotRound } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loginFormRef = ref(null)

const loginForm = reactive({
  matricule: '',
  password: ''
})

const rules = {
  matricule: [
    { required: true, message: 'Veuillez saisir votre matricule', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Veuillez saisir votre mot de passe', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return

    const success = await authStore.login(loginForm.matricule, loginForm.password)

    if (success) {
      if (authStore.mustChangePassword) {
        router.push('/change-password')
      } else if (authStore.isAdmin) {
        router.push('/admin/users')
      } else {
        router.push('/chat')
      }
    }
  })
}

onMounted(() => {
  if (authStore.isAuthenticated) {
    if (authStore.mustChangePassword) {
      router.push('/change-password')
    } else if (authStore.isAdmin) {
      router.push('/admin/users')
    } else {
      router.push('/chat')
    }
  }
})
</script>

<style scoped lang="scss">
.login-page-irobot {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

// Partie gauche - Branding
.left-panel {
  flex: 1;
  background: linear-gradient(135deg, #005ca9 0%, #004a8a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 30% 50%, rgba(194, 167, 18, 0.1) 0%, transparent 50%);
    pointer-events: none;
  }

  .branding-content {
    text-align: center;
    z-index: 1;
    padding: 40px;

    .logo-irobot {
      margin-bottom: 40px;
      animation: fadeInScale 0.8s ease-out;

      .logo-circle {
        width: 160px;
        height: 160px;
        margin: 0 auto;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.1);
        border: 3px solid #c2a712;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      }
    }

    .title-irobot {
      font-size: 64px;
      font-weight: 800;
      letter-spacing: 4px;
      margin: 0 0 16px 0;
      text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
      animation: fadeInUp 0.8s ease-out 0.2s both;
    }

    .subtitle-env {
      font-size: 18px;
      font-weight: 400;
      margin: 0 0 32px 0;
      opacity: 0.9;
      animation: fadeInUp 0.8s ease-out 0.3s both;
    }

    .subtitle-cap {
      font-size: 24px;
      font-weight: 600;
      letter-spacing: 1px;
      margin: 0;
      opacity: 0.95;
      animation: fadeInUp 0.8s ease-out 0.4s both;
    }
  }
}

// Partie droite - Formulaire
.right-panel {
  flex: 1;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;

  .form-container {
    background: white;
    border-radius: 16px;
    padding: 48px 40px;
    width: 100%;
    max-width: 440px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    animation: fadeInRight 0.6s ease-out;

    .form-header {
      text-align: center;
      margin-bottom: 40px;

      .logo-form {
        margin-bottom: 16px;
      }

      h3 {
        font-size: 18px;
        font-weight: 600;
        color: #005ca9;
        margin: 0;
      }
    }

    .login-form {
      .el-form-item {
        margin-bottom: 24px;
      }

      :deep(.irobot-input) {
        .el-input__wrapper {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 14px 16px;
          box-shadow: none;
          transition: all 0.3s;

          &:hover {
            border-color: #cbd5e1;
          }

          &.is-focus {
            background: white;
            border-color: #005ca9;
            box-shadow: 0 0 0 3px rgba(0, 92, 169, 0.1);
          }
        }

        .el-input__inner {
          font-size: 15px;
          color: #1e293b;
          font-weight: 500;

          &::placeholder {
            color: #94a3b8;
            font-weight: 400;
          }
        }
      }

      .forgot-password {
        text-align: right;
        margin-bottom: 24px;
        margin-top: -8px;

        a {
          font-size: 14px;
          color: #ef4444;
          text-decoration: none;
          font-weight: 500;
          transition: color 0.2s;

          &:hover {
            color: #dc2626;
            text-decoration: underline;
          }
        }
      }

      .connexion-button {
        width: 100%;
        height: 52px;
        font-size: 16px;
        font-weight: 600;
        background: #005ca9;
        border: none;
        border-radius: 8px;
        letter-spacing: 0.5px;
        transition: all 0.3s;

        &:hover:not(:disabled) {
          background: #004a8a;
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(0, 92, 169, 0.3);
        }

        &:active:not(:disabled) {
          transform: translateY(0);
        }

        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }
    }
  }
}

// Animations
@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

// Responsive
@media (max-width: 968px) {
  .login-page-irobot {
    flex-direction: column;
  }

  .left-panel {
    min-height: 40vh;

    .branding-content {
      padding: 20px;

      .logo-irobot .logo-circle {
        width: 100px;
        height: 100px;
      }

      .title-irobot {
        font-size: 40px;
      }

      .subtitle-env {
        font-size: 14px;
      }

      .subtitle-cap {
        font-size: 18px;
      }
    }
  }

  .right-panel {
    min-height: 60vh;
    padding: 20px;

    .form-container {
      padding: 32px 24px;
    }
  }
}
</style>