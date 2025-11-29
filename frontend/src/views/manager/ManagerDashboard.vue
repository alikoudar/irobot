<template>
  <div class="manager-dashboard">
    <div class="dashboard-header">
      <h1>📊 Mon Dashboard Manager</h1>
      
      <div class="date-filters">
        <el-radio-group v-model="selectedPeriod" @change="handlePeriodChange">
          <el-radio-button label="today">Aujourd'hui</el-radio-button>
          <el-radio-button label="7days">7 jours</el-radio-button>
          <el-radio-button label="30days">30 jours</el-radio-button>
          <el-radio-button label="custom">Personnalisé</el-radio-button>
        </el-radio-group>
        
        <el-date-picker
          v-if="selectedPeriod === 'custom'"
          v-model="customDateRange"
          type="daterange"
          range-separator="-"
          start-placeholder="Début"
          end-placeholder="Fin"
          @change="fetchStats"
        />
        
        <el-button :icon="Refresh" @click="fetchStats">Actualiser</el-button>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>
    
    <!-- Error State -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="error-alert"
    />
    
    <!-- Dashboard Content -->
    <div v-if="!loading && !error">
      <!-- KPI Cards -->
      <el-row :gutter="20" class="kpi-section">
        <el-col :span="8">
          <StatsCard
            title="Documents Traités"
            :value="animatedStats.docsCompleted.displayValue.value"
            :total="stats.documents?.total || 0"
            icon="Document"
            color="#67C23A"
          />
        </el-col>
        
        <el-col :span="8">
          <StatsCard
            title="Messages Générés"
            :value="animatedStats.messagesTotal.displayValue.value"
            subtitle="Utilisant mes documents"
            icon="ChatDotRound"
            color="#409EFF"
          />
        </el-col>
        
        <el-col :span="8">
          <StatsCard
            title="Taux de Complétion"
            :value="`${animatedStats.completionRate.displayValue.value}%`"
            :subtitle="`${animatedStats.docsProcessing.displayValue.value} en cours`"
            icon="CircleCheckFilled"
            :color="getCompletionColor(documentCompletionRate)"
          />
        </el-col>
      </el-row>
      
      <!-- Charts Section -->
      <el-row :gutter="20" class="charts-section">
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>📊 Documents par Catégorie</h3>
              </div>
            </template>
            <div class="chart-container">
              <Pie :data="categoryChartData" :options="pieChartOptions" />
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>🔝 Top 10 Documents</h3>
              </div>
            </template>
            <div class="chart-container">
              <Bar :data="topDocsChartData" :options="barChartOptions" />
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- Timeline Section -->
      <el-row :gutter="20" class="charts-section">
        <el-col :span="24">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>📈 Timeline des Uploads (30 jours)</h3>
              </div>
            </template>
            <div class="chart-container">
              <Line :data="timelineChartData" :options="lineChartOptions" />
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- Documents Info -->
      <el-row :gutter="20" class="info-section">
        <el-col :span="24">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>📋 Récapitulatif</h3>
              </div>
            </template>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="Total Documents">
                {{ animatedStats.docsTotal.displayValue.value }}
              </el-descriptions-item>
              <el-descriptions-item label="Documents Complétés">
                {{ animatedStats.docsCompleted.displayValue.value }}
              </el-descriptions-item>
              <el-descriptions-item label="Documents en Traitement">
                {{ animatedStats.docsProcessing.displayValue.value }}
              </el-descriptions-item>
              <el-descriptions-item label="Documents Échoués">
                {{ animatedStats.docsFailed.displayValue.value }}
              </el-descriptions-item>
              <el-descriptions-item label="Total Chunks">
                {{ animatedStats.totalChunks.displayValue.value }}
              </el-descriptions-item>
              <el-descriptions-item label="Messages Générés">
                {{ animatedStats.messagesTotal.displayValue.value }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Line, Pie, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement,
  Filler
} from 'chart.js'
import { Refresh } from '@element-plus/icons-vue'
import { useManagerDashboardStore } from '@/stores/managerDashboard'
import StatsCard from '@/components/dashboard/StatsCard.vue'
import { ElMessage } from 'element-plus'
import { useCountAnimation } from '@/composables/useCountAnimation'

// Register Chart.js components
ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement,
  Filler
)

const managerStore = useManagerDashboardStore()

// State
const selectedPeriod = ref('30days')
const customDateRange = ref([])
let refreshInterval = null

// Computed
const stats = computed(() => managerStore.stats)
const topDocs = computed(() => managerStore.topDocuments)
const timeline = computed(() => managerStore.timeline)
const loading = computed(() => managerStore.loading)
const error = computed(() => managerStore.error)
const documentCompletionRate = computed(() => managerStore.documentCompletionRate)

