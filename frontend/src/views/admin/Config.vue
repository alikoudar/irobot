<template>
  <div class="config-management">
    <!-- Header avec gradient -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-icon-wrapper">
          <div class="header-icon">
            <el-icon :size="32"><Setting /></el-icon>
          </div>
          <div class="header-glow"></div>
        </div>
        <div>
          <h1>Configuration Système</h1>
          <el-text class="header-subtitle">
            Gestion centralisée des paramètres IroBot - Effet immédiat
          </el-text>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          size="large"
          @click="handleRefreshAll"
          :loading="loading"
          :icon="Refresh"
          class="refresh-button"
        >
          Actualiser
        </el-button>
      </div>
    </div>

    <!-- Alert moderne -->
    <el-alert
      :closable="false"
      class="success-alert"
    >
      <template #title>
        <div class="alert-content">
          <el-icon :size="20" class="alert-icon"><CircleCheck /></el-icon>
          <span class="alert-text">
            <strong>Modifications en temps réel</strong> - Toutes les modifications prennent effet
            <strong>immédiatement</strong> sans nécessiter de redémarrage
          </span>
        </div>
      </template>
    </el-alert>

    <el-card v-loading="loading">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- Tab Modèles -->
        <el-tab-pane label="Modèles Mistral" name="models">
          <template #label>
            <span>
              <el-icon><Box /></el-icon>
              Modèles
            </span>
          </template>
          
          <config-section
            title="Modèles Mistral AI"
            description="Configuration des modèles utilisés pour l'embedding, le reranking, la génération et l'OCR"
            :configs="configs.models"
            category="models"
          />
        </el-tab-pane>

        <!-- Tab Chunking -->
        <el-tab-pane label="Chunking" name="chunking">
          <template #label>
            <span>
              <el-icon><Grid /></el-icon>
              Chunking
            </span>
          </template>
          
          <config-section
            title="Paramètres de Chunking"
            description="Taille et chevauchement des chunks pour le découpage des documents"
            :configs="configs.chunking"
            category="chunking"
          />
        </el-tab-pane>

        <!-- Tab Recherche -->
        <el-tab-pane label="Recherche" name="search">
          <template #label>
            <span>
              <el-icon><Search /></el-icon>
              Recherche
            </span>
          </template>
          
          <config-section
            title="Paramètres de Recherche Hybride"
            description="Configuration de la recherche (BM25 + Sémantique) et du reranking"
            :configs="configs.search"
            category="search"
          />
        </el-tab-pane>

        <!-- Tab Cache -->
        <el-tab-pane label="Cache" name="cache">
          <template #label>
            <span>
              <el-icon><Timer /></el-icon>
              Cache
            </span>
          </template>
          
          <config-section
            title="Paramètres du Cache Redis"
            description="Durée de vie (TTL) des caches pour les requêtes et les configurations"
            :configs="configs.cache"
            category="cache"
          />
        </el-tab-pane>

        <!-- Tab Upload -->
        <el-tab-pane label="Upload" name="upload">
          <template #label>
            <span>
              <el-icon><Upload /></el-icon>
              Upload
            </span>
          </template>
          
          <config-section
            title="Paramètres d'Upload"
            description="Taille maximale des fichiers et extensions autorisées"
            :configs="configs.upload"
            category="upload"
          />
        </el-tab-pane>

        <!-- Tab Tarifs -->
        <el-tab-pane label="Tarifs Mistral" name="pricing">
          <template #label>
            <span>
              <el-icon><Coin /></el-icon>
              Tarifs
            </span>
          </template>
          
          <pricing-config :configs="configs.pricing" />
        </el-tab-pane>

        <!-- Tab Rate Limiting -->
        <el-tab-pane label="Rate Limiting" name="rate_limit">
          <template #label>
            <span>
              <el-icon><Warning /></el-icon>
              Rate Limit
            </span>
          </template>
          
          <config-section
            title="Limitation de Requêtes"
            description="Nombre maximum de requêtes par minute et par heure"
            :configs="configs.rate_limit"
            category="rate_limit"
          />
        </el-tab-pane>

        <!-- Tab Taux de change -->
        <el-tab-pane label="Taux de Change" name="exchange_rate">
          <template #label>
            <span>
              <el-icon><Money /></el-icon>
              Taux XAF
            </span>
          </template>
          
          <config-section
            title="Taux de Change USD/XAF"
            description="Configuration du taux de change et de la mise à jour automatique"
            :configs="configs.exchange_rate"
            category="exchange_rate"
          />
        </el-tab-pane>

        <!-- Tab Embedding -->
        <el-tab-pane label="Embedding" name="embedding">
          <template #label>
            <span>
              <el-icon><DataLine /></el-icon>
              Embedding
            </span>
          </template>
          
          <config-section
            title="Paramètres d'Embedding"
            description="Taille de batch pour les appels API d'embedding"
            :configs="configs.embedding"
            category="embedding"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Statistiques en bas -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card>
          <el-statistic title="Total Configurations" :value="totalConfigs">
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <el-statistic title="Catégories" :value="9">
            <template #prefix>
              <el-icon><Grid /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <el-statistic title="Dernière Modification" :value="lastModified">
            <template #prefix>
              <el-icon><Clock /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Refresh,
  Box,
  Grid,
  Search as SearchIcon,
  Timer,
  Upload as UploadIcon,
  Coin,
  Warning,
  Money,
  DataLine,
  Document,
  Clock,
  Setting,
  CircleCheck
} from '@element-plus/icons-vue'
import { useConfigStore } from '@/stores/config'
import { ElMessage } from 'element-plus'
import ConfigSection from '@/components/admin/ConfigSection.vue'
import PricingConfig from '@/components/admin/PricingConfig.vue'

