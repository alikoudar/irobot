<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <!-- Logo et titre -->
      <div class="sidebar-header">
        <div class="logo-container">
          <div class="logo">
            <el-icon :size="28" color="#005ca9">
              <ChatDotRound />
            </el-icon>
          </div>
          <transition name="fade">
            <span v-show="!sidebarCollapsed" class="app-title">IroBot</span>
          </transition>
        </div>
        <el-tooltip
          :content="sidebarCollapsed ? 'Agrandir' : 'Réduire'"
          placement="right"
        >
          <el-button
            link
            class="collapse-btn"
            @click="toggleSidebar"
          >
            <el-icon :size="18">
              <DArrowLeft v-if="!sidebarCollapsed" />
              <DArrowRight v-else />
            </el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <!-- Navigation principale -->
      <nav class="sidebar-nav">
        <el-menu
          :default-active="activeMenu"
          :collapse="sidebarCollapsed"
          :unique-opened="true"
          @select="handleMenuSelect"
        >
          <!-- ============================================================ -->
          <!-- SECTION BASE - Tous les utilisateurs (USER, MANAGER, ADMIN) -->
          <!-- ============================================================ -->
          
          <!-- Chat - Tous les utilisateurs -->
          <el-menu-item index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>Chat</template>
          </el-menu-item>

          <!-- Historique - Tous les utilisateurs -->
          <el-menu-item index="/history">
            <el-icon><Clock /></el-icon>
            <template #title>Historique</template>
          </el-menu-item>

          <!-- Mes Feedbacks - Tous les utilisateurs -->
          <el-menu-item index="/feedbacks">
            <el-icon><ChatLineSquare /></el-icon>
            <template #title>Mes Feedbacks</template>
          </el-menu-item>

          <!-- ============================================================ -->
          <!-- SECTION MANAGEMENT - MANAGER et ADMIN uniquement             -->
          <!-- ============================================================ -->
          
          <!-- Divider -->
          <el-divider v-if="isManagerOrAdmin" />

          <!-- Management (Manager + Admin) - Icône Folder -->
          <el-sub-menu index="management" v-if="isManagerOrAdmin">
            <template #title>
              <el-icon><Folder /></el-icon>
              <span>Gestion Contenu</span>
            </template>
            <el-menu-item index="/documents">
              <el-icon><Document /></el-icon>
              <template #title>Documents</template>
            </el-menu-item>
            <el-menu-item index="/categories">
              <el-icon><CollectionTag /></el-icon>
              <template #title>Catégories</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- ============================================================ -->
          <!-- SECTION ADMINISTRATION - ADMIN uniquement                    -->
          <!-- ============================================================ -->
          
          <!-- Divider -->
          <el-divider v-if="isAdmin" />

          <!-- Administration (Admin uniquement) - Icône Tools -->
          <el-sub-menu index="admin" v-if="isAdmin">
            <template #title>
              <el-icon><Tools /></el-icon>
              <span>Administration</span>
            </template>
            <el-menu-item index="/admin/users">
              <el-icon><User /></el-icon>
              <template #title>Utilisateurs</template>
            </el-menu-item>
            <el-menu-item index="/admin/dashboard">
              <el-icon><Monitor /></el-icon>
              <template #title>Dashboard</template>
            </el-menu-item>
            <el-menu-item index="/admin/stats">
              <el-icon><TrendCharts /></el-icon>
              <template #title>Statistiques</template>
            </el-menu-item>
            <el-menu-item index="/admin/logs">
              <el-icon><DocumentCopy /></el-icon>
              <template #title>Logs Audit</template>
            </el-menu-item>
            <el-menu-item index="/admin/config">
              <el-icon><Setting /></el-icon>
              <template #title>Configuration</template>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </nav>

      <!-- Support en bas -->
      <div class="sidebar-footer">
        <div class="support-card" v-if="!sidebarCollapsed">
          <el-icon :size="20" color="#005ca9">
            <QuestionFilled />
          </el-icon>
          <div class="support-text">
            <p class="support-title">Besoin d'aide ?</p>
            <p class="support-subtitle">Contactez le support</p>
          </div>
        </div>
        <el-tooltip content="Support" placement="right" v-else>
          <el-button
            link
            class="support-btn-collapsed"
          >
            <el-icon :size="20">
              <QuestionFilled />
            </el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-container">
      <!-- Navbar -->
      <header class="navbar">
        <div class="navbar-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">
              <el-icon><HomeFilled /></el-icon>
              Accueil
            </el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.name }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="navbar-right">
          <!-- Notifications -->
          <el-dropdown trigger="click" @command="handleNotificationCommand">
            <el-badge :value="notificationCount" class="navbar-badge" :hidden="notificationCount === 0">
              <el-button link class="navbar-btn">
                <el-icon :size="20">
                  <Bell />
                </el-icon>
              </el-button>
            </el-badge>
            <template #dropdown>
              <el-dropdown-menu>
                <div class="notifications-header">
                  <span>Notifications</span>
                  <el-button link size="small" @click="clearNotifications">
                    Tout effacer
                  </el-button>
                </div>
                <el-dropdown-item v-for="notif in notifications" :key="notif.id" :command="notif.id">
                  <div class="notification-item">
                    <el-icon :color="notif.color"><component :is="notif.icon" /></el-icon>
                    <div class="notification-content">
                      <p class="notification-title">{{ notif.title }}</p>
                      <p class="notification-time">{{ notif.time }}</p>
                    </div>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item v-if="notifications.length === 0" disabled>
                  <div class="no-notifications">
                    <el-icon :size="32" color="#cbd5e1"><Bell /></el-icon>
                    <p>Aucune notification</p>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- User dropdown -->
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-dropdown">
              <el-avatar :size="36" :style="{ background: '#005ca9' }">
                {{ authStore.currentUser?.prenom?.charAt(0) }}{{ authStore.currentUser?.nom?.charAt(0) }}
              </el-avatar>
              <div class="user-info">
                <span class="user-name">{{ authStore.userFullName }}</span>
                <span class="user-role">{{ getRoleLabel(authStore.currentUser?.role) }}</span>
              </div>
              <el-icon class="dropdown-icon">
                <CaretBottom />
              </el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  Mon profil
                </el-dropdown-item>
                <el-dropdown-item command="change-password">
                  <el-icon><Lock /></el-icon>
                  Changer mot de passe
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  Déconnexion
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Page content -->
      <main class="content">
        <transition name="fade-slide" mode="out-in">
          <slot />
        </transition>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ChatDotRound,
  Clock,
  ChatLineSquare,
  Folder,           // 📁 Gestion Contenu (Management)
  Document,
  CollectionTag,
  Tools,            // 🔧 Administration
  User,
  Monitor,          // 🖥️ Dashboard
  TrendCharts,
  DocumentCopy,
  Setting,
  QuestionFilled,
  HomeFilled,
  Bell,
  CaretBottom,
  Lock,
  SwitchButton,
  DArrowLeft,
  DArrowRight,
  InfoFilled,
  WarningFilled
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// State
const sidebarCollapsed = ref(false)
const notificationCount = ref(3)

