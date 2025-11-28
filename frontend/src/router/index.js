import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/auth/Login.vue'),
      meta: { requiresGuest: true, noLayout: true }
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('../views/auth/ForgotPassword.vue'),
      meta: { requiresGuest: true, noLayout: true }
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('../views/auth/ChangePassword.vue'),
      meta: { requiresAuth: true, noLayout: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/Profile.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      redirect: (to) => {
        const authStore = useAuthStore()
        if (authStore.isAuthenticated) {
          return authStore.isAdmin ? '/admin/users' : '/chat'
        }
        return '/login'
      }
    },
    {
    path: '/chat',
    name: 'chat',
    component: () => import('../views/user/Chat.vue'),
    meta: { requiresAuth: true }
    },
    {
    path: '/conversations',
    name: 'conversations',
    component: () => import('../views/user/Conversations.vue'),
    meta: { requiresAuth: true }
    },
    // Redirection de l'ancienne route /history vers /conversations
    {
    path: '/history',
    redirect: '/conversations'
    },
    {
      path: '/feedbacks',
      name: 'feedbacks',
      component: () => import('../views/user/MyFeedbacks.vue'),
      meta: { requiresAuth: true }
    },
    {
    path: '/documents',
    name: 'documents',
    component: () => import('../views/manager/Documents.vue'),
    meta: { requiresAuth: true, requiresManager: true }
    },

    // Route Admin - Documents (même vue, permissions différentes)
    {
    path: '/admin/documents',
    name: 'admin-documents',
    component: () => import('../views/admin/Documents.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
    },
    // ============================================================================
    // ROUTES CATÉGORIES - SPRINT 3 PHASE 3
    // ============================================================================
    {
      path: '/categories',
      name: 'categories',
      component: () => import('../views/admin/Categories.vue'),
      meta: { requiresAuth: true, requiresManager: true }
    },
    {
      path: '/admin/categories',
      name: 'admin-categories',
      component: () => import('../views/admin/Categories.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/manager/categories',
      name: 'manager-categories',
      component: () => import('../views/manager/Categories.vue'),
      meta: { requiresAuth: true, requiresManager: true }
    },
    // ============================================================================
    // ROUTES ADMIN
    // ============================================================================
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('../views/admin/Users.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/dashboard',
      name: 'admin-dashboard',
      component: () => import('../views/admin/Dashboard.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/stats',
      name: 'admin-stats',
      component: () => import('../views/Home.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/feedbacks',
      name: 'admin-feedbacks',
      component: () => import('../views/admin/AdminFeedbacks.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/logs',
      name: 'admin-logs',
      component: () => import('../views/Home.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/config',
      name: 'admin-config',
      component: () => import('../views/Home.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ]
})

// Guards de navigation
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Initialiser le user si on a un token
  if (!authStore.currentUser && authStore.accessToken) {
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      console.error('Error fetching current user:', error)
    }
  }

  // Routes nécessitant authentification
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }

    // Forcer changement de mot de passe
    if (authStore.mustChangePassword && to.name !== 'change-password') {
      next({ name: 'change-password' })
      return
    }

    // Vérifier rôle Admin
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
      next({ name: 'chat' })
      return
    }

    // Vérifier rôle Manager
    if (to.meta.requiresManager && !authStore.canManageDocuments) {
      next({ name: 'chat' })
      return
    }
  }

  // Routes pour invités (login)
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    if (authStore.mustChangePassword) {
      next({ name: 'change-password' })
    } else if (authStore.isAdmin) {
      next({ name: 'admin-users' })
    } else {
      next({ name: 'chat' })
    }
    return
  }

  next()
})

export default router