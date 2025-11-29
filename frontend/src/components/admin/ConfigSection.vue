<template>
  <div class="config-section">
    <el-card>
      <template #header>
        <div class="section-header">
          <h3>{{ title }}</h3>
          <el-text type="info" size="small">{{ description }}</el-text>
        </div>
      </template>

      <el-table
        :data="configItems"
        stripe
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column
          prop="label"
          label="Paramètre"
          min-width="200"
        >
          <template #default="{ row }">
            <div class="param-cell">
              <strong>{{ row.label }}</strong>
              <el-text type="info" size="small" v-if="row.description">
                {{ row.description }}
              </el-text>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="current_value"
          label="Valeur actuelle"
          min-width="250"
        >
          <template #default="{ row }">
            <div class="value-cell">
              <!-- Affichage pour nombres -->
              <el-tag v-if="row.type === 'number'">
                {{ formatValue(row.current_value) }} {{ row.unit || '' }}
              </el-tag>

              <!-- Affichage pour boolean -->
              <el-tag
                v-else-if="row.type === 'boolean'"
                :type="row.current_value ? 'success' : 'danger'"
              >
                {{ row.current_value ? 'Activé' : 'Désactivé' }}
              </el-tag>

              <!-- Affichage pour modèles -->
              <el-tag v-else-if="row.type === 'model'" type="primary">
                {{ row.current_value }}
              </el-tag>

              <!-- Affichage pour listes -->
              <div v-else-if="row.type === 'array'" class="array-value">
                <el-tag
                  v-for="(item, index) in row.current_value"
                  :key="index"
                  size="small"
                  style="margin-right: 5px; margin-bottom: 5px;"
                >
                  {{ item }}
                </el-tag>
              </div>

              <!-- Affichage par défaut -->
              <span v-else>{{ formatValue(row.current_value) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="Actions"
          width="220"
          align="center"
        >
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                @click="handleEdit(row)"
                :disabled="saving"
              >
                <el-icon><Edit /></el-icon>
                Modifier
              </el-button>
              <el-button
                size="small"
                type="info"
                plain
                @click="handleHistory(row)"
              >
                <el-icon><Clock /></el-icon>
                Historique
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Modal d'édition -->
    <el-dialog
      v-model="editDialogVisible"
      :title="`Modifier ${currentRow?.label}`"
      width="600px"
      @close="handleEditClose"
    >
      <el-form
        v-if="currentRow"
        :model="editForm"
        label-position="top"
      >
        <!-- Édition nombre -->
        <el-form-item
          v-if="currentRow.type === 'number'"
          :label="`Nouvelle valeur ${currentRow.unit ? '(' + currentRow.unit + ')' : ''}`"
        >
          <el-input-number
            v-model="editForm.value"
            :min="currentRow.min"
            :max="currentRow.max"
            :step="currentRow.step || 1"
            :precision="currentRow.precision"
            style="width: 100%"
          />
          <el-text type="info" size="small" v-if="currentRow.range">
            {{ currentRow.range }}
          </el-text>
        </el-form-item>

        <!-- Édition boolean -->
        <el-form-item
          v-else-if="currentRow.type === 'boolean'"
          label="État"
        >
          <el-switch
            v-model="editForm.value"
            active-text="Activé"
            inactive-text="Désactivé"
          />
        </el-form-item>

        <!-- Édition modèle -->
        <el-form-item
          v-else-if="currentRow.type === 'model'"
          label="Modèle Mistral"
        >
          <el-select
            v-model="editForm.value"
            placeholder="Sélectionner un modèle"
            style="width: 100%"
          >
            <el-option
              v-for="model in availableModels"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>

        <!-- Édition liste -->
        <el-form-item
          v-else-if="currentRow.type === 'array'"
          label="Extensions autorisées"
        >
          <el-select
            v-model="editForm.value"
            multiple
            placeholder="Sélectionner les extensions"
            style="width: 100%"
          >
            <el-option
              v-for="ext in availableExtensions"
              :key="ext"
              :label="ext"
              :value="ext"
            />
          </el-select>
        </el-form-item>

        <!-- Édition texte (fallback) -->
        <el-form-item
          v-else
          label="Nouvelle valeur"
        >
          <el-input v-model="editForm.value" />
        </el-form-item>

        <!-- Description (optionnel) -->
        <el-form-item label="Description (optionnel)">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="2"
            placeholder="Raison de la modification..."
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">Annuler</el-button>
        <el-button
          type="primary"
          @click="handleSave"
          :loading="saving"
        >
          Enregistrer
        </el-button>
      </template>
    </el-dialog>

    <!-- Modal historique -->
    <config-history-modal
      v-model="historyDialogVisible"
      :config-key="currentHistoryKey"
      :config-label="currentHistoryLabel"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Edit, Clock } from '@element-plus/icons-vue'
import { useConfigStore } from '@/stores/config'
import { ElMessage } from 'element-plus'
import ConfigHistoryModal from './ConfigHistoryModal.vue'

// Props
const props = defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  configs: {
    type: Object,
    required: true
  },
  category: {
    type: String,
    required: true
  }
})

