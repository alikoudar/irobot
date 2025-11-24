/**
 * Index des composables de l'application.
 * 
 * Exporte tous les composables pour une utilisation simplifiée :
 * import { useSSE, useChat } from '@/composables'
 * 
 * Sprint 8 - Phase 1 : Stores & Composables
 */

// Composable SSE pour les connexions Server-Sent Events
export { useSSE, default as useSSEDefault } from './useSSE'

// Composable Chat pour l'envoi de messages et le streaming
export { useChat, default as useChatDefault } from './useChat'