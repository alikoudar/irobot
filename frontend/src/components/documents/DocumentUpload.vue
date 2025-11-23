<template>
  <div class="document-upload">
    <!-- Zone de sélection de catégorie -->
    <div class="upload-category">
      <label class="form-label">Catégorie de destination</label>
      <el-select
        v-model="selectedCategory"
        placeholder="Sélectionnez une catégorie"
        size="large"
        :loading="categoriesLoading"
        filterable
        class="category-select"
      >
        <el-option
          v-for="cat in categories"
          :key="cat.id"
          :label="cat.name"
          :value="cat.id"
        >
          <div class="category-option">
            <el-icon><Folder /></el-icon>
            <span>{{ cat.name }}</span>
            <span class="doc-count">{{ cat.document_count || 0 }} docs</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- Zone de drag & drop -->
    <el-upload
      ref="uploadRef"
      class="upload-dragger"
      drag
      multiple
      :auto-upload="false"
      :file-list="fileList"
      :on-change="handleFileChange"
      :on-remove="handleFileRemove"
      :before-upload="beforeUpload"
      :limit="10"
      :on-exceed="handleExceed"
      :accept="acceptedTypes"
    >
      <div class="upload-content">
        <el-icon class="upload-icon" :class="{ 'is-uploading': isUploading }">
          <UploadFilled />
        </el-icon>
        <div class="upload-text">
          <h3>Glissez vos fichiers ici</h3>
          <p>ou <em>cliquez pour sélectionner</em></p>
        </div>
        <div class="upload-tips">
          <el-tag size="small" type="info">PDF</el-tag>
          <el-tag size="small" type="info">DOCX</el-tag>
          <el-tag size="small" type="info">XLSX</el-tag>
          <el-tag size="small" type="info">PPTX</el-tag>
          <el-tag size="small" type="info">Images</el-tag>
          <el-tag size="small" type="info">TXT</el-tag>
        </div>
        <p class="upload-limit">Maximum 10 fichiers • 50 MB par fichier</p>
      </div>
    </el-upload>

    <!-- Liste des fichiers sélectionnés -->
    <div v-if="fileList.length > 0" class="selected-files">
      <div class="files-header">
        <h4>
          <el-icon><Document /></el-icon>
          {{ fileList.length }} fichier(s) sélectionné(s)
        </h4>
        <el-button text type="danger" @click="clearFiles">
          <el-icon><Delete /></el-icon>
          Tout supprimer
        </el-button>
      </div>
      
      <div class="files-list">
        <div
          v-for="(file, index) in fileList"
          :key="file.uid"
          class="file-item"
          :class="getFileStatus(file)"
        >
          <div class="file-icon">
            <el-icon :size="24">
              <component :is="getFileIconComponent(file.name)" />
            </el-icon>
          </div>
          
          <div class="file-info">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>
          
          <div class="file-status">
            <!-- Status pendant upload -->
            <template v-if="uploadingFiles[index]">
              <el-progress
                v-if="uploadingFiles[index].status === 'uploading'"
                :percentage="uploadingFiles[index].progress"
                :stroke-width="4"
                :show-text="false"
                class="file-progress"
              />
              <el-tag
                v-else-if="uploadingFiles[index].status === 'processing'"
                type="warning"
                size="small"
              >
                <el-icon class="is-loading"><Loading /></el-icon>
                Traitement...
              </el-tag>
              <el-tag
                v-else-if="uploadingFiles[index].status === 'completed'"
                type="success"
                size="small"
              >
                <el-icon><CircleCheck /></el-icon>
                Terminé
              </el-tag>
              <el-tag
                v-else-if="uploadingFiles[index].status === 'failed'"
                type="danger"
                size="small"
              >
                <el-icon><CircleClose /></el-icon>
                Échec
              </el-tag>
            </template>
          </div>
          
          <el-button
            v-if="!isUploading"
            text
            type="danger"
            @click="removeFile(file)"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- Progression globale -->
    <div v-if="isUploading" class="upload-progress">
      <div class="progress-header">
        <span>Upload en cours...</span>
        <span>{{ uploadProgress }}%</span>
      </div>
      <el-progress
        :percentage="uploadProgress"
        :stroke-width="8"
        :show-text="false"
        status="success"
      />
    </div>

    <!-- Boutons d'action -->
    <div class="upload-actions">
      <el-button @click="$emit('cancel')" :disabled="isUploading">
        Annuler
      </el-button>
      <el-button
        type="primary"
        :loading="isUploading"
        :disabled="!canUpload"
        @click="startUpload"
      >
        <el-icon v-if="!isUploading"><Upload /></el-icon>
        {{ isUploading ? 'Upload en cours...' : `Uploader ${fileList.length} fichier(s)` }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  UploadFilled,
  Document,
  Delete,
  Close,
  Upload,
  Folder,
  CircleCheck,
  CircleClose,
  Loading,
  DocumentCopy,
  Grid,
  PictureFilled,
  Tickets,
  Picture
} from '@element-plus/icons-vue'
import { useDocumentsStore } from '@/stores/documents'
import { ElMessage } from 'element-plus'

