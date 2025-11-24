<template>
  <div class="sources-list">
    <!-- Header cliquable -->
    <div class="sources-header" @click="expanded = !expanded">
      <el-icon><Document /></el-icon>
      <span class="sources-title">{{ sources.length }} source{{ sources.length > 1 ? 's' : '' }}</span>
      <el-icon class="expand-icon" :class="{ expanded }">
        <ArrowDown />
      </el-icon>
    </div>
    
    <!-- Liste des sources -->
    <Transition name="expand">
      <div v-if="expanded" class="sources-content">
        <div
          v-for="(source, index) in sources"
          :key="index"
          class="source-item"
          @click="openSourceDetails(source)"
        >
          <span class="source-index">{{ index + 1 }}</span>
          <div class="source-info">
            <span class="source-title">{{ source.title || 'Document sans titre' }}</span>
            <div class="source-meta">
              <el-tag size="small" type="info">
                {{ source.category || 'Non catégorisé' }}
              </el-tag>
              <span v-if="source.page" class="source-page">Page {{ source.page }}</span>
              <span class="source-score" :class="getScoreClass(source.relevance_score)">
                {{ formatScore(source.relevance_score) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
    
    <!-- Modal détails avec PREVIEW DU CHUNK -->
    <el-dialog
      v-model="showDetails"
      :title="selectedSource?.title || 'Détails de la source'"
      width="650px"
      class="source-details-dialog"
    >
      <div class="source-details" v-if="selectedSource">
        <h4>Informations</h4>
        
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Catégorie</span>
            <el-tag>{{ selectedSource.category || 'Non catégorisé' }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">Page</span>
            <span class="info-value">{{ selectedSource.page || 'N/A' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Chunk</span>
            <span class="info-value">#{{ selectedSource.chunk_index ?? 'N/A' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Pertinence</span>
            <div class="relevance-bar">
              <el-progress
                :percentage="Math.round((selectedSource.relevance_score || 0) * 100)"
                :color="getProgressColor(selectedSource.relevance_score)"
                :stroke-width="10"
              />
            </div>
          </div>
        </div>
        
        <!-- Extrait / Preview du chunk -->
        <div class="excerpt-section">
          <h4>
            <el-icon><DocumentCopy /></el-icon>
            Extrait du document
          </h4>
          <div class="excerpt-box" v-if="excerptContent">
            {{ excerptContent }}
          </div>
          <div class="excerpt-empty" v-else>
            <el-icon><InfoFilled /></el-icon>
            <span>Aucun extrait disponible pour ce chunk.</span>
          </div>
        </div>
        
        <!-- Actions -->
        <div class="source-actions">
          <el-button 
            type="primary" 
            @click="copyExcerpt"
          >
            <el-icon><CopyDocument /></el-icon>
            Copier l'extrait
          </el-button>
          <el-button @click="showDetails = false">
            Fermer
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * SourcesList.vue
 * 
 * Liste des sources citées avec modal de détails.
 * 
 * CORRECTIONS V2 :
 * - Bouton "Copier l'extrait" TOUJOURS actif
 * - Affiche le chunk/excerpt au lieu de rediriger vers documents
 * - Pas de bouton "Voir le document" (utilisateurs n'ont pas accès)
 * 
 * Sprint 8 - CORRECTIONS V2
 */
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document,
  ArrowDown,
  CopyDocument,
  DocumentCopy,
  InfoFilled
} from '@element-plus/icons-vue'

// ============================================================================
// PROPS
// ============================================================================

defineProps({
  sources: {
    type: Array,
    default: () => []
  }
})

// ============================================================================
// STATE
// ============================================================================

const expanded = ref(false)
const showDetails = ref(false)
const selectedSource = ref(null)

// ============================================================================
// COMPUTED
// ============================================================================

/**
 * Contenu de l'extrait (excerpt ou text)
 */
const excerptContent = computed(() => {
  if (!selectedSource.value) return ''
  
  // Essayer différents champs possibles
  return selectedSource.value.excerpt 
      || selectedSource.value.text 
      || selectedSource.value.content 
      || selectedSource.value.chunk_text
      || ''
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Ouvrir les détails d'une source
 */
function openSourceDetails(source) {
  selectedSource.value = source
  showDetails.value = true
}

/**
 * Copier l'extrait - TOUJOURS ACTIF
 */
async function copyExcerpt() {
  const textToCopy = excerptContent.value 
    || selectedSource.value?.title 
    || 'Aucun contenu disponible'
  
  try {
    await navigator.clipboard.writeText(textToCopy)
    ElMessage.success('Contenu copié dans le presse-papiers !')
  } catch (err) {
    // Fallback
    try {
      const textArea = document.createElement('textarea')
      textArea.value = textToCopy
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      ElMessage.success('Contenu copié dans le presse-papiers !')
    } catch (e) {
      ElMessage.error('Impossible de copier')
    }
  }
}

/**
 * Formater le score de pertinence
 */
function formatScore(score) {
  if (score === null || score === undefined) return 'N/A'
  return `${Math.round(score * 100)}%`
}

/**
 * Classe CSS basée sur le score
 */
function getScoreClass(score) {
  if (!score) return ''
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

/**
 * Couleur de la barre de progression
 */
function getProgressColor(score) {
  if (!score) return '#909399'
  if (score >= 0.8) return '#10b981'
  if (score >= 0.6) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped lang="scss">
.sources-list {
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
  color: #005ca9;
  font-weight: 500;
  
  &:hover {
    background: #f1f5f9;
  }
  
  .sources-title {
    flex: 1;
  }
  
  .expand-icon {
    transition: transform 0.3s;
    
    &.expanded {
      transform: rotate(180deg);
    }
  }
}

.sources-content {
  padding: 0 12px 12px;
}

.source-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  margin-top: 8px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: #005ca9;
    box-shadow: 0 2px 8px rgba(0, 92, 169, 0.1);
  }
  
  .source-index {
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #005ca9 0%, #0077cc 100%);
    color: white;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
  }
  
  .source-info {
    flex: 1;
    min-width: 0;
    
    .source-title {
      display: block;
      font-weight: 500;
      color: #1f2937;
      margin-bottom: 6px;
      line-height: 1.4;
    }
    
    .source-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      
      .source-page {
        font-size: 12px;
        color: #6b7280;
      }
      
      .source-score {
        font-size: 12px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        
        &.high {
          background: #d1fae5;
          color: #059669;
        }
        
        &.medium {
          background: #fef3c7;
          color: #d97706;
        }
        
        &.low {
          background: #fee2e2;
          color: #dc2626;
        }
      }
    }
  }
}

// Transition expand
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}

// Modal
.source-details {
  h4 {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #374151;
    margin: 0 0 16px;
  }
  
  .info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
    
    .info-item {
      .info-label {
        display: block;
        font-size: 12px;
        color: #6b7280;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      
      .info-value {
        font-weight: 500;
        color: #1f2937;
      }
    }
    
    .relevance-bar {
      margin-top: 4px;
    }
  }
  
  .excerpt-section {
    margin-bottom: 24px;
    
    .excerpt-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      font-size: 14px;
      line-height: 1.7;
      color: #374151;
      max-height: 250px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    
    .excerpt-empty {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px;
      background: #fef3c7;
      border-radius: 8px;
      color: #92400e;
      font-size: 14px;
      
      .el-icon {
        font-size: 18px;
      }
    }
  }
  
  .source-actions {
    display: flex;
    gap: 12px;
    padding-top: 16px;
    border-top: 1px solid #e5e7eb;
  }
}

:deep(.source-details-dialog) {
  .el-dialog__header {
    padding: 20px 24px;
    border-bottom: 1px solid #e5e7eb;
    margin: 0;
  }
  
  .el-dialog__body {
    padding: 24px;
  }
}
</style>