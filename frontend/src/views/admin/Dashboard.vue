<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <h1>Dashboard Administrateur</h1>
      
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
        <el-button :icon="Download" @click="exportStats">Exporter</el-button>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
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
        <el-col :span="6">
          <StatsCard
            title="Utilisateurs Actifs"
            :value="animatedStats.usersActive.displayValue.value"
            :total="stats.users?.total || 0"
            icon="User"
            color="#409EFF"
          />
        </el-col>
        
        <el-col :span="6">
          <StatsCard
            title="Documents Traités"
            :value="animatedStats.docsCompleted.displayValue.value"
            :total="stats.documents?.total || 0"
            icon="Document"
            color="#67C23A"
          />
        </el-col>
        
        <el-col :span="6">
          <StatsCard
            title="Messages"
            :value="animatedStats.messagesTotal.displayValue.value"
            subtitle="Total messages"
            icon="ChatDotRound"
            color="#E6A23C"
          />
        </el-col>
        
        <el-col :span="6">
          <StatsCard
            title="Taux de Satisfaction"
            :value="`${animatedStats.satisfactionRate.displayValue.value}%`"
            subtitle="Feedbacks positifs"
            icon="CircleCheckFilled"
            :color="getSatisfactionColor(stats.feedbacks?.satisfaction_rate)"
          />
        </el-col>
      </el-row>
      
      <!-- Cache Statistics -->
      <el-card class="cache-stats-card">
        <template #header>
          <div class="card-header">
            <h3>📊 Statistiques du Cache</h3>
          </div>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic
              title="Taux de Hit"
              :value="animatedStats.cacheHitRate.displayValue.value"
              suffix="%"
            >
              <template #prefix>
                <el-icon color="#67C23A"><CircleCheck /></el-icon>
              </template>
            </el-statistic>
          </el-col>
          
          <el-col :span="8">
            <el-statistic
              title="Tokens Économisés"
              :value="animatedStats.tokensSaved.displayValue.value"
              :precision="0"
            >
              <template #prefix>
                <el-icon color="#409EFF"><Coin /></el-icon>
              </template>
            </el-statistic>
          </el-col>
          
          <el-col :span="8">
            <el-statistic
              title="Coûts Économisés"
              :value="animatedStats.costSavedUSD.displayValue.value"
              prefix="$"
              :precision="2"
            />
          </el-col>
        </el-row>
        
        <div class="cache-details">
          <p>Cache Hits: <strong>{{ animatedStats.cacheHits.displayValue.value }}</strong></p>
          <p>Cache Misses: <strong>{{ animatedStats.cacheMisses.displayValue.value }}</strong></p>
          <p>Économie XAF: <strong>{{ formatXAF(animatedStats.costSavedXAF.displayValue.value) }}</strong></p>
        </div>
      </el-card>
      
      <!-- Token Usage & Costs -->
      <el-card class="token-stats-card">
        <template #header>
          <div class="card-header">
            <h3>💰 Utilisation des Tokens & Coûts</h3>
          </div>
        </template>
        
        <el-table :data="tokenTableData" stripe>
          <el-table-column prop="operation" label="Opération" min-width="180" />
          <el-table-column prop="count" label="Nombre d'appels" align="center" width="150" />
          <el-table-column prop="tokens" label="Tokens" align="right" width="120">
            <template #default="{ row }">
              {{ formatNumber(row.tokens) }}
            </template>
          </el-table-column>
          <el-table-column prop="cost_usd" label="Coût USD" align="right" width="120">
            <template #default="{ row }">
              ${{ row.cost_usd.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="cost_xaf" label="Coût XAF" align="right" min-width="150">
            <template #default="{ row }">
              {{ formatXAF(row.cost_xaf) }}
            </template>
          </el-table-column>
        </el-table>
        
        <div class="token-totals">
          <h4>Total</h4>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic
                title="Tokens Total"
                :value="animatedStats.tokensTotal.displayValue.value"
                :precision="0"
              />
            </el-col>
            <el-col :span="8">
              <el-statistic
                title="Coût Total USD"
                :value="animatedStats.totalCostUSD.displayValue.value"
                prefix="$"
                :precision="2"
              />
            </el-col>
            <el-col :span="8">
              <el-statistic
                title="Coût Total XAF"
                :value="animatedStats.totalCostXAF.displayValue.value"
                suffix=" FCFA"
                :precision="2"
              />
            </el-col>
          </el-row>
        </div>
      </el-card>
      
      <!-- Charts Section -->
      <el-row :gutter="20" class="charts-section">
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>📈 Activité sur 30 jours</h3>
              </div>
            </template>
            <div class="chart-container">
              <Line :data="activityChartData" :options="lineChartOptions" />
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>📊 Répartition des Documents</h3>
              </div>
            </template>
            <div class="chart-container">
              <Pie :data="documentsChartData" :options="pieChartOptions" />
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <el-row :gutter="20" class="charts-section">
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
        
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>👥 Utilisateurs Actifs</h3>
              </div>
            </template>
            <el-table :data="userActivityData" stripe max-height="400">
              <el-table-column prop="name" label="Utilisateur" min-width="150" />
              <el-table-column prop="matricule" label="Matricule" width="120" />
              <el-table-column prop="message_count" label="Messages" align="center" width="100" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Line, Pie, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  Filler,
  BarElement,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement
} from 'chart.js'
import { Refresh, Download, CircleCheck, Coin } from '@element-plus/icons-vue'
import { useDashboardStore } from '@/stores/dashboard'
import StatsCard from '@/components/dashboard/StatsCard.vue'
import { ElMessage } from 'element-plus'
import { useCountAnimation } from '@/composables/useCountAnimation'

// Register Chart.js components
ChartJS.register(
  Title,
  Tooltip,
  Legend,
  Filler,
  BarElement,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement
)

const dashboardStore = useDashboardStore()

// State
const selectedPeriod = ref('30days')
const customDateRange = ref([])
let refreshInterval = null

// Computed
const stats = computed(() => dashboardStore.stats)
const topDocs = computed(() => dashboardStore.topDocuments)
const activityTimeline = computed(() => dashboardStore.activityTimeline)
const userActivityData = computed(() => dashboardStore.userActivity)
const loading = computed(() => dashboardStore.loading)
const error = computed(() => dashboardStore.error)

// ✨ ANIMATIONS - Créer des animations pour toutes les valeurs numériques
const animatedStats = {
  // KPI Cards (value seulement, pas total pour barres de progression)
  usersActive: useCountAnimation(computed(() => stats.value?.users?.active || 0)),
  docsCompleted: useCountAnimation(computed(() => stats.value?.documents?.completed || 0)),
  messagesTotal: useCountAnimation(computed(() => stats.value?.messages?.total || 0)),
  satisfactionRate: useCountAnimation(computed(() => stats.value?.feedbacks?.satisfaction_rate || 0), 1500, 0),
  
  // Cache Stats
  cacheHitRate: useCountAnimation(computed(() => stats.value?.cache?.hit_rate || 0), 1500, 1),
  tokensSaved: useCountAnimation(computed(() => stats.value?.cache?.tokens_saved || 0)),
  costSavedUSD: useCountAnimation(computed(() => stats.value?.cache?.cost_saved_usd || 0), 1500, 2),
  cacheHits: useCountAnimation(computed(() => stats.value?.cache?.cache_hits || 0)),
  cacheMisses: useCountAnimation(computed(() => stats.value?.cache?.cache_misses || 0)),
  costSavedXAF: useCountAnimation(computed(() => stats.value?.cache?.cost_saved_xaf || 0), 1500, 0),
  
  // Token Stats Totals
  tokensTotal: useCountAnimation(computed(() => stats.value?.tokens?.total?.total_tokens || 0)),
  totalCostUSD: useCountAnimation(computed(() => stats.value?.tokens?.total?.total_cost_usd || 0), 1500, 2),
  totalCostXAF: useCountAnimation(computed(() => stats.value?.tokens?.total?.total_cost_xaf || 0), 1500, 2)
}

// Date Range Helpers
const getDateRange = () => {
  const now = new Date()
  let startDate, endDate

  if (selectedPeriod.value === 'custom') {
    if (!customDateRange.value || customDateRange.value.length !== 2) {
      return { startDate: null, endDate: null }
    }
    startDate = customDateRange.value[0]
    endDate = customDateRange.value[1]
  } else {
    endDate = now
    
    const start = new Date()
    if (selectedPeriod.value === 'today') {
      start.setHours(0, 0, 0, 0)
    } else if (selectedPeriod.value === '7days') {
      start.setDate(start.getDate() - 7)
    } else {
      start.setDate(start.getDate() - 30)
    }
    startDate = start
  }

  return { startDate, endDate }
}

const fetchStats = async () => {
  try {
    const { startDate, endDate } = getDateRange()
    
    await Promise.all([
      dashboardStore.fetchStats(startDate, endDate),
      dashboardStore.fetchTopDocuments(10, startDate, endDate),
      dashboardStore.fetchActivityTimeline(30),
      dashboardStore.fetchUserActivity(startDate, endDate)
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

const exportStats = async () => {
  try {
    await dashboardStore.exportStats('csv')
    ElMessage.success('Export réussi')
  } catch (err) {
    ElMessage.error('Erreur lors de l\'export')
  }
}

// Chart data
const tokenTableData = computed(() => {
  if (!stats.value?.tokens) return []
  
  return [
    {
      operation: 'Embedding',
      count: stats.value.tokens.EMBEDDING?.count || 0,
      tokens: stats.value.tokens.EMBEDDING?.total_tokens || 0,
      cost_usd: stats.value.tokens.EMBEDDING?.total_cost_usd || 0,
      cost_xaf: stats.value.tokens.EMBEDDING?.total_cost_xaf || 0
    },
    {
      operation: 'Reranking',
      count: stats.value.tokens.RERANKING?.count || 0,
      tokens: stats.value.tokens.RERANKING?.total_tokens || 0,
      cost_usd: stats.value.tokens.RERANKING?.total_cost_usd || 0,
      cost_xaf: stats.value.tokens.RERANKING?.total_cost_xaf || 0
    },
    {
      operation: 'Titres Conversations',
      count: stats.value.tokens.TITLE_GENERATION?.count || 0,
      tokens: stats.value.tokens.TITLE_GENERATION?.total_tokens || 0,
      cost_usd: stats.value.tokens.TITLE_GENERATION?.total_cost_usd || 0,
      cost_xaf: stats.value.tokens.TITLE_GENERATION?.total_cost_xaf || 0
    },
    {
      operation: 'Génération Réponses',
      count: stats.value.tokens.RESPONSE_GENERATION?.count || 0,
      tokens: stats.value.tokens.RESPONSE_GENERATION?.total_tokens || 0,
      cost_usd: stats.value.tokens.RESPONSE_GENERATION?.total_cost_usd || 0,
      cost_xaf: stats.value.tokens.RESPONSE_GENERATION?.total_cost_xaf || 0
    }
  ]
})

const activityChartData = computed(() => ({
  labels: activityTimeline.value.map(d => new Date(d.date).toLocaleDateString('fr-FR')),
  datasets: [
    {
      label: 'Messages',
      data: activityTimeline.value.map(d => d.messages),
      borderColor: '#409EFF',
      backgroundColor: 'rgba(64, 158, 255, 0.1)',
      tension: 0.4,
      fill: true
    },
    {
      label: 'Documents',
      data: activityTimeline.value.map(d => d.documents),
      borderColor: '#67C23A',
      backgroundColor: 'rgba(103, 194, 58, 0.1)',
      tension: 0.4,
      fill: true
    }
  ]
}))

const documentsChartData = computed(() => ({
  labels: ['Complétés', 'En cours', 'Échoués'],
  datasets: [{
    data: [
      stats.value?.documents?.completed || 0,
      stats.value?.documents?.processing || 0,
      stats.value?.documents?.failed || 0
    ],
    backgroundColor: ['#67C23A', '#E6A23C', '#F56C6C']
  }]
}))

const topDocsChartData = computed(() => ({
  labels: topDocs.value.map(d => d.title.substring(0, 30) + (d.title.length > 30 ? '...' : '')),
  datasets: [{
    label: 'Utilisations',
    data: topDocs.value.map(d => d.usage_count),
    backgroundColor: '#005ca9'
  }]
}))

const lineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { 
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 15
      }
    },
    tooltip: {
      mode: 'index',
      intersect: false
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        precision: 0
      }
    }
  }
}

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
      beginAtZero: true,
      ticks: {
        precision: 0
      }
    }
  }
}

