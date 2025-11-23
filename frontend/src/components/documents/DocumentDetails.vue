<template>
  <div class="document-details">
    <!-- Header avec statut -->
    <div class="details-header">
      <div class="file-icon-large" :class="document.file_extension">
        <el-icon :size="32">
          <component :is="getFileIcon(document.file_extension)" />
        </el-icon>
      </div>
      <div class="file-info">
        <h3>{{ document.original_filename }}</h3>
        <div class="file-meta">
          <span>{{ formatSize(document.file_size_bytes) }}</span>
          <span v-if="document.page_count">• {{ document.page_count }} pages</span>
          <span>• {{ document.file_extension?.toUpperCase() }}</span>
        </div>
      </div>
      <el-tag
        :type="getStatusColor(document.status)"
        size="large"
        class="status-tag"
      >
        <el-icon v-if="document.status === 'PROCESSING'" class="is-loading">
          <Loading />
        </el-icon>
        {{ getStatusLabel(document.status) }}
      </el-tag>
    </div>

    <!-- Message d'erreur -->
    <el-alert
      v-if="document.status === 'FAILED' && document.error_message"
      type="error"
      :closable="false"
      class="error-alert"
    >
      <template #title>
        <strong>Erreur de traitement</strong>
      </template>
      {{ document.error_message }}
    </el-alert>

    <!-- Pipeline de traitement -->
    <div class="processing-pipeline">
      <h4>Pipeline de traitement</h4>
      <el-steps
        :active="getActiveStep(document)"
        :process-status="getProcessStatus(document)"
        finish-status="success"
        align-center
      >
        <el-step title="Validation" :icon="Check" />
        <el-step title="Extraction" :icon="Document" />
        <el-step title="Découpage" :icon="Scissor" />
        <el-step title="Embedding" :icon="Connection" />
        <el-step title="Indexation" :icon="Search" />
      </el-steps>
    </div>

    <!-- Informations détaillées -->
    <div class="details-grid">
      <div class="detail-item">
        <span class="label">Catégorie</span>
        <span class="value">
          <el-tag size="small" type="info">{{ getCategoryName(document.category_id) }}</el-tag>
        </span>
      </div>
      
      <div class="detail-item">
        <span class="label">Uploadé par</span>
        <span class="value">{{ getUploaderName(document) }}</span>
      </div>
      
      <div class="detail-item">
        <span class="label">Date d'upload</span>
        <span class="value">{{ formatDate(document.uploaded_at) }}</span>
      </div>
      
      <div class="detail-item">
        <span class="label">Traitement terminé</span>
        <span class="value">{{ document.processed_at ? formatDate(document.processed_at) : '-' }}</span>
      </div>
      
      <div class="detail-item">
        <span class="label">Nombre de chunks</span>
        <span class="value">{{ document.total_chunks || '-' }}</span>
      </div>
      
      <div class="detail-item">
        <span class="label">Tentatives</span>
        <span class="value">{{ document.retry_count || 0 }}</span>
      </div>
      
      <div class="detail-item">
        <span class="label">Temps de traitement</span>
        <span class="value">{{ getTotalProcessingTime(document) }}</span>
      </div>
      
      <div class="detail-item">
        <span class="label">Coût total</span>
        <span class="value">{{ getTotalCost(document) }}</span>
      </div>
    </div>

    <!-- Statistiques de traitement (si disponibles) -->
    <div v-if="document.document_metadata" class="processing-stats">
      <h4>Statistiques de traitement</h4>
      
      <div class="stats-grid">
        <!-- Extraction -->
        <div v-if="document.document_metadata.extraction_method" class="stat-item">
          <span class="stat-label">Méthode d'extraction</span>
          <span class="stat-value">{{ document.document_metadata.extraction_method }}</span>
        </div>
        
        <div v-if="document.document_metadata.total_images_ocr" class="stat-item">
          <span class="stat-label">Images OCR</span>
          <span class="stat-value">{{ document.document_metadata.total_images_ocr }}</span>
        </div>
        
        <!-- Chunking -->
        <div v-if="document.document_metadata.chunking_stats" class="stat-item">
          <span class="stat-label">Temps de découpage</span>
          <span class="stat-value">
            {{ document.document_metadata.chunking_stats.chunking_time_seconds?.toFixed(2) }}s
          </span>
        </div>
        
        <!-- Embedding -->
        <div v-if="document.document_metadata.embedding_stats" class="stat-item">
          <span class="stat-label">Tokens embedding</span>
          <span class="stat-value">
            {{ document.document_metadata.embedding_stats.total_tokens?.toLocaleString() }}
          </span>
        </div>
        
        <div v-if="document.document_metadata.embedding_stats?.cost_usd" class="stat-item">
          <span class="stat-label">Coût embedding</span>
          <span class="stat-value">
            ${{ document.document_metadata.embedding_stats.cost_usd?.toFixed(6) }}
            <span class="secondary">
              ({{ document.document_metadata.embedding_stats.cost_xaf?.toFixed(2) }} XAF)
            </span>
          </span>
        </div>
        
        <!-- Temps total -->
        <div v-if="document.processing_time_seconds" class="stat-item full-width">
          <span class="stat-label">Temps total de traitement</span>
          <span class="stat-value">{{ formatDuration(document.processing_time_seconds) }}</span>
        </div>
      </div>
    </div>

    <!-- Hash du fichier -->
    <div class="file-hash">
      <span class="label">Hash SHA-256</span>
      <code>{{ document.file_hash || 'Non disponible' }}</code>
    </div>

    <!-- Actions -->
    <div class="details-actions">
      <el-button
        v-if="document.status === 'FAILED'"
        type="warning"
        @click="$emit('retry', document)"
      >
        <el-icon><RefreshRight /></el-icon>
        Relancer le traitement
      </el-button>
      
      <el-button
        type="danger"
        plain
        @click="$emit('delete', document)"
      >
        <el-icon><Delete /></el-icon>
        Supprimer
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Document,
  Loading,
  Check,
  Connection,
  Search,
  Delete,
  RefreshRight,
  DocumentCopy,
  Grid,
  PictureFilled,
  Tickets,
  Picture,
  Scissor
} from '@element-plus/icons-vue'
import { useDocumentsStore } from '@/stores/documents'

