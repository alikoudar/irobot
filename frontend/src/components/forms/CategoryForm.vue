<template>
  <el-form
    ref="formRef"
    :model="formData"
    :rules="rules"
    label-position="top"
    label-width="120px"
    @submit.prevent="handleSubmit"
  >
    <!-- Nom de la catégorie -->
    <el-form-item label="Nom de la catégorie" prop="name" required>
      <el-input
        v-model="formData.name"
        placeholder="Ex: Lettres Circulaires"
        maxlength="100"
        show-word-limit
        clearable
      >
        <template #prefix>
          <el-icon><Folder /></el-icon>
        </template>
      </el-input>
      <div class="form-help-text">
        Le nom doit être unique et contenir au moins 2 caractères
      </div>
    </el-form-item>

    <!-- Description -->
    <el-form-item label="Description" prop="description">
      <el-input
        v-model="formData.description"
        type="textarea"
        placeholder="Description de la catégorie (optionnel)"
        :rows="3"
        maxlength="500"
        show-word-limit
      />
    </el-form-item>

    <!-- Couleur -->
    <el-form-item label="Couleur" prop="color">
      <div class="color-selector">
        <el-color-picker
          v-model="formData.color"
          show-alpha
          :predefine="predefinedColors"
          size="large"
        />
        <el-input
          v-model="formData.color"
          placeholder="#005CA9"
          maxlength="7"
          style="width: 150px; margin-left: 16px;"
        >
          <template #prefix>
            <span style="color: #999">#</span>
          </template>
        </el-input>
        <div class="color-preview" :style="{ backgroundColor: formData.color || '#CCCCCC' }">
          <span v-if="formData.color">{{ formData.name || 'Aperçu' }}</span>
          <span v-else style="color: #999">Aperçu</span>
        </div>
      </div>
      <div class="form-help-text">
        Sélectionnez une couleur pour identifier rapidement la catégorie
      </div>
    </el-form-item>

    <!-- Couleurs prédéfinies -->
    <el-form-item label="Couleurs suggérées">
      <div class="color-palette-compact">
        <div
          v-for="(colorInfo, index) in suggestedColors"
          :key="index"
          class="color-option-compact"
          :class="{ active: formData.color?.toUpperCase() === colorInfo.hex.toUpperCase() }"
          :style="{ backgroundColor: colorInfo.hex }"
          @click="selectColor(colorInfo.hex)"
          :title="colorInfo.name"
        >
          <el-icon v-if="formData.color?.toUpperCase() === colorInfo.hex.toUpperCase()" class="check-icon">
            <Check />
          </el-icon>
        </div>
      </div>
    </el-form-item>

    <!-- Actions -->
    <el-form-item>
      <div class="form-actions">
        <el-button @click="handleCancel">
          Annuler
        </el-button>
        <el-button
          type="primary"
          native-type="submit"
          :loading="isLoading"
        >
          {{ isEditMode ? 'Mettre à jour' : 'Créer' }}
        </el-button>
      </div>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { Folder, Check } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  category: {
    type: Object,
    default: null
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['submit', 'cancel'])

// Refs
const formRef = ref(null)

// Mode édition
const isEditMode = computed(() => !!props.category)

// Données du formulaire
const formData = reactive({
  name: '',
  description: '',
  color: '#005CA9' // Couleur par défaut BEAC
})

// Couleurs BEAC prédéfinies
const predefinedColors = [
  '#005CA9', // Bleu BEAC
  '#C2A712', // Or BEAC
  '#4A90E2', // Bleu clair
  '#50C878', // Vert émeraude
  '#E74C3C', // Rouge
  '#9B59B6', // Violet
  '#F39C12', // Orange
  '#1ABC9C'  // Turquoise
]

// Couleurs suggérées avec labels
const suggestedColors = [
  { hex: '#005CA9', name: 'Bleu BEAC', label: 'Bleu BEAC' },
  { hex: '#C2A712', name: 'Or BEAC', label: 'Or BEAC' },
  { hex: '#4A90E2', name: 'Bleu clair', label: 'Bleu' },
  { hex: '#50C878', name: 'Vert émeraude', label: 'Vert' },
  { hex: '#E74C3C', name: 'Rouge', label: 'Rouge' },
  { hex: '#9B59B6', name: 'Violet', label: 'Violet' },
  { hex: '#F39C12', name: 'Orange', label: 'Orange' },
  { hex: '#1ABC9C', name: 'Turquoise', label: 'Turquoise' }
]

// Règles de validation
const rules = {
  name: [
    { required: true, message: 'Le nom est obligatoire', trigger: 'blur' },
    { min: 2, message: 'Le nom doit contenir au moins 2 caractères', trigger: 'blur' },
    { max: 100, message: 'Le nom ne peut pas dépasser 100 caractères', trigger: 'blur' }
  ],
  description: [
    { max: 500, message: 'La description ne peut pas dépasser 500 caractères', trigger: 'blur' }
  ],
  color: [
    {
      pattern: /^#[0-9A-Fa-f]{6}$/,
      message: 'La couleur doit être au format hexadécimal (#RRGGBB)',
      trigger: 'blur'
    }
  ]
}

// Watcher pour initialiser le formulaire en mode édition
watch(
  () => props.category,
  (newCategory) => {
    if (newCategory) {
      formData.name = newCategory.name || ''
      formData.description = newCategory.description || ''
      formData.color = newCategory.color || '#005CA9'
    } else {
      resetForm()
    }
  },
  { immediate: true }
)

// Méthodes

/**
 * Sélectionner une couleur
 */
function selectColor(hex) {
  formData.color = hex.toUpperCase()
}

/**
 * Gérer la soumission du formulaire
 */
async function handleSubmit() {
  if (!formRef.value) return

  try {
    // Valider le formulaire
    await formRef.value.validate()

    // Préparer les données
    const data = {
      name: formData.name.trim(),
      description: formData.description?.trim() || null,
      color: formData.color?.toUpperCase() || null
    }

    // Émettre l'événement submit
    emit('submit', data)
  } catch (error) {
    console.error('❌ Validation error:', error)
  }
}

/**
 * Gérer l'annulation
 */
function handleCancel() {
  emit('cancel')
}

/**
 * Réinitialiser le formulaire
 */
function resetForm() {
  formData.name = ''
  formData.description = ''
  formData.color = '#005CA9'
  formRef.value?.clearValidate()
}

// Exposer les méthodes
defineExpose({
  resetForm
})
</script>

<style scoped lang="scss">
.form-help-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.color-selector {
  display: flex;
  align-items: center;
  gap: 16px;

  .color-preview {
    flex: 1;
    height: 48px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 14px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.3);
  }
}

.color-palette-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;

  .color-option-compact {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
    border: 2px solid transparent;
    position: relative;

    &:hover {
      transform: scale(1.1);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    &.active {
      border-color: white;
      box-shadow: 0 0 0 2px var(--el-color-primary);

      .check-icon {
        color: white;
        font-size: 20px;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
      }
    }
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>