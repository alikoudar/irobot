<template>
  <div class="notification-panel">
    <!-- Header du panel -->
    <div class="panel-header">
      <span class="panel-title">Notifications</span>
      <div class="panel-actions">
        <el-tooltip content="Marquer tout comme lu" placement="top">
          <el-button 
            link 
            :disabled="!hasUnread"
            @click="handleMarkAllRead"
          >
            <el-icon><Check /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="Paramètres" placement="top">
          <el-button link @click="showSettings = true">
            <el-icon><Setting /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- Indicateur connexion SSE -->
    <div v-if="!sseConnected" class="sse-indicator disconnected">
      <el-icon><WarningFilled /></el-icon>
      <span>Connexion temps réel inactive</span>
      <el-button link size="small" @click="reconnectSSE">Reconnecter</el-button>
    </div>

    <!-- Liste des notifications -->
    <div class="notifications-list" v-loading="loading">
      <template v-if="notifications.length > 0">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-item"
          :class="{ unread: !notification.is_read }"
          @click="handleNotificationClick(notification)"
        >
          <!-- Icône -->
          <div 
            class="notification-icon"
            :style="{ color: notification.color }"
          >
            <el-icon :size="20">
              <component :is="getIconComponent(notification.icon)" />
            </el-icon>
          </div>

          <!-- Contenu -->
          <div class="notification-content">
            <div class="notification-title">{{ notification.title }}</div>
            <div v-if="notification.message" class="notification-message">
              {{ notification.message }}
            </div>
            <div class="notification-time">
              {{ formatTime(notification.created_at) }}
            </div>
          </div>

          <!-- Actions -->
          <div class="notification-actions" @click.stop>
            <el-tooltip content="Supprimer" placement="top">
              <el-button 
                link 
                class="dismiss-btn"
                @click="handleDismiss(notification.id)"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </el-tooltip>
          </div>

          <!-- Badge non lu -->
          <div v-if="!notification.is_read" class="unread-dot"></div>
        </div>
      </template>

      <!-- État vide -->
      <div v-else class="empty-state">
        <el-icon :size="48" color="#cbd5e1"><Bell /></el-icon>
        <p>Aucune notification</p>
      </div>
    </div>

    <!-- Footer -->
    <div class="panel-footer" v-if="notifications.length > 0">
      <el-button link @click="handleClearAll">
        Tout effacer
      </el-button>
      <el-button link type="primary" @click="$emit('view-all')">
        Voir tout
      </el-button>
    </div>

    <!-- Dialog paramètres -->
    <el-dialog
      v-model="showSettings"
      title="Paramètres de notification"
      width="400px"
    >
      <div class="settings-form">
        <el-form label-position="left" label-width="180px">
          <el-form-item label="Sons">
            <el-switch v-model="localSettings.soundEnabled" />
          </el-form-item>
          <el-form-item label="Popups">
            <el-switch v-model="localSettings.showPopups" />
          </el-form-item>
          <el-form-item label="Durée popup (ms)">
            <el-input-number 
              v-model="localSettings.popupDuration"
              :min="1000"
              :max="30000"
              :step="1000"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showSettings = false">Annuler</el-button>
        <el-button type="primary" @click="saveSettings">Enregistrer</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, markRaw } from 'vue'
import { 
  Bell, 
  Check, 
  Close, 
  Setting,
  WarningFilled,
  InfoFilled,
  SuccessFilled,
  CircleCloseFilled,
  CircleCheckFilled,
  Upload,
  Loading,
  ChatLineSquare,
  TrendCharts,
  UserFilled,
  Edit,
  Delete,
  Lock
} from '@element-plus/icons-vue'
import { useNotificationStore } from '@/stores/notifications'
import { ElMessage, ElMessageBox } from 'element-plus'

// Props & Emits
defineProps({
  maxItems: {
    type: Number,
    default: 10
  }
})

const emit = defineEmits(['view-all', 'notification-click'])

// Store
const notificationStore = useNotificationStore()

// State
const showSettings = ref(false)
const localSettings = ref({
  soundEnabled: true,
  showPopups: true,
  popupDuration: 5000
})

// Computed
const loading = computed(() => notificationStore.loading)
const notifications = computed(() => notificationStore.recentNotifications)
const hasUnread = computed(() => notificationStore.hasUnread)
const sseConnected = computed(() => notificationStore.sseConnected)