// Props
const props = defineProps({
  document: {
    type: Object,
    required: true
  }
})

// Emits
defineEmits(['retry', 'delete'])

// Store
const documentsStore = useDocumentsStore()

// Methods
const getFileIcon = (extension) => {
  const icons = {
    pdf: DocumentCopy,
    docx: Document,
    doc: Document,
    xlsx: Grid,
    xls: Grid,
    pptx: PictureFilled,
    ppt: PictureFilled,
    txt: Tickets,
    md: Tickets,
    png: Picture,
    jpg: Picture,
    jpeg: Picture,
    webp: Picture
  }
  return icons[extension?.toLowerCase()] || Document
}

const formatSize = (bytes) => {
  return documentsStore.formatFileSize(bytes)
}

const getStatusColor = (status) => {
  return documentsStore.getStatusColor(status)
}

const getStatusLabel = (status) => {
  return documentsStore.getStatusLabel(status)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(dateString))
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`
  }
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}m ${secs.toFixed(0)}s`
}

/**
 * Récupère le nom de l'utilisateur qui a uploadé le document
 * Utilise le nouveau champ uploader_name retourné par le backend
 */
const getUploaderName = (doc) => {
  // Nouveau champ ajouté au backend
  if (doc.uploader_name) return doc.uploader_name
  
  // Fallbacks pour compatibilité
  if (doc.uploaded_by_name) return doc.uploaded_by_name
  if (doc.uploader?.full_name) return doc.uploader.full_name
  if (doc.uploader?.nom && doc.uploader?.prenom) {
    return `${doc.uploader.prenom} ${doc.uploader.nom}`
  }
  
  return 'Utilisateur'
}

/**
 * Calcule le temps total de traitement
 * Utilise le nouveau champ total_processing_time_seconds si disponible
 */
const getTotalProcessingTime = (doc) => {
  // Nouveau champ calculé par le backend
  if (doc.total_processing_time_seconds) {
    return formatDuration(doc.total_processing_time_seconds)
  }
  
  // Fallback: calculer depuis les temps individuels
  let totalSeconds = 0
  
  if (doc.extraction_time_seconds) totalSeconds += doc.extraction_time_seconds
  if (doc.chunking_time_seconds) totalSeconds += doc.chunking_time_seconds
  if (doc.embedding_time_seconds) totalSeconds += doc.embedding_time_seconds
  if (doc.indexing_time_seconds) totalSeconds += doc.indexing_time_seconds
  
  if (totalSeconds === 0) return '-'
  return formatDuration(totalSeconds)
}