// Store
const configStore = useConfigStore()

// State
const activeTab = ref('models')

// Computed
const loading = computed(() => configStore.loading)
const configs = computed(() => configStore.configs)
const totalConfigs = computed(() => {
  let count = 0
  Object.values(configs.value).forEach(category => {
    count += Object.keys(category).length
  })
  return count
})

const lastModified = computed(() => {
  // Retourne "Jamais" ou la date de la dernière modification
  // À implémenter si nécessaire en récupérant l'historique
  return 'Aujourd\'hui'
})

// Lifecycle
onMounted(async () => {
  await loadAllConfigs()
})

/**
 * Charge toutes les configurations
 */
async function loadAllConfigs() {
  try {
    await configStore.fetchAllCategories()
    console.log('✅ All configs loaded')
  } catch (error) {
    console.error('❌ Error loading configs:', error)
    ElMessage.error('Erreur lors du chargement des configurations')
  }
}

/**
 * Rafraîchit toutes les configurations
 */
async function handleRefreshAll() {
  try {
    await loadAllConfigs()
    ElMessage.success('Configurations actualisées')
  } catch (error) {
    console.error('❌ Error refreshing configs:', error)
  }
}
</script>

<style scoped>
.config-management {
  padding: 24px;
  background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon-wrapper {
  position: relative;
}

.header-icon {
  width: 72px;
  height: 72px;
  background: #005ca9;  /* ✅ Bleu BEAC solide */
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 24px rgba(0, 92, 169, 0.4);  /* ✅ Ombre bleu BEAC */
  position: relative;
  z-index: 2;
  transition: all 0.3s ease;
}

.header-icon:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 12px 32px rgba(0, 92, 169, 0.5);  /* ✅ Ombre bleu BEAC */
}

.header-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90px;
  height: 90px;
  background: radial-gradient(circle, rgba(0, 92, 169, 0.3) 0%, transparent 70%);  /* ✅ Glow bleu BEAC */
  border-radius: 50%;
  z-index: 1;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.6;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0.3;
    transform: translate(-50%, -50%) scale(1.1);
  }
}

.page-header h1 {
  margin: 0 0 4px 0;
  font-size: 32px;
  font-weight: 800;
  color: #005ca9;  /* ✅ Bleu BEAC comme Dashboard */
  letter-spacing: -0.5px;
}

.header-subtitle {
  font-size: 15px;
  color: #6b7280;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.refresh-button {
  border-radius: 12px;
  padding: 12px 24px;
  font-weight: 700;
  font-size: 15px;
  box-shadow: 0 4px 12px rgba(0, 92, 169, 0.3);  /* ✅ Ombre bleu BEAC */
  transition: all 0.3s ease;
}

.refresh-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 92, 169, 0.4);  /* ✅ Ombre bleu BEAC */
}

.success-alert {
  margin-bottom: 28px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-left: 4px solid #10b981;
  box-shadow: 0 2px 12px rgba(16, 185, 129, 0.1);
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-icon {
  color: #10b981;
}

.alert-text {
  font-size: 15px;
  color: #065f46;
  line-height: 1.6;
}

:deep(.el-tabs__item) {
  font-weight: 600;
  font-size: 15px;
  transition: all 0.3s ease;
  border-radius: 8px 8px 0 0;
}

.el-tabs__item:hover {
  background-color: #f9fafb;
}

:deep(.el-tabs__item.is-active) {
  color: #005ca9;  /* ✅ Bleu BEAC */
  background: linear-gradient(180deg, #e6f0f9 0%, white 100%);  /* ✅ Gradient bleu BEAC léger */
}

:deep(.el-tabs__active-bar) {
  background: #005ca9;  /* ✅ Bleu BEAC solide */
  height: 3px;
  border-radius: 3px 3px 0 0;
}

:deep(.el-card) {
  border: none;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: all 0.3s ease;
}

:deep(.el-card:hover) {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

:deep(.el-statistic__title) {
  font-size: 14px;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.el-statistic__number) {
  font-size: 28px;
  font-weight: 800;
  color: #005ca9;  /* ✅ Bleu BEAC solide */
}

:deep(.el-button--primary) {
  background: #005ca9;  /* ✅ Bleu BEAC */
  border: none;
}

:deep(.el-button--primary:hover) {
  background: #004a8a;  /* ✅ Bleu BEAC plus foncé au hover */
}
</style>