// Map des icônes
const iconComponents = {
  Bell: markRaw(Bell),
  Upload: markRaw(Upload),
  Loading: markRaw(Loading),
  SuccessFilled: markRaw(SuccessFilled),
  CircleCloseFilled: markRaw(CircleCloseFilled),
  CircleCheckFilled: markRaw(CircleCheckFilled),
  ChatLineSquare: markRaw(ChatLineSquare),
  WarningFilled: markRaw(WarningFilled),
  InfoFilled: markRaw(InfoFilled),
  TrendCharts: markRaw(TrendCharts),
  UserFilled: markRaw(UserFilled),
  Edit: markRaw(Edit),
  Delete: markRaw(Delete),
  Lock: markRaw(Lock)
}

// Methods
function getIconComponent(iconName) {
  return iconComponents[iconName] || iconComponents.Bell
}

function formatTime(dateString) {
  return notificationStore.formatRelativeTime(dateString)
}

async function handleNotificationClick(notification) {
  // Marquer comme lu
  if (!notification.is_read) {
    await notificationStore.markAsRead(notification.id)
  }
  
  emit('notification-click', notification)
}

async function handleMarkAllRead() {
  try {
    await notificationStore.markAllAsRead()
    ElMessage.success('Toutes les notifications ont été marquées comme lues')
  } catch (error) {
    ElMessage.error('Erreur lors du marquage')
  }
}

async function handleDismiss(notificationId) {
  try {
    await notificationStore.dismissNotification(notificationId)
  } catch (error) {
    ElMessage.error('Erreur lors de la suppression')
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm(
      'Voulez-vous vraiment supprimer toutes les notifications ?',
      'Confirmation',
      {
        confirmButtonText: 'Supprimer',
        cancelButtonText: 'Annuler',
        type: 'warning'
      }
    )
    
    await notificationStore.dismissAll()
    ElMessage.success('Toutes les notifications ont été supprimées')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Erreur lors de la suppression')
    }
  }
}

function reconnectSSE() {
  notificationStore.disconnectSSE()
  notificationStore.connectSSE()
}

function saveSettings() {
  notificationStore.updateSettings(localSettings.value)
  showSettings.value = false
  ElMessage.success('Paramètres enregistrés')
}

// Lifecycle
onMounted(() => {
  // Charger les paramètres actuels
  localSettings.value = { ...notificationStore.settings }
  
  // Charger les notifications initiales
  notificationStore.fetchNotifications()
  
  // Connecter au SSE
  notificationStore.connectSSE()
})

onUnmounted(() => {
  // Note: Ne pas déconnecter ici car le store reste actif
})

// Watch pour sync les settings
watch(() => notificationStore.settings, (newSettings) => {
  localSettings.value = { ...newSettings }
}, { deep: true })
</script>

<style scoped lang="scss">
.notification-panel {
  width: 360px;
  max-height: 500px;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color);
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color-lighter);
  
  .panel-title {
    font-weight: 600;
    font-size: 16px;
    color: var(--el-text-color-primary);
  }
  
  .panel-actions {
    display: flex;
    gap: 8px;
    
    .el-button {
      color: var(--el-text-color-secondary);
      
      &:hover {
        color: var(--el-color-primary);
      }
    }
  }
}

.sse-indicator {
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
  
  &.disconnected {
    background: var(--el-color-danger-light-9);
    color: var(--el-color-danger);
  }
  
  .el-button {
    margin-left: auto;
  }
}

.notifications-list {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 350px;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
  
  &:hover {
    background: var(--el-fill-color-light);
    
    .notification-actions {
      opacity: 1;
    }
  }
  
  &.unread {
    background: var(--el-color-primary-light-9);
  }
  
  &:not(:last-child) {
    border-bottom: 1px solid var(--el-border-color-lighter);
  }
}

.notification-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--el-fill-color);
}

.notification-content {
  flex: 1;
  min-width: 0;
  
  .notification-title {
    font-weight: 500;
    font-size: 14px;
    color: var(--el-text-color-primary);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .notification-message {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 4px;
  }
  
  .notification-time {
    font-size: 12px;
    color: var(--el-text-color-placeholder);
  }
}

.notification-actions {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
  
  .dismiss-btn {
    color: var(--el-text-color-secondary);
    padding: 4px;
    
    &:hover {
      color: var(--el-color-danger);
    }
  }
}

.unread-dot {
  position: absolute;
  top: 50%;
  right: 12px;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: var(--el-text-color-secondary);
  
  p {
    margin-top: 12px;
    font-size: 14px;
  }
}

.panel-footer {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-lighter);
}

.settings-form {
  .el-form-item {
    margin-bottom: 20px;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
}

/* Scrollbar */
.notifications-list {
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 3px;
    
    &:hover {
      background: var(--el-border-color-darker);
    }
  }
}
</style>