// Utiliser markRaw pour éviter les warnings Vue
const notifications = ref([
  {
    id: 1,
    title: 'Nouveau document disponible',
    time: 'Il y a 5 minutes',
    icon: InfoFilled,
    color: '#3b82f6'
  },
  {
    id: 2,
    title: 'Mise à jour système programmée',
    time: 'Il y a 1 heure',
    icon: WarningFilled,
    color: '#f59e0b'
  },
  {
    id: 3,
    title: 'Sauvegarde complétée',
    time: 'Il y a 2 heures',
    icon: InfoFilled,
    color: '#10b981'
  }
])

// ============================================================================
// PERMISSIONS CUMULATIVES
// ============================================================================

/**
 * Système de permissions cumulatif :
 * - USER : accès de base (chat, historique, feedbacks)
 * - MANAGER : TOUT ce que USER a + documents + catégories
 * - ADMIN : TOUT ce que MANAGER a + administration
 */

// ADMIN = accès complet
const isAdmin = computed(() => {
  return authStore.currentUser?.role === 'ADMIN'
})

// MANAGER ou ADMIN = accès documents et catégories
const isManagerOrAdmin = computed(() => {
  const role = authStore.currentUser?.role
  return role === 'MANAGER' || role === 'ADMIN'
})

// USER = utilisateur de base
const isUser = computed(() => {
  return authStore.currentUser?.role !== undefined
})

// ============================================================================
// COMPUTED
// ============================================================================

const activeMenu = computed(() => route.path)

const breadcrumbs = computed(() => {
  const paths = route.path.split('/').filter(Boolean)
  return paths.map((path, index) => ({
    name: path.charAt(0).toUpperCase() + path.slice(1),
    path: '/' + paths.slice(0, index + 1).join('/')
  }))
})

// ============================================================================
// METHODS
// ============================================================================

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar-collapsed', sidebarCollapsed.value)
}

const handleMenuSelect = (index) => {
  router.push(index)
}

const handleNotificationCommand = (command) => {
  const notif = notifications.value.find(n => n.id === command)
  if (notif) {
    ElMessage.info(notif.title)
  }
}

const clearNotifications = () => {
  notifications.value = []
  notificationCount.value = 0
  ElMessage.success('Notifications effacées')
}

const handleUserCommand = async (command) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'change-password':
      router.push('/change-password')
      break
    case 'logout':
      await authStore.logout()
      router.push('/login')
      break
  }
}

const getRoleLabel = (role) => {
  const labels = {
    'ADMIN': 'Administrateur',
    'MANAGER': 'Manager',
    'USER': 'Utilisateur'
  }
  return labels[role] || role
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  // Restaurer l'état du sidebar
  const saved = localStorage.getItem('sidebar-collapsed')
  if (saved !== null) {
    sidebarCollapsed.value = saved === 'true'
  }
})
</script>

