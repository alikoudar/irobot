<template>
  <el-card class="stats-card" :style="{ borderTop: `3px solid ${color}` }">
    <div class="card-content">
      <div class="icon-wrapper" :style="{ backgroundColor: `${color}15` }">
        <el-icon :size="32" :color="color">
          <component :is="iconComponent" />
        </el-icon>
      </div>
      
      <div class="stats-info">
        <h3 class="title">{{ title }}</h3>
        <p class="value">{{ value }}</p>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
        <p v-if="total" class="total">sur {{ total }} total</p>
      </div>
    </div>
    
    <div v-if="total" class="progress-bar">
      <el-progress
        :percentage="percentage"
        :color="color"
        :show-text="false"
      />
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import {
  User,
  Document,
  ChatDotRound,
  CircleCheck,
  Coin,
  CircleCheckFilled
} from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  total: {
    type: Number,
    default: null
  },
  icon: {
    type: String,
    required: true
  },
  color: {
    type: String,
    required: true
  }
})

// Map icon string to component
const iconComponents = {
  User,
  Document,
  ChatDotRound,
  CircleCheck,
  Coin,
  CircleCheckFilled
}

const iconComponent = computed(() => {
  return iconComponents[props.icon] || User
})

const percentage = computed(() => {
  if (!props.total) return 0
  const val = typeof props.value === 'string' 
    ? parseFloat(props.value) 
    : props.value
  return Math.round((val / props.total) * 100)
})
</script>

<style lang="scss" scoped>
.stats-card {
  height: 100%;
  
  :deep(.el-card__body) {
    height: 100%;
  }
  
  .card-content {
    display: flex;
    gap: 15px;
    align-items: flex-start;
    
    .icon-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 60px;
      height: 60px;
      border-radius: 10px;
      flex-shrink: 0;
    }
    
    .stats-info {
      flex: 1;
      
      .title {
        font-size: 14px;
        color: #909399;
        margin: 0 0 5px 0;
        font-weight: 500;
      }
      
      .value {
        font-size: 28px;
        font-weight: bold;
        margin: 0;
        color: #303133;
        line-height: 1.2;
      }
      
      .subtitle,
      .total {
        font-size: 12px;
        color: #909399;
        margin: 5px 0 0 0;
      }
    }
  }
  
  .progress-bar {
    margin-top: 15px;
  }
}
</style>