<template>
  <div class="conversation-search">
    <el-card class="search-card">
      <div class="search-filters">
        <!-- Recherche textuelle -->
        <el-input
          v-model="searchQuery"
          placeholder="Rechercher dans vos conversations..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="debouncedSearch"
        />
        
        <!-- Filtres avancés (collapsible) -->
        <el-button
          :icon="showAdvanced ? ArrowUp : ArrowDown"
          @click="showAdvanced = !showAdvanced"
        >
          {{ showAdvanced ? 'Masquer' : 'Filtres avancés' }}
        </el-button>
      </div>
      
      <!-- Filtres avancés -->
      <transition name="slide-fade">
        <div v-show="showAdvanced" class="advanced-filters">
          <!-- Plage de dates -->
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="à"
            start-placeholder="Date début"
            end-placeholder="Date fin"
            format="DD/MM/YYYY"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
            @change="handleSearch"
          />
          
          <!-- Afficher archivées -->
          <el-checkbox
            v-model="showArchived"
            @change="handleSearch"
          >
            Afficher les conversations archivées
          </el-checkbox>
          
          <!-- Bouton reset -->
          <el-button
            :icon="RefreshLeft"
            @click="resetFilters"
          >
            Réinitialiser
          </el-button>
        </div>
      </transition>
    </el-card>
  </div>
</template>

<script setup>
/**
 * ConversationSearch.vue
 * 
 * Composant de recherche et filtrage des conversations
 * avec debounce pour la recherche textuelle
 * 
 * Sprint 9 - Phase 3
 */
import { ref, watch } from 'vue'
import {
  Search,
  ArrowUp,
  ArrowDown,
  RefreshLeft
} from '@element-plus/icons-vue'
import _ from 'lodash'

// ============================================================================
// EMITS
// ============================================================================

const emit = defineEmits(['search'])

// ============================================================================
// STATE
// ============================================================================

const searchQuery = ref('')
const dateRange = ref(null)
const showArchived = ref(false)
const showAdvanced = ref(false)

// Raccourcis de dates
const dateShortcuts = [
  {
    text: "Aujourd'hui",
    value: () => {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      return [today, new Date()]
    }
  },
  {
    text: 'Cette semaine',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - start.getDay())
      start.setHours(0, 0, 0, 0)
      return [start, end]
    }
  },
  {
    text: 'Ce mois',
    value: () => {
      const end = new Date()
      const start = new Date(end.getFullYear(), end.getMonth(), 1)
      return [start, end]
    }
  },
  {
    text: '3 derniers mois',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setMonth(start.getMonth() - 3)
      return [start, end]
    }
  }
]

// ============================================================================
// METHODS
// ============================================================================

/**
 * Émettre les filtres de recherche
 */
function handleSearch() {
  emit('search', {
    query: searchQuery.value,
    startDate: dateRange.value?.[0] || null,
    endDate: dateRange.value?.[1] || null,
    showArchived: showArchived.value
  })
}

/**
 * Recherche avec debounce (500ms)
 */
const debouncedSearch = _.debounce(() => {
  handleSearch()
}, 500)

/**
 * Réinitialiser les filtres
 */
function resetFilters() {
  searchQuery.value = ''
  dateRange.value = null
  showArchived.value = false
  handleSearch()
}

// ============================================================================
// WATCHERS
// ============================================================================

// Émettre les filtres initiaux au montage
watch(() => searchQuery.value, (newVal) => {
  if (newVal === '') {
    handleSearch()
  }
}, { immediate: true })
</script>

<style scoped lang="scss">
.conversation-search {
  .search-card {
    :deep(.el-card__body) {
      padding: 20px;
    }
  }
  
  .search-filters {
    display: flex;
    gap: 12px;
    align-items: center;
    
    .search-input {
      flex: 1;
      max-width: 600px;
    }
  }
  
  .advanced-filters {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-light);
    display: flex;
    gap: 16px;
    align-items: center;
    flex-wrap: wrap;
  }
}

// Transition pour les filtres avancés
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}
</style>