<style scoped lang="scss">
// ... (même CSS que précédemment)
.app-layout {
  display: flex;
  height: 100vh;
  background: var(--bg-color);

  // CSS Variables
  --primary-color: #005ca9;
  --bg-color: #f5f7fa;
  --navbar-bg: #ffffff;
  --sidebar-bg: #ffffff;
  --content-bg: #f5f7fa;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --border-color: #e2e8f0;
  --hover-bg: #f1f5f9;
  --active-bg: #e0f2fe;
  --support-card-bg: #eff6ff;
  --scrollbar-thumb: #cbd5e1;
  --scrollbar-thumb-hover: #94a3b8;

  .sidebar {
    width: 260px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    transition: width 0.3s;

    .sidebar-header {
      height: 64px;
      padding: 0 16px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      gap: 8px;
      
      .logo-container {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 12px;
        
        .logo {
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--support-card-bg);
          border-radius: 10px;
          flex-shrink: 0;
        }
        
        .app-title {
          font-size: 20px;
          font-weight: 700;
          color: var(--text-primary);
        }
      }

      .collapse-btn {
        color: var(--text-secondary);
        flex-shrink: 0;
        width: 32px;
        height: 32px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        
        &:hover {
          color: var(--primary-color);
          background: var(--hover-bg);
          border-radius: 6px;
        }
      }
    }

    .sidebar-nav {
      flex: 1;
      overflow-y: auto;
      padding: 16px 12px;

      :deep(.el-menu) {
        border: none;
        background: transparent;

        .el-menu-item,
        .el-sub-menu__title {
          border-radius: 8px;
          margin-bottom: 4px;
          height: 44px;
          line-height: 44px;
          color: var(--text-secondary);
          transition: all 0.2s;

          &:hover {
            background: var(--hover-bg);
            color: var(--primary-color);
          }

          &.is-active {
            background: var(--active-bg);
            color: var(--primary-color);
            font-weight: 600;
          }

          .el-icon {
            font-size: 18px;
          }
        }

        .el-divider {
          margin: 12px 0;
        }
      }
    }

    .sidebar-footer {
      padding: 16px;
      border-top: 1px solid var(--border-color);

      .support-card {
        background: var(--support-card-bg);
        border-radius: 12px;
        padding: 16px;
        display: flex;
        gap: 12px;
        align-items: flex-start;
        transition: all 0.3s;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 92, 169, 0.1);
        }

        .support-text {
          flex: 1;

          .support-title {
            font-weight: 600;
            color: var(--text-primary);
            margin: 0 0 4px 0;
            font-size: 14px;
          }

          .support-subtitle {
            font-size: 12px;
            color: var(--text-secondary);
            margin: 0;
          }
        }
      }

      .support-btn-collapsed {
        width: 100%;
        height: 44px;
        color: var(--primary-color);
      }
    }
  }

  &.sidebar-collapsed .sidebar {
    width: 72px;

    .sidebar-nav {
      padding: 16px 8px;
    }

    .sidebar-header {
      .collapse-btn {
        margin-left: auto;
      }
    }
  }

  .main-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .navbar {
      height: 64px;
      background: var(--navbar-bg);
      border-bottom: 1px solid var(--border-color);
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;

      .navbar-left {
        :deep(.el-breadcrumb) {
          font-size: 14px;

          .el-breadcrumb__item {
            .el-breadcrumb__inner {
              color: var(--text-secondary);
              font-weight: 500;

              &:hover {
                color: var(--primary-color);
              }
            }

            &:last-child .el-breadcrumb__inner {
              color: var(--text-primary);
              font-weight: 600;
            }
          }
        }
      }

      .navbar-right {
        display: flex;
        align-items: center;
        gap: 16px;

        .navbar-btn {
          color: var(--text-secondary);
          padding: 8px;
          border-radius: 8px;

          &:hover {
            color: var(--primary-color);
            background: var(--hover-bg);
          }
        }

        .navbar-badge {
          :deep(.el-badge__content) {
            background: #f56c6c;
          }
        }

        .user-dropdown {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 6px 12px;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;

          &:hover {
            background: var(--hover-bg);
          }

          .user-info {
            display: flex;
            flex-direction: column;

            .user-name {
              font-size: 14px;
              font-weight: 600;
              color: var(--text-primary);
            }

            .user-role {
              font-size: 12px;
              color: var(--text-secondary);
            }
          }

          .dropdown-icon {
            color: var(--text-secondary);
          }
        }
      }
    }

    .content {
      flex: 1;
      overflow-y: auto;
      background: var(--content-bg);
    }
  }
}

:deep(.notifications-header) {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
  color: var(--text-primary);
}

:deep(.notification-item) {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 8px 0;

  .notification-content {
    flex: 1;

    .notification-title {
      margin: 0 0 4px 0;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
    }

    .notification-time {
      margin: 0;
      font-size: 12px;
      color: var(--text-secondary);
    }
  }
}

:deep(.no-notifications) {
  text-align: center;
  padding: 32px 16px;
  color: var(--text-secondary);

  p {
    margin: 8px 0 0 0;
    font-size: 14px;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 3px;

  &:hover {
    background: var(--scrollbar-thumb-hover);
  }
}
</style>