<template>
  <el-card shadow="hover" class="stat-card" :class="cardClass">
    <el-statistic 
      :title="title" 
      :value="animatedValue"
      :suffix="suffix"
      :precision="precision"
    >
      <template #prefix>
        <el-icon :size="iconSize" :style="{ color: iconColor }">
          <component :is="icon" />
        </el-icon>
      </template>
    </el-statistic>
    
    <!-- Slot pour contenu additionnel (ex: tendance, texte) -->
    <slot name="extra"></slot>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useCountAnimation } from '@/composables/useCountAnimation'

const props = defineProps({
  // Texte du titre
  title: {
    type: String,
    required: true
  },
  
  // Valeur à afficher
  value: {
    type: Number,
    required: true,
    default: 0
  },
  
  // Icône Element Plus
  icon: {
    type: Object,
    required: true
  },
  
  // Couleur de l'icône
  iconColor: {
    type: String,
    default: '#409EFF'
  },
  
  // Taille de l'icône
  iconSize: {
    type: Number,
    default: 24
  },
  
  // Suffixe (%, €, etc.)
  suffix: {
    type: String,
    default: ''
  },
  
  // Nombre de décimales
  precision: {
    type: Number,
    default: 0
  },
  
  // Durée d'animation (ms)
  animationDuration: {
    type: Number,
    default: 1500
  },
  
  // Classe CSS additionnelle
  cardClass: {
    type: String,
    default: ''
  }
})

// Créer une computed réactive pour la valeur
const valueRef = computed(() => props.value || 0)

// Animation de la valeur
const { displayValue: animatedValue } = useCountAnimation(
  valueRef, 
  props.animationDuration, 
  props.precision
)
</script>

<style lang="scss" scoped>
.stat-card {
  height: 100%;
  min-height: 140px;
  border-radius: 10px;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  :deep(.el-card__body) {
    padding: 20px;
    height: 100%;
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
      color: #303133;
      
      .el-icon {
        margin-right: 8px;
      }
    }
  }
}

@media (max-width: 768px) {
  .stat-card {
    min-height: 120px;
    
    :deep(.el-card__body) {
      padding: 16px;
    }
    
    :deep(.el-statistic__content) {
      font-size: 24px;
    }
  }
}
</style>