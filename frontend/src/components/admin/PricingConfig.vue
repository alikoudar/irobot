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
        :data="pricingItems"
        stripe
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column
          label="Modèle"
          min-width="200"
        >
          <template #default="{ row }">
            <div class="param-cell">
              <strong>{{ row.model }}</strong>
              <el-text type="info" size="small" v-if="row.description">
                {{ row.description }}
              </el-text>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="Prix Input ($/M tokens)"
          min-width="150"
          align="center"
        >
          <template #default="{ row }">
            <el-tag v-if="row.price_input !== null">
              ${{ row.price_input.toFixed(2) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column
          label="Prix Output ($/M tokens)"
          min-width="150"
          align="center"
        >
          <template #default="{ row }">
            <el-tag v-if="row.price_output !== null" type="success">
              ${{ row.price_output.toFixed(2) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column
          label="Unité spéciale"
          min-width="150"
          align="center"
        >
          <template #default="{ row }">
            <el-tag v-if="row.price_pages !== null" type="warning">
              ${{ row.price_pages.toFixed(2) }} / 1000 pages
            </el-tag>
            <span v-else>-</span>
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
      :title="`Modifier ${currentRow?.model}`"
      width="600px"
      @close="handleEditClose"
    >
      <el-form
        v-if="currentRow"
        :model="editForm"
        label-position="top"
      >
        <!-- Prix Input -->
        <el-form-item
          v-if="currentRow.price_input !== null"
          label="Prix Input ($ par million de tokens)"
        >
          <el-input-number
            v-model="editForm.price_input"
            :min="0"
            :max="100"
            :precision="2"
            :step="0.01"
            style="width: 100%"
          />
        </el-form-item>

        <!-- Prix Output -->
        <el-form-item
          v-if="currentRow.price_output !== null"
          label="Prix Output ($ par million de tokens)"
        >
          <el-input-number
            v-model="editForm.price_output"
            :min="0"
            :max="100"
            :precision="2"
            :step="0.01"
            style="width: 100%"
          />
        </el-form-item>

        <!-- Prix Pages (pour OCR) -->
        <el-form-item
          v-if="currentRow.price_pages !== null"
          label="Prix ($ par 1000 pages)"
        >
          <el-input-number
            v-model="editForm.price_pages"
            :min="0"
            :max="100"
            :precision="2"
            :step="0.01"
            style="width: 100%"
          />
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

        <el-alert
          type="warning"
          :closable="false"
          show-icon
        >
          <template #title>
            ⚠️ Les modifications de tarifs affectent les calculs futurs uniquement
          </template>
        </el-alert>
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
  price_input: null,
  price_output: null,
  price_pages: null,
  description: ''
})

// Computed
const loading = computed(() => configStore.loading)
const saving = computed(() => configStore.saving)

/**
 * Transforme les configs de pricing en items de tableau
 */
const pricingItems = computed(() => {
  const items = []
  
  Object.entries(props.configs).forEach(([key, value]) => {
    // ✅ EXTRACTION DU DERNIER SEGMENT DE LA CLÉ
    // Si key = "mistral.embed" → lastPart = "embed"
    // Si key = "embed" → lastPart = "embed"
    const lastPart = key.split('.').pop()
    
    // ✅ CONSTRUCTION DE LA CLÉ DB COMPLÈTE
    // Clé DB = "mistral.pricing.embed"
    const dbKey = `mistral.pricing.${lastPart}`
    
    const item = {
      key: dbKey,  // ✅ Clé complète pour l'historique
      model: value.model || key,
      description: value.description || '',
      price_input: value.price_per_million_input !== undefined ? value.price_per_million_input : null,
      price_output: value.price_per_million_output !== undefined ? value.price_per_million_output : null,
      price_pages: value.price_per_thousand_pages !== undefined ? value.price_per_thousand_pages : null,
      unit: value.unit || 'tokens'
    }
    
    items.push(item)
  })
  
  return items.sort((a, b) => a.model.localeCompare(b.model))
})

/**
 * Ouvre le modal d'édition
 */
function handleEdit(row) {
  currentRow.value = row
  
  // Pré-remplir le formulaire
  editForm.value = {
    price_input: row.price_input,
    price_output: row.price_output,
    price_pages: row.price_pages,
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
    price_input: null,
    price_output: null,
    price_pages: null,
    description: ''
  }
}

/**
 * Sauvegarde les modifications
 */
async function handleSave() {
  if (!currentRow.value) return
  
  try {
    // Construire la nouvelle valeur
    const newValue = {
      model: currentRow.value.model,
      unit: currentRow.value.unit
    }
    
    // Ajouter les prix selon le type
    if (editForm.value.price_input !== null) {
      newValue.price_per_million_input = editForm.value.price_input
    }
    
    if (editForm.value.price_output !== null) {
      newValue.price_per_million_output = editForm.value.price_output
    }
    
    if (editForm.value.price_pages !== null) {
      newValue.price_per_thousand_pages = editForm.value.price_pages
    }
    
    if (currentRow.value.description) {
      newValue.description = currentRow.value.description
    }
    
    // Mettre à jour via le store
    await configStore.updateConfig(
      currentRow.value.key,  // ✅ Utilise la clé DB complète
      newValue,
      editForm.value.description
    )
    
    // ✅ CORRECTION : Rafraîchir la catégorie pricing pour affichage immédiat
    await configStore.fetchCategory('pricing')
    
    ElMessage.success('Tarif mis à jour avec succès')
    editDialogVisible.value = false
    handleEditClose()
  } catch (error) {
    console.error('Error updating pricing:', error)
    ElMessage.error('Erreur lors de la mise à jour du tarif')
  }
}

/**
 * Ouvre le modal d'historique
 */
function handleHistory(row) {
  currentHistoryKey.value = row.key  // ✅ Utilise la clé DB complète
  currentHistoryLabel.value = row.model
  historyDialogVisible.value = true
}
</script>

<style scoped>
.config-section {
  width: 100%;
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.param-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-cell strong {
  font-size: 14px;
  color: #303133;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

.el-button .el-icon {
  margin-right: 4px;
}
</style>