const formatNumber = (num) => {
  return new Intl.NumberFormat('fr-FR').format(num)
}

const formatXAF = (amount) => {
  return new Intl.NumberFormat('fr-FR').format(amount) + ' FCFA'
}

const getSatisfactionColor = (rate) => {
  if (!rate) return '#909399'
  if (rate >= 80) return '#67C23A'
  if (rate >= 60) return '#E6A23C'
  return '#F56C6C'
}

// Lifecycle
onMounted(() => {
  fetchStats()
  // Auto-refresh every 30 seconds
  refreshInterval = setInterval(fetchStats, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style lang="scss" scoped>
.admin-dashboard {
  padding: 20px;
  max-width: 1800px;
  margin: 0 auto;
  
  .dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
    
    h1 {
      margin: 0;
      color: #005ca9;
      font-size: 28px;
      font-weight: 600;
    }
    
    .date-filters {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
  }
  
  .loading-container {
    padding: 40px 0;
  }
  
  .error-alert {
    margin-bottom: 20px;
  }
  
  .kpi-section {
    margin-bottom: 24px;
  }
  
  .cache-stats-card,
  .token-stats-card {
    margin-bottom: 24px;
    
    .card-header {
      h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #303133;
      }
    }
    
    .cache-details,
    .token-totals {
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid #EBEEF5;
      
      h4 {
        margin: 0 0 16px 0;
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }
      
      p {
        margin: 8px 0;
        color: #606266;
        
        strong {
          color: #303133;
          font-weight: 600;
        }
      }
    }
  }
  
  .charts-section {
    margin-bottom: 24px;
    
    .el-card {
      height: 100%;
      
      .card-header {
        h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #303133;
        }
      }
    }
    
    .chart-container {
      height: 350px;
      padding: 10px 0;
    }
  }
}

:deep(.el-statistic) {
  .el-statistic__head {
    font-size: 14px;
    color: #909399;
    margin-bottom: 8px;
  }
  
  .el-statistic__content {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
  }
}

:deep(.el-table) {
  font-size: 14px;
}
</style>