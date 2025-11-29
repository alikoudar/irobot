<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="`Historique: ${configLabel}`"
    width="900px"
    @open="handleOpen"
  >
    <div v-loading="loading">
      <el-alert
        v-if="history.length === 0 && !loading"
        title="Aucune modification"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        Aucune modification n'a été enregistrée pour cette configuration.
      </el-alert>

      <el-timeline v-else>
        <el-timeline-item
          v-for="(entry, index) in history"
          :key="index"
          :timestamp="formatDate(entry.created_at)"
          placement="top"
          :type="index === 0 ? 'primary' : ''"
        >
          <el-card>
            <template #header>
              <div class="entry-header">
                <div>
                  <el-text type="primary" strong>
                    {{ entry.user_email }}
                  </el-text>
                  <el-text type="info" size="small" style="margin-left: 10px;">
                    {{ getRelativeTime(entry.created_at) }}
                  </el-text>
                </div>
                <el-tag size="small" :type="getActionType(entry.action)">
                  {{ entry.action }}
                </el-tag>
              </div>
            </template>

            <!-- Ancienne valeur -->
            <div v-if="entry.details?.old_value" class="value-section">
              <el-text type="info" size="small" strong>Ancienne valeur :</el-text>
              <div class="value-display">
                <code>{{ formatValue(entry.details.old_value) }}</code>
              </div>
            </div>

            <!-- Nouvelle valeur -->
            <div v-if="entry.details?.new_value" class="value-section">
              <el-text type="success" size="small" strong>Nouvelle valeur :</el-text>
              <div class="value-display">
                <code>{{ formatValue(entry.details.new_value) }}</code>
              </div>
            </div>

            <!-- Description -->
            <div
              v-if="entry.details?.description"
              class="value-section"
              style="border-top: 1px solid #ebeef5; padding-top: 10px; margin-top: 10px;"
            >
              <el-text type="info" size="small" strong>Description :</el-text>
              <p style="margin: 5px 0 0 0;">{{ entry.details.description }}</p>
            </div>

            <!-- Différences -->
            <div
              v-if="entry.details?.old_value && entry.details?.new_value"
              class="diff-section"
            >
              <el-tag
                v-for="(change, key) in getChanges(entry.details.old_value, entry.details.new_value)"
                :key="key"
                size="small"
                type="warning"
                style="margin-right: 5px; margin-bottom: 5px;"
              >
                {{ key }}: {{ change.old }} → {{ change.new }}
              </el-tag>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">Fermer</el-button>
      <el-button
        type="primary"
        plain
        @click="handleRefresh"
        :loading="loading"
      >
        <el-icon><Refresh /></el-icon>
        Actualiser
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useConfigStore } from '@/stores/config'
import { ElMessage } from 'element-plus'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  configKey: {
    type: String,
    required: true
  },
  configLabel: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['update:modelValue'])

// Store
const configStore = useConfigStore()

// State
const loading = ref(false)
const history = ref([])

/**
 * Charge l'historique quand le modal s'ouvre
 */
async function handleOpen() {
  if (!props.configKey) return
  
  loading.value = true
  try {
    history.value = await configStore.fetchHistory(props.configKey)
  } catch (error) {
    console.error('Error loading history:', error)
    ElMessage.error('Erreur lors du chargement de l\'historique')
  } finally {
    loading.value = false
  }
}

/**
 * Rafraîchit l'historique
 */
async function handleRefresh() {
  await handleOpen()
  ElMessage.success('Historique actualisé')
}

/**
 * Watch pour recharger l'historique si la clé change
 */
watch(() => props.configKey, () => {
  if (props.modelValue && props.configKey) {
    handleOpen()
  }
})

/**
 * Formate une date
 */
function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Retourne le temps relatif
 */
function getRelativeTime(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'À l\'instant'
  if (diffMins === 1) return 'Il y a 1 minute'
  if (diffMins < 60) return `Il y a ${diffMins} minutes`
  if (diffHours === 1) return 'Il y a 1 heure'
  if (diffHours < 24) return `Il y a ${diffHours} heures`
  if (diffDays === 1) return 'Hier'
  if (diffDays < 7) return `Il y a ${diffDays} jours`
  if (diffDays < 30) return `Il y a ${Math.floor(diffDays / 7)} semaines`
  return `Il y a ${Math.floor(diffDays / 30)} mois`
}

/**
 * Retourne le type de tag selon l'action
 */
function getActionType(action) {
  const types = {
    'CREATE': 'success',
    'UPDATE': 'primary',
    'DELETE': 'danger'
  }
  return types[action] || ''
}

/**
 * Formate une valeur pour l'affichage
 */
function formatValue(value) {
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

/**
 * Calcule les différences entre deux valeurs
 */
function getChanges(oldValue, newValue) {
  const changes = {}
  
  if (typeof oldValue === 'object' && typeof newValue === 'object') {
    // Comparer les objets
    const allKeys = new Set([
      ...Object.keys(oldValue),
      ...Object.keys(newValue)
    ])
    
    allKeys.forEach(key => {
      const oldVal = oldValue[key]
      const newVal = newValue[key]
      
      if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
        changes[key] = {
          old: formatSimpleValue(oldVal),
          new: formatSimpleValue(newVal)
        }
      }
    })
  } else {
    // Valeurs simples
    if (oldValue !== newValue) {
      changes['value'] = {
        old: formatSimpleValue(oldValue),
        new: formatSimpleValue(newValue)
      }
    }
  }
  
  return changes
}

/**
 * Formate une valeur simple pour l'affichage
 */
function formatSimpleValue(value) {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.value-section {
  margin-bottom: 10px;
}

.value-display {
  background-color: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  margin-top: 5px;
  overflow-x: auto;
}

.value-display code {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #303133;
  white-space: pre-wrap;
}

.diff-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

:deep(.el-timeline-item__timestamp) {
  font-weight: 600;
  color: #606266;
}

:deep(.el-card__header) {
  padding: 12px 16px;
  background-color: #fafafa;
}
</style>