/**
 * useCountAnimation.js - VERSION CORRIGÉE
 * 
 * Composable pour animer les chiffres (effet compteur)
 * Utilisé pour animer tous les chiffres statistiques
 * 
 * CORRECTIF : Gestion correcte de la réactivité avec toRef
 */

import { ref, watch, onMounted, onUnmounted, toRef, isRef, computed } from 'vue'

/**
 * Hook pour animer un chiffre de 0 à sa valeur finale
 * 
 * @param {Number|Ref} targetSource - Valeur cible à atteindre (peut être une ref ou un nombre)
 * @param {Number} duration - Durée de l'animation en ms (défaut: 1500ms)
 * @param {Number} decimals - Nombre de décimales (défaut: 0)
 * @returns {Object} - { displayValue, startAnimation }
 */
export function useCountAnimation(targetSource, duration = 1500, decimals = 0) {
  const displayValue = ref(0)
  let animationFrame = null
  let startTime = null
  
  // Convertir targetSource en ref si ce n'est pas déjà le cas
  const targetRef = isRef(targetSource) ? targetSource : ref(targetSource)

  /**
   * Fonction d'easing pour une animation fluide
   * Utilise easeOutQuart pour un ralentissement progressif
   */
  const easeOutQuart = (t) => {
    return 1 - Math.pow(1 - t, 4)
  }

  /**
   * Démarre l'animation
   */
  const startAnimation = () => {
    // Récupérer la valeur cible actuelle
    const currentTarget = targetRef.value
    
    // Ne rien faire si la cible est undefined/null ou 0
    if (currentTarget === undefined || currentTarget === null) {
      displayValue.value = 0
      return
    }
    
    // Annuler l'animation précédente si elle existe
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
    }

    startTime = null
    const startValue = displayValue.value // Partir de la valeur actuelle
    const targetValue = currentTarget

    const animate = (currentTime) => {
      if (!startTime) startTime = currentTime
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      
      // Appliquer l'easing
      const easedProgress = easeOutQuart(progress)
      
      // Calculer la valeur actuelle (de startValue à targetValue)
      const currentValue = startValue + (targetValue - startValue) * easedProgress
      displayValue.value = decimals > 0 
        ? parseFloat(currentValue.toFixed(decimals))
        : Math.floor(currentValue)

      // Continuer l'animation si pas terminée
      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate)
      } else {
        // S'assurer que la valeur finale est exacte
        displayValue.value = decimals > 0
          ? parseFloat(targetValue.toFixed(decimals))
          : targetValue
      }
    }

    animationFrame = requestAnimationFrame(animate)
  }

  /**
   * Nettoyer l'animation au démontage
   */
  const cleanup = () => {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
    }
  }

  // CORRECTIF : Observer les changements de targetRef (ref réactive)
  watch(targetRef, (newTarget, oldTarget) => {
    // Ne déclencher que si la valeur a vraiment changé
    if (newTarget !== oldTarget && newTarget !== undefined && newTarget !== null) {
      startAnimation()
    }
  }, { immediate: false })

  // Démarrer l'animation au montage
  onMounted(() => {
    const currentTarget = targetRef.value
    if (currentTarget !== undefined && currentTarget !== null) {
      // Petit délai pour un effet plus visible
      setTimeout(() => {
        startAnimation()
      }, 100)
    }
  })

  // Nettoyer au démontage
  onUnmounted(() => {
    cleanup()
  })

  return {
    displayValue,
    startAnimation,
    cleanup
  }
}

/**
 * Hook simplifié pour animer plusieurs valeurs - VERSION CORRIGÉE
 * 
 * @param {Object|Ref} targetsSource - Objet avec les valeurs cibles (peut être une ref)
 * @param {Number} duration - Durée de l'animation
 * @returns {Object} - Valeurs animées
 */
export function useMultipleCountAnimations(targetsSource, duration = 1500) {
  const animations = {}
  
  // Si targetsSource est une ref, l'utiliser directement
  // Sinon, créer une ref
  const targetsRef = isRef(targetsSource) ? targetsSource : ref(targetsSource)
  
  // Créer les animations pour chaque clé
  const targets = targetsRef.value
  for (const key in targets) {
    const value = targets[key]
    const decimals = typeof value === 'number' && value % 1 !== 0 ? 2 : 0
    
    // CORRECTIF : Créer une computed pour chaque valeur
    const targetComputed = computed(() => targetsRef.value[key])
    
    animations[key] = useCountAnimation(targetComputed, duration, decimals)
  }

  return animations
}

export default useCountAnimation