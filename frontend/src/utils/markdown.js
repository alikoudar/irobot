/**
 * Configuration markdown-it avec highlight.js et DOMPurify
 * 
 * Fonctionnalités :
 * - Rendu markdown complet (tableaux, listes, titres, etc.)
 * - Coloration syntaxique du code avec highlight.js
 * - Protection XSS avec DOMPurify
 * 
 * Sprint 9 - Correction formatage markdown
 * 
 * Fichier : /frontend/src/utils/markdown.js
 */
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

// Import du thème highlight.js (GitHub Dark)
import 'highlight.js/styles/github-dark.css'

// Configuration markdown-it
const md = new MarkdownIt({
  html: false,         // Désactiver HTML brut pour sécurité
  breaks: true,        // Convertir les \n en <br>
  linkify: true,       // Auto-convertir les URLs en liens
  typographer: true,   // Guillemets intelligents, tirets, etc.
  
  // Configuration de la coloration syntaxique
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code class="language-' + lang + '">' +
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>'
      } catch (__) {
        // Ignorer les erreurs de highlighting
      }
    }
    
    // Pas de langage spécifié ou non reconnu
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})

/**
 * Rendre du markdown en HTML sécurisé.
 * 
 * @param {string} markdown - Texte markdown à convertir
 * @returns {string} HTML sécurisé
 * 
 * @example
 * renderMarkdown('# Titre\n\n**Gras** et *italique*')
 * // => '<h1>Titre</h1><p><strong>Gras</strong> et <em>italique</em></p>'
 */
export function renderMarkdown(markdown) {
  if (!markdown) return ''
  
  // Étape 1 : Rendu markdown → HTML
  const html = md.render(markdown)
  
  // Étape 2 : Nettoyage XSS avec DOMPurify
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      // Texte
      'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
      // Titres
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      // Listes
      'ul', 'ol', 'li',
      // Citations
      'blockquote',
      // Liens et images
      'a', 'img',
      // Tableaux
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      // Conteneurs
      'span', 'div'
    ],
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title', 'class', 'target', 'rel',
      'id', 'style'
    ],
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
  })
  
  return clean
}

/**
 * Rendre du markdown inline (sans blocs).
 * 
 * @param {string} markdown - Texte markdown inline
 * @returns {string} HTML sécurisé sans <p>
 * 
 * @example
 * renderMarkdownInline('**Gras** et *italique*')
 * // => '<strong>Gras</strong> et <em>italique</em>'
 */
export function renderMarkdownInline(markdown) {
  if (!markdown) return ''
  
  const html = md.renderInline(markdown)
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['strong', 'em', 'code', 'a', 'span'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class']
  })
  
  return clean
}

// Export par défaut
export default {
  renderMarkdown,
  renderMarkdownInline
}