/**
 * Index des composants Chat.
 * 
 * Exporte tous les composants du module chat :
 * import { ChatInterface, MessageBubble } from '@/components/chat'
 * 
 * Sprint 8 - Phase 2 : Composants Chat
 */

// Composant principal
export { default as ChatInterface } from './ChatInterface.vue'

// Sidebar
export { default as ConversationsSidebar } from './ConversationsSidebar.vue'
export { default as ConversationItem } from './ConversationItem.vue'

// Fenêtre de chat
export { default as ChatWindow } from './ChatWindow.vue'
export { default as MessageBubble } from './MessageBubble.vue'

// Composants secondaires
export { default as SourcesList } from './SourcesList.vue'
export { default as FeedbackButtons } from './FeedbackButtons.vue'