// ✨ ANIMATIONS - Créer des animations pour toutes les valeurs numériques
const animatedStats = {
  // KPI Cards (value seulement, pas total pour barres de progression)
  docsCompleted: useCountAnimation(computed(() => stats.value?.documents?.completed || 0)),
  docsProcessing: useCountAnimation(computed(() => stats.value?.documents?.processing || 0)),
  messagesTotal: useCountAnimation(computed(() => stats.value?.messages?.total || 0)),
  completionRate: useCountAnimation(computed(() => documentCompletionRate.value || 0), 1500, 0),
  
  // Récapitulatif (animer pour le tableau el-descriptions)
  docsTotal: useCountAnimation(computed(() => stats.value?.documents?.total || 0)),
  docsFailed: useCountAnimation(computed(() => stats.value?.documents?.failed || 0)),
  totalChunks: useCountAnimation(computed(() => stats.value?.documents?.total_chunks || 0))
}

// Methods
const fetchStats = async () => {
  let startDate, endDate
  
  switch (selectedPeriod.value) {
    case 'today':
      startDate = new Date()
      startDate.setHours(0, 0, 0, 0)
      endDate = new Date()
      break
    case '7days':
      startDate = new Date()
      startDate.setDate(startDate.getDate() - 7)
      endDate = new Date()
      break
    case '30days':
      startDate = new Date()
      startDate.setDate(startDate.getDate() - 30)
      endDate = new Date()
      break
    case 'custom':
      if (!customDateRange.value || customDateRange.value.length !== 2) {
        ElMessage.warning('Veuillez sélectionner une plage de dates')
        return
      }
      startDate = customDateRange.value[0]
      endDate = customDateRange.value[1]
      break
  }
  
  try {
    await Promise.all([
      managerStore.fetchStats(startDate, endDate),
      managerStore.fetchTopDocuments(10),
      managerStore.fetchTimeline(30)
    ])
  } catch (err) {
    ElMessage.error('Erreur lors du chargement des statistiques')
  }
}

const handlePeriodChange = () => {
  if (selectedPeriod.value !== 'custom') {
    fetchStats()
  }
}

const getCompletionColor = (rate) => {
  if (rate >= 90) return '#67C23A'
  if (rate >= 70) return '#E6A23C'
  return '#F56C6C'
}

// Chart data - Documents par Catégorie
const categoryChartData = computed(() => {
  const categories = stats.value.documents_by_category || []
  
  return {
    labels: categories.map(c => c.category),
    datasets: [{
      label: 'Documents',
      data: categories.map(c => c.count),
      backgroundColor: [
        '#409EFF',
        '#67C23A',
        '#E6A23C',
        '#F56C6C',
        '#909399',
        '#00D8FF',
        '#FF6384',
        '#36A2EB'
      ]
    }]
  }
})

// Chart data - Top Documents
const topDocsChartData = computed(() => ({
  labels: topDocs.value.map(d => d.title.substring(0, 30) + (d.title.length > 30 ? '...' : '')),
  datasets: [{
    label: 'Utilisations',
    data: topDocs.value.map(d => d.usage_count),
    backgroundColor: '#409EFF'
  }]
}))

// Chart data - Timeline
const timelineChartData = computed(() => ({
  labels: timeline.value.map(t => {
    const date = new Date(t.date)
    return `${date.getDate()}/${date.getMonth() + 1}`
  }),
  datasets: [{
    label: 'Documents Uploadés',
    data: timeline.value.map(t => t.documents_count),
    borderColor: '#67C23A',
    backgroundColor: 'rgba(103, 194, 58, 0.1)',
    tension: 0.4
  }]
}))

// Chart options
const pieChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right'
    }
  }
}

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  plugins: {
    legend: {
      display: false
    }
  },
  scales: {
    x: {
      beginAtZero: true
    }
  }
}

const lineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        stepSize: 1
      }
    }
  }
}

// Lifecycle
onMounted(() => {
  fetchStats()
  
  // Auto-refresh every 60 seconds
  refreshInterval = setInterval(() => {
    fetchStats()
  }, 60000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.manager-dashboard {
  padding: 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.date-filters {
  display: flex;
  gap: 12px;
  align-items: center;
}

.loading-container {
  padding: 40px;
}

.error-alert {
  margin-bottom: 20px;
}

.kpi-section {
  margin-bottom: 24px;
}

.charts-section {
  margin-bottom: 24px;
}

.info-section {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.chart-container {
  height: 350px;
  padding: 20px 0;
}

:deep(.el-card__header) {
  background-color: #f5f7fa;
  padding: 14px 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}
</style>