// Props & Emits
const props = defineProps({
  defaultCategory: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['success', 'cancel'])

// Store
const documentsStore = useDocumentsStore()

// Refs
const uploadRef = ref(null)
const selectedCategory = ref(props.defaultCategory)
const fileList = ref([])
const categoriesLoading = ref(false)

// Computed
const categories = computed(() => documentsStore.categories)
const isUploading = computed(() => documentsStore.isUploading)
const uploadProgress = computed(() => documentsStore.uploadProgress)
const uploadingFiles = computed(() => documentsStore.uploadingFiles)

const canUpload = computed(() => {
  return fileList.value.length > 0 && selectedCategory.value && !isUploading.value
})

const acceptedTypes = computed(() => {
  return '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.rtf,.png,.jpg,.jpeg,.webp,.gif'
})

// Methods
const formatSize = (bytes) => {
  return documentsStore.formatFileSize(bytes)
}

const getFileIconComponent = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
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
  return icons[ext] || Document
}

const getFileStatus = (file) => {
  const tracking = uploadingFiles.value.find(f => f.name === file.name)
  if (tracking) {
    return `status-${tracking.status}`
  }
  return ''
}

const handleFileChange = (file, newFileList) => {
  // Valider le fichier
  const maxSize = 50 * 1024 * 1024 // 50 MB
  if (file.raw.size > maxSize) {
    ElMessage.error(`Le fichier "${file.name}" dépasse la taille maximale de 50 MB`)
    return false
  }
  
  fileList.value = newFileList
}

const handleFileRemove = (file, newFileList) => {
  fileList.value = newFileList
}

const removeFile = (file) => {
  fileList.value = fileList.value.filter(f => f.uid !== file.uid)
  if (uploadRef.value) {
    uploadRef.value.handleRemove(file)
  }
}

const clearFiles = () => {
  fileList.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const handleExceed = (files) => {
  ElMessage.warning(`Maximum 10 fichiers autorisés. Vous avez sélectionné ${files.length} fichiers supplémentaires.`)
}

const beforeUpload = (file) => {
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error(`Le fichier "${file.name}" dépasse 50 MB`)
    return false
  }
  return true
}

const startUpload = async () => {
  if (!canUpload.value) return
  
  // Extraire les fichiers raw
  const files = fileList.value.map(f => f.raw)
  
  // Lancer l'upload
  const result = await documentsStore.uploadDocuments(files, selectedCategory.value)
  
  if (result) {
    emit('success', result)
    
    // Nettoyer après succès
    setTimeout(() => {
      clearFiles()
    }, 2000)
  }
}

// Lifecycle
onMounted(async () => {
  categoriesLoading.value = true
  await documentsStore.fetchCategories()
  categoriesLoading.value = false
  
  // Sélectionner la première catégorie par défaut
  if (!selectedCategory.value && categories.value.length > 0) {
    selectedCategory.value = categories.value[0].id
  }
})

// Watchers
watch(() => props.defaultCategory, (newVal) => {
  if (newVal) {
    selectedCategory.value = newVal
  }
})
</script>

<style scoped lang="scss">
.document-upload {
  padding: 24px;
}

.upload-category {
  margin-bottom: 24px;
  
  .form-label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text-primary, #1f2937);
  }
  
  .category-select {
    width: 100%;
  }
}

.category-option {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .doc-count {
    margin-left: auto;
    color: var(--text-secondary, #6b7280);
    font-size: 12px;
  }
}

.upload-dragger {
  width: 100%;
  
  :deep(.el-upload-dragger) {
    width: 100%;
    height: auto;
    padding: 40px 20px;
    border: 2px dashed var(--border-color, #dcdfe6);
    border-radius: 12px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: var(--primary-color, #409eff);
      background: var(--primary-light, #ecf5ff);
    }
  }
}

.upload-content {
  text-align: center;
  
  .upload-icon {
    font-size: 48px;
    color: var(--primary-color, #409eff);
    margin-bottom: 16px;
    
    &.is-uploading {
      animation: pulse 1.5s infinite;
    }
  }
  
  .upload-text {
    h3 {
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 4px;
      color: var(--text-primary, #1f2937);
    }
    
    p {
      color: var(--text-secondary, #6b7280);
      margin: 0;
      
      em {
        color: var(--primary-color, #409eff);
        font-style: normal;
        cursor: pointer;
      }
    }
  }
  
  .upload-tips {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-top: 16px;
    flex-wrap: wrap;
  }
  
  .upload-limit {
    margin-top: 12px;
    font-size: 12px;
    color: var(--text-muted, #9ca3af);
  }
}

.selected-files {
  margin-top: 24px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
  
  .files-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-secondary, #f9fafb);
    border-bottom: 1px solid var(--border-color, #e5e7eb);
    
    h4 {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
  }
  
  .files-list {
    max-height: 300px;
    overflow-y: auto;
  }
  
  .file-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color, #e5e7eb);
    transition: background 0.2s;
    
    &:last-child {
      border-bottom: none;
    }
    
    &:hover {
      background: var(--bg-hover, #f3f4f6);
    }
    
    &.status-completed {
      background: rgba(16, 185, 129, 0.05);
    }
    
    &.status-failed {
      background: rgba(239, 68, 68, 0.05);
    }
    
    .file-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--primary-light, #ecf5ff);
      border-radius: 8px;
      color: var(--primary-color, #409eff);
    }
    
    .file-info {
      flex: 1;
      min-width: 0;
      
      .file-name {
        display: block;
        font-weight: 500;
        color: var(--text-primary, #1f2937);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      
      .file-size {
        font-size: 12px;
        color: var(--text-secondary, #6b7280);
      }
    }
    
    .file-status {
      min-width: 100px;
      text-align: right;
      
      .file-progress {
        width: 80px;
      }
    }
  }
}

.upload-progress {
  margin-top: 24px;
  padding: 16px;
  background: var(--bg-secondary, #f9fafb);
  border-radius: 12px;
  
  .progress-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
  }
}

.upload-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color, #e5e7eb);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>