// Store
const configStore = useConfigStore()

// State
const editDialogVisible = ref(false)
const historyDialogVisible = ref(false)
const currentRow = ref(null)
const currentHistoryKey = ref('')
const currentHistoryLabel = ref('')
const editForm = ref({
  value: null,
  description: ''
})

// Computed
const loading = computed(() => configStore.loading)
const saving = computed(() => configStore.saving)

// Modèles Mistral disponibles
const availableModels = [
  'mistral-embed',
  'mistral-small-latest',
  'mistral-medium-latest',
  'mistral-large-latest',
  'pixtral-12b',
  'mistral-ocr-latest'
]

// Extensions disponibles
const availableExtensions = [
  'pdf', 'docx', 'doc', 'xlsx', 'xls',
  'pptx', 'ppt', 'rtf', 'txt', 'md',
  'png', 'jpg', 'jpeg', 'webp'
]

/**
 * Transforme les configs en items de tableau
 */
const configItems = computed(() => {
  const items = []
  
  Object.entries(props.configs).forEach(([key, value]) => {
    const item = {
      key: `${props.category}.${key}`,
      label: formatLabel(key),
      description: value.description || '',
      current_value: value.value !== undefined ? value.value : value,
      type: detectType(key, value),
      unit: value.unit || '',
      min: getMinValue(key),
      max: getMaxValue(key),
      precision: getPrecision(key),
      step: getStep(key),
      range: getRange(key)
    }
    
    items.push(item)
  })
  
  return items
})

/**
 * Détecte le type d'une configuration
 */
function detectType(key, value) {
  // Type explicite pour modèles
  if (key.includes('model') && typeof value.model_name === 'string') {
    return 'model'
  }
  
  // Type explicite pour boolean
  if (typeof value.value === 'boolean') {
    return 'boolean'
  }
  
  // Type explicite pour arrays
  if (Array.isArray(value.value)) {
    return 'array'
  }
  
  // Type explicite pour numbers
  if (typeof value.value === 'number') {
    return 'number'
  }
  
  return 'string'
}

/**
 * Formate un label à partir d'une clé
 */
function formatLabel(key) {
  const labels = {
    'embedding': 'Embedding',
    'reranking': 'Reranking',
    'generation': 'Génération',
    'title_generation': 'Génération de titres',
    'ocr': 'OCR',
    'size': 'Taille des chunks',
    'overlap': 'Chevauchement',
    'min_size': 'Taille minimum',
    'max_size': 'Taille maximum',
    'batch_size': 'Taille de batch',
    'top_k': 'Nombre de résultats (top_k)',
    'hybrid_alpha': 'Alpha recherche hybride',
    'rerank_enabled': 'Reranking activé',
    'max_file_size_mb': 'Taille max fichier',
    'max_batch_size_mb': 'Taille max batch',
    'max_files_per_batch': 'Fichiers max par batch',
    'allowed_extensions': 'Extensions autorisées',
    'per_minute': 'Requêtes par minute',
    'per_hour': 'Requêtes par heure',
    'query_ttl_seconds': 'TTL cache requêtes',
    'config_ttl_seconds': 'TTL cache configs',
    'default_usd_xaf': 'Taux USD/XAF par défaut',
    'api_enabled': 'API taux activée',
    'update_frequency_hours': 'Fréquence mise à jour'
  }
  
  return labels[key] || key
}

