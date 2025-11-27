<template>
  <div class="feedback-stats">
    <!-- Ligne 1 : 3 cards (Total, Satisfaction, Feedback Rate) -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <!-- Card 1 : Total Feedbacks -->
      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="stat-card stat-card-total">
          <el-statistic title="Total Feedbacks" :value="animatedTotal">
            <template #prefix>
              <el-icon><ChatDotRound /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>

      <!-- Card 2 : Taux de Satisfaction -->
      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="stat-card stat-card-satisfaction">
          <el-statistic 
            title="Taux de Satisfaction" 
            :value="animatedSatisfaction"
            suffix="%"
            :precision="1"
          >
            <template #prefix>
              <el-icon><TrendCharts /></el-icon>
            </template>
          </el-statistic>
          <el-progress 
            :percentage="animatedSatisfaction" 
            :show-text="false" 
            :stroke-width="8"
            :color="satisfactionColor"
          />
        </el-card>
      </el-col>

      <!-- Card 3 : Taux de Feedback -->
      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="stat-card stat-card-feedback-rate">
          <el-statistic 
            title="Taux de Feedback" 
            :value="animatedFeedbackRate"
            suffix="%"
            :precision="1"
          >
            <template #prefix>
              <el-icon><DataLine /></el-icon>
            </template>
          </el-statistic>
          <div style="margin-top: 8px; color: #909399; font-size: 12px;">
            {{ stats.total_feedbacks }} / {{ stats.total_messages }} messages
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Ligne 2 : 3 cards (Commentaires, Positifs, Négatifs) -->
    <el-row :gutter="20">
      <!-- Card 4 : Avec Commentaires -->
      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="stat-card stat-card-comments">
          <el-statistic title="Avec Commentaires" :value="animatedComments">
            <template #prefix>
              <el-icon><ChatLineRound /></el-icon>
            </template>
          </el-statistic>
          <div style="margin-top: 8px; color: #909399; font-size: 12px;">
            {{ commentPercentage }}% des feedbacks
          </div>
        </el-card>
      </el-col>

      <!-- Card 5 : Positifs (fond vert) -->
      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="stat-card stat-card-colored stat-card-positive">
          <el-statistic title="Positifs (👍)" :value="animatedThumbsUp">
            <template #prefix>
              <el-icon><CircleCheck /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>

      <!-- Card 6 : Négatifs (fond rouge) -->
      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="stat-card stat-card-colored stat-card-negative">
          <el-statistic title="Négatifs (👎)" :value="animatedThumbsDown">
            <template #prefix>
              <el-icon><CircleClose /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { useCountAnimation } from '@/composables/useCountAnimation'
import {
  ChatDotRound,
  TrendCharts,
  DataLine,
  ChatLineRound,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'

const props = defineProps({
  stats: {
    type: Object,
    required: true,
    default: () => ({
      total_feedbacks: 0,
      thumbs_up: 0,
      thumbs_down: 0,
      with_comments: 0,
      satisfaction_rate: 0,
      feedback_rate: 0,
      total_messages: 0
    })
  },
  trends: {
    type: Array,
    default: () => []
  }
})

// CORRECTIF : Créer des computed réactives pour chaque valeur
const totalFeedbacksRef = computed(() => props.stats.total_feedbacks || 0)
const thumbsUpRef = computed(() => props.stats.thumbs_up || 0)
const thumbsDownRef = computed(() => props.stats.thumbs_down || 0)
const withCommentsRef = computed(() => props.stats.with_comments || 0)
const satisfactionRateRef = computed(() => props.stats.satisfaction_rate || 0)
const feedbackRateRef = computed(() => props.stats.feedback_rate || 0)

// CORRECTIF : Créer les animations avec les computed réactives
const { displayValue: animatedTotal } = useCountAnimation(totalFeedbacksRef, 1500, 0)
const { displayValue: animatedThumbsUp } = useCountAnimation(thumbsUpRef, 1500, 0)
const { displayValue: animatedThumbsDown } = useCountAnimation(thumbsDownRef, 1500, 0)
const { displayValue: animatedComments } = useCountAnimation(withCommentsRef, 1500, 0)
const { displayValue: animatedSatisfaction } = useCountAnimation(satisfactionRateRef, 1500, 1)
const { displayValue: animatedFeedbackRate } = useCountAnimation(feedbackRateRef, 1500, 1)

// Calculer le pourcentage de commentaires
const commentPercentage = computed(() => {
  if (props.stats.total_feedbacks === 0) return 0
  return Math.round((props.stats.with_comments / props.stats.total_feedbacks) * 100)
})

// Couleur de la barre de progression selon le taux
const satisfactionColor = computed(() => {
  const rate = props.stats.satisfaction_rate
  if (rate >= 80) return '#2ecc71' // Vert atténué
  if (rate >= 60) return '#f39c12' // Orange
  return '#e74c3c' // Rouge atténué
})

// LOGS DE DEBUG (À RETIRER EN PRODUCTION)
console.log('🎯 FeedbackStats - props.stats:', props.stats)
watch(() => props.stats, (newStats) => {
  console.log('🔄 Stats changées:', newStats)
}, { immediate: true, deep: true })
</script>

<style lang="scss" scoped>
.feedback-stats {
  width: 100%;
}

.stat-card {
  height: 100%;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  :deep(.el-card__body) {
    padding: 20px;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  :deep(.el-statistic) {
    .el-statistic__head {
      font-size: 14px;
      color: #909399;
      margin-bottom: 12px;
      font-weight: 500;
    }

    .el-statistic__content {
      font-size: 28px;
      font-weight: 600;
    }
  }

  // Couleurs spécifiques pour chaque card
  &.stat-card-total :deep(.el-icon) {
    color: #3498db; // Bleu pour Total Feedbacks
  }

  &.stat-card-satisfaction :deep(.el-icon) {
    color: #f39c12; // Orange pour Taux de Satisfaction
  }

  &.stat-card-feedback-rate :deep(.el-icon) {
    color: #9b59b6; // Violet pour Taux de Feedback
  }

  &.stat-card-comments :deep(.el-icon) {
    color: #e67e22; // Orange foncé pour Avec Commentaires
  }

  &.stat-card-colored {
    :deep(.el-card__body) {
      background: linear-gradient(135deg, var(--card-color-start) 0%, var(--card-color-end) 100%);
      border-radius: 4px;
    }

    :deep(.el-statistic__head),
    :deep(.el-statistic__content),
    :deep(.el-icon) {
      color: #ffffff !important;
    }
  }

  &.stat-card-positive {
    --card-color-start: #2ecc71;  // Vert atténué (plus doux que BEAC)
    --card-color-end: #58d68d;    // Vert clair
  }

  &.stat-card-negative {
    --card-color-start: #e74c3c;  // Rouge atténué (plus doux que BEAC)
    --card-color-end: #ec7063;    // Rouge clair
  }
}

.el-progress {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .stat-card {
    margin-bottom: 16px;
    min-height: 120px;
  }
}
</style>