/**
 * Récupère le coût total du traitement
 * Utilise les nouveaux champs total_cost_usd et total_cost_xaf
 */
const getTotalCost = (doc) => {
  // Nouveaux champs ajoutés au backend
  const costUsd = doc.total_cost_usd || 0
  const costXaf = doc.total_cost_xaf || 0
  
  if (costUsd === 0 && costXaf === 0) return '-'
  
  return `$${costUsd.toFixed(6)} (${costXaf.toFixed(2)} XAF)`
}

/**
 * Récupère le nom de la catégorie
 * Utilise le nouveau champ category_name si disponible
 */
const getCategoryName = (categoryId) => {
  // Si le document a déjà le nom de la catégorie (nouveau backend)
  if (props.document?.category_name) {
    return props.document.category_name
  }
  
  // Fallback: chercher dans le store
  if (!categoryId) return 'Non classé'
  const category = categoriesStore.categories.find(c => c.id === categoryId)
  return category?.name || 'Catégorie inconnue'
}

const getActiveStep = (doc) => {
  const stages = ['VALIDATION', 'EXTRACTION', 'CHUNKING', 'EMBEDDING', 'INDEXING']
  const stageIndex = stages.indexOf(doc.processing_stage)
  
  if (doc.status === 'COMPLETED') {
    return 5 // Toutes les étapes terminées
  }
  
  if (doc.status === 'FAILED') {
    return stageIndex >= 0 ? stageIndex : 0
  }
  
  return stageIndex >= 0 ? stageIndex : 0
}

const getProcessStatus = (doc) => {
  if (doc.status === 'FAILED') {
    return 'error'
  }
  if (doc.status === 'PROCESSING') {
    return 'process'
  }
  return 'success'
}
</script>

<style scoped lang="scss">
.document-details {
  padding: 8px 0;
}

.details-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  
  .file-icon-large {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--primary-light, #ecf5ff);
    color: var(--primary-color, #409eff);
    flex-shrink: 0;

    &.pdf {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }

    &.docx, &.doc {
      background: rgba(59, 130, 246, 0.1);
      color: #3b82f6;
    }

    &.xlsx, &.xls {
      background: rgba(16, 185, 129, 0.1);
      color: #10b981;
    }

    &.pptx, &.ppt {
      background: rgba(245, 158, 11, 0.1);
      color: #f59e0b;
    }
  }
  
  .file-info {
    flex: 1;
    min-width: 0;
    
    h3 {
      margin: 0 0 4px;
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary, #1f2937);
      word-break: break-word;
    }
    
    .file-meta {
      font-size: 14px;
      color: var(--text-secondary, #6b7280);
      
      span:not(:last-child)::after {
        content: ' ';
      }
    }
  }
  
  .status-tag {
    flex-shrink: 0;
  }
}

.error-alert {
  margin-bottom: 24px;
}

.processing-pipeline {
  margin-bottom: 24px;
  padding: 20px;
  background: var(--bg-secondary, #f9fafb);
  border-radius: 12px;
  
  h4 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary, #1f2937);
  }
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  
  .detail-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    
    .label {
      font-size: 12px;
      color: var(--text-secondary, #6b7280);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .value {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #1f2937);
    }
  }
}

.processing-stats {
  margin-bottom: 24px;
  padding: 20px;
  background: var(--bg-secondary, #f9fafb);
  border-radius: 12px;
  
  h4 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary, #1f2937);
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    
    .stat-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 12px;
      background: white;
      border-radius: 8px;
      
      &.full-width {
        grid-column: span 2;
      }
      
      .stat-label {
        font-size: 12px;
        color: var(--text-secondary, #6b7280);
      }
      
      .stat-value {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary, #1f2937);
        
        .secondary {
          font-weight: 400;
          color: var(--text-secondary, #6b7280);
        }
      }
    }
  }
}

.file-hash {
  margin-bottom: 24px;
  
  .label {
    display: block;
    font-size: 12px;
    color: var(--text-secondary, #6b7280);
    margin-bottom: 4px;
  }
  
  code {
    display: block;
    padding: 12px;
    background: var(--bg-secondary, #f3f4f6);
    border-radius: 8px;
    font-size: 12px;
    font-family: monospace;
    color: var(--text-primary, #1f2937);
    word-break: break-all;
  }
}

.details-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color, #e5e7eb);
}
</style>
