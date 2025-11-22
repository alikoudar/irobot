<template>
  <el-dialog
    v-model="visible"
    :title="isEditMode ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'"
    width="600px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="Matricule" prop="matricule">
            <el-input
              v-model="formData.matricule"
              placeholder="Ex: A0001, U0042"
              :disabled="isEditMode"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Email" prop="email">
            <el-input
              v-model="formData.email"
              type="email"
              placeholder="utilisateur@beac.int"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="Nom" prop="nom">
            <el-input
              v-model="formData.nom"
              placeholder="Dupont"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Prénom" prop="prenom">
            <el-input
              v-model="formData.prenom"
              placeholder="Jean"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="Rôle" prop="role">
            <el-select
              v-model="formData.role"
              placeholder="Sélectionnez un rôle"
              style="width: 100%"
            >
              <el-option label="Administrateur" value="ADMIN">
                <span style="float: left">Administrateur</span>
                <span style="float: right; color: #8492a6; font-size: 13px">
                  Accès complet
                </span>
              </el-option>
              <el-option label="Manager" value="MANAGER">
                <span style="float: left">Manager</span>
                <span style="float: right; color: #8492a6; font-size: 13px">
                  Gestion docs
                </span>
              </el-option>
              <el-option label="Utilisateur" value="USER">
                <span style="float: left">Utilisateur</span>
                <span style="float: right; color: #8492a6; font-size: 13px">
                  Chatbot uniquement
                </span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Statut">
            <el-switch
              v-model="formData.is_active"
              active-text="Actif"
              inactive-text="Inactif"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item v-if="!isEditMode" label="Mot de passe" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="Minimum 10 caractères"
          show-password
        >
          <template #append>
            <el-button @click="generatePassword">
              <el-icon><RefreshRight /></el-icon>
              Générer
            </el-button>
          </template>
        </el-input>
        <div v-if="formData.password" class="password-hint">
          <small>
            <el-icon><InfoFilled /></el-icon>
            L'utilisateur devra changer ce mot de passe à la première connexion
          </small>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">Annuler</el-button>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ isEditMode ? 'Mettre à jour' : 'Créer' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { RefreshRight, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  user: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const formRef = ref(null)

// Visibilité du dialog
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// Mode édition
const isEditMode = computed(() => !!props.user)

// Formulaire
const formData = reactive({
  matricule: '',
  email: '',
  nom: '',
  prenom: '',
  role: 'USER',
  password: '',
  is_active: true
})

// Règles de validation
const validatePassword = (rule, value, callback) => {
  if (!isEditMode.value) {
    if (!value) {
      callback(new Error('Veuillez saisir un mot de passe'))
    } else if (value.length < 10) {
      callback(new Error('Le mot de passe doit contenir au moins 10 caractères'))
    } else if (!/[A-Z]/.test(value)) {
      callback(new Error('Le mot de passe doit contenir au moins une majuscule'))
    } else if (!/[a-z]/.test(value)) {
      callback(new Error('Le mot de passe doit contenir au moins une minuscule'))
    } else if (!/[0-9]/.test(value)) {
      callback(new Error('Le mot de passe doit contenir au moins un chiffre'))
    } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(value)) {
      callback(new Error('Le mot de passe doit contenir au moins un caractère spécial'))
    } else {
      callback()
    }
  } else {
    callback()
  }
}

const rules = {
  matricule: [
    { required: true, message: 'Veuillez saisir un matricule', trigger: 'blur' }
  ],
  email: [
    { required: true, message: 'Veuillez saisir un email', trigger: 'blur' },
    { type: 'email', message: 'Email invalide', trigger: 'blur' }
  ],
  nom: [
    { required: true, message: 'Veuillez saisir un nom', trigger: 'blur' }
  ],
  prenom: [
    { required: true, message: 'Veuillez saisir un prénom', trigger: 'blur' }
  ],
  role: [
    { required: true, message: 'Veuillez sélectionner un rôle', trigger: 'change' }
  ],
  password: [
    { validator: validatePassword, trigger: 'blur' }
  ]
}

// Réinitialiser le formulaire (DÉCLARÉ AVANT watch)
const resetForm = () => {
  Object.assign(formData, {
    matricule: '',
    email: '',
    nom: '',
    prenom: '',
    role: 'USER',
    password: '',
    is_active: true
  })
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

// Générer un mot de passe aléatoire
const generatePassword = () => {
  const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  const lowercase = 'abcdefghijklmnopqrstuvwxyz'
  const numbers = '0123456789'
  const special = '!@#$%^&*(),.?":{}|<>'
  const all = uppercase + lowercase + numbers + special

  let password = ''
  
  // Assurer au moins un caractère de chaque type
  password += uppercase[Math.floor(Math.random() * uppercase.length)]
  password += lowercase[Math.floor(Math.random() * lowercase.length)]
  password += numbers[Math.floor(Math.random() * numbers.length)]
  password += special[Math.floor(Math.random() * special.length)]

  // Compléter jusqu'à 12 caractères
  for (let i = password.length; i < 12; i++) {
    password += all[Math.floor(Math.random() * all.length)]
  }

  // Mélanger les caractères
  formData.password = password.split('').sort(() => Math.random() - 0.5).join('')
}

// Charger les données de l'utilisateur en mode édition (MAINTENANT APRÈS resetForm)
watch(
  () => props.user,
  (newUser) => {
    if (newUser) {
      Object.assign(formData, {
        matricule: newUser.matricule,
        email: newUser.email,
        nom: newUser.nom,
        prenom: newUser.prenom,
        role: newUser.role,
        is_active: newUser.is_active,
        password: '' // Ne pas charger le mot de passe
      })
    } else {
      resetForm()
    }
  },
  { immediate: true }
)

// Fermer le dialog
const handleClose = () => {
  resetForm()
  visible.value = false
}

// Soumettre le formulaire
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate((valid) => {
    if (valid) {
      // Préparer les données à envoyer
      const dataToSend = isEditMode.value
        ? {
            email: formData.email,
            nom: formData.nom,
            prenom: formData.prenom,
            role: formData.role,
            is_active: formData.is_active
          }
        : { ...formData }

      emit('submit', dataToSend)
    }
  })
}

defineExpose({
  resetForm
})
</script>

<style scoped lang="scss">
:deep(.el-dialog__body) {
  padding: 20px 30px;
}

.password-hint {
  margin-top: 8px;
  color: #909399;

  small {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>