/**
 * Formate une valeur pour l'affichage
 */
function formatValue(value) {
  if (typeof value === 'object' && value !== null) {
    if (value.model_name) return value.model_name
    if (value.value !== undefined) return value.value
    return JSON.stringify(value)
  }
  return value
}

/**
 * Retourne la valeur min selon la clé
 */
function getMinValue(key) {
  const mins = {
    'size': 50,
    'overlap': 0,
    'min_size': 10,
    'max_size': 100,
    'batch_size': 1,
    'top_k': 1,
    'hybrid_alpha': 0,
    'max_file_size_mb': 1,
    'max_batch_size_mb': 10,
    'max_files_per_batch': 1,
    'per_minute': 1,
    'per_hour': 1,
    'query_ttl_seconds': 60,
    'config_ttl_seconds': 60,
    'default_usd_xaf': 1,
    'update_frequency_hours': 1
  }
  return mins[key.split('.').pop()]
}

/**
 * Retourne la valeur max selon la clé
 */
function getMaxValue(key) {
  const maxs = {
    'size': 2048,
    'overlap': 512,
    'min_size': 500,
    'max_size': 4096,
    'batch_size': 100,
    'top_k': 100,
    'hybrid_alpha': 1,
    'max_file_size_mb': 500,
    'max_batch_size_mb': 5000,
    'max_files_per_batch': 100,
    'per_minute': 1000,
    'per_hour': 10000,
    'query_ttl_seconds': 86400,
    'config_ttl_seconds': 3600,
    'default_usd_xaf': 2000,
    'update_frequency_hours': 168
  }
  return maxs[key.split('.').pop()]
}

/**
 * Retourne la précision selon la clé
 */
function getPrecision(key) {
  const precisions = {
    'hybrid_alpha': 2,
    'default_usd_xaf': 3
  }
  return precisions[key.split('.').pop()]
}

/**
 * Retourne le step selon la clé
 */
function getStep(key) {
  const steps = {
    'hybrid_alpha': 0.05,
    'default_usd_xaf': 0.001
  }
  return steps[key.split('.').pop()] || 1
}

/**
 * Retourne la plage de valeurs selon la clé
 */
function getRange(key) {
  const ranges = {
    'size': 'Entre 50 et 2048 tokens',
    'overlap': 'Entre 0 et 512 tokens',
    'hybrid_alpha': '0 = BM25 uniquement, 1 = Sémantique uniquement',
    'top_k': 'Entre 1 et 100 résultats'
  }
  return ranges[key.split('.').pop()]
}

/**
 * Ouvre le modal d'édition
 */
function handleEdit(row) {
  currentRow.value = row
  editForm.value = {
    value: row.current_value,
    description: ''
  }
  editDialogVisible.value = true
}

/**
 * Ferme le modal d'édition
 */
function handleEditClose() {
  currentRow.value = null
  editForm.value = {
    value: null,
    description: ''
  }
}

/**
 * Enregistre les modifications
 */
async function handleSave() {
  if (!currentRow.value) return
  
  try {
    // Construire la nouvelle valeur selon le type
    let newValue
    
    if (currentRow.value.type === 'model') {
      newValue = {
        ...props.configs[currentRow.value.key.split('.').pop()],
        model_name: editForm.value.value
      }
    } else {
      newValue = {
        ...props.configs[currentRow.value.key.split('.').pop()],
        value: editForm.value.value
      }
    }
    
    await configStore.updateConfig(
      currentRow.value.key,
      newValue,
      editForm.value.description || null
    )
    
    // Rafraîchir la catégorie
    await configStore.fetchCategory(props.category)
    
    editDialogVisible.value = false
    handleEditClose()
  } catch (error) {
    console.error('Error saving config:', error)
  }
}

/**
 * Ouvre l'historique
 */
function handleHistory(row) {
  currentHistoryKey.value = row.key
  currentHistoryLabel.value = row.label
  historyDialogVisible.value = true
}
</script>

<style scoped>
.config-section {
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0 0 5px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.param-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.value-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.array-value {
  display: flex;
  flex-wrap: wrap;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

:deep(.el-card__header) {
  background-color: #f5f7fa;
}
</style>