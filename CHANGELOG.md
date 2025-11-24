# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### À venir - Sprint 9
- Tests E2E Playwright
- Optimisations performance
- Monitoring et métriques

---

## [1.0.0-sprint8] - 2025-11-24

### ✨ Ajouté

#### Phase 1 : Interface Chat Vue.js (2025-11-24)
- **ChatView.vue** :
  - Vue principale du chatbot
  - Sidebar conversations (liste, recherche, archivage)
  - Zone de messages avec scroll automatique
  - Input message avec envoi Enter/Ctrl+Enter
  - Bouton nouvelle conversation
- **MessageBubble.vue** :
  - Affichage messages USER/ASSISTANT
  - Formatage Markdown (listes, code, tableaux)
  - Indicateur de streaming (curseur clignotant)
  - Horodatage et métadonnées
  - Support texte blanc sur fond bleu (USER)
- **SourcesList.vue** :
  - Liste des sources collapsée par défaut
  - Modal détails avec preview du chunk
  - Score de pertinence visuel (barre de progression)
  - Bouton copier l'extrait (cherche dans 15+ champs)
- **FeedbackButtons.vue** :
  - Boutons pouce haut/bas
  - Feedback persisté en base
  - Animation de confirmation
- **ConversationsList.vue** :
  - Liste conversations triées par date
  - Recherche temps réel
  - Actions (archiver, supprimer, renommer)
  - Indicateur conversation active

#### Phase 2 : Store Pinia Chat (2025-11-24)
- **chat.js** :
  - State : conversations, messages, streaming
  - Actions : fetchConversations, sendMessage, addFeedback
  - Support streaming SSE avec `/api/v1/chat/stream`
  - Fallback machine à écrire si pas de streaming
  - Reset automatique au changement d'utilisateur
  - Gestion AbortController pour annulation

#### Phase 3 : Corrections UX (2025-11-24)
- **Texte blanc sur fond bleu** (messages USER)
- **Espacement compact** dans le formatage Markdown
- **Sources après réponse** (pas pendant le streaming)
- **Sources collapsées par défaut**
- **Preview chunk** au lieu de redirection document
- **Stats feedback à 0** par défaut (pas d'estimation)

### 🛠️ Corrigé

#### Frontend
- **Texte utilisateur illisible** :
  - Texte noir sur fond bleu → CSS forcé `color: #ffffff !important`
- **Espacement excessif Markdown** :
  - Listes et paragraphes trop espacés → Parser compact + CSS réduit
- **Bouton copier désactivé** :
  - Condition `!excerpt` bloquante → Cherche dans 15+ champs possibles
- **Redirection "Voir document"** :
  - Utilisateurs sans accès aux documents → Preview du chunk dans modal
- **Stats feedback erronées** :
  - Estimation `Math.ceil(total * 0.1)` → Valeurs à 0 par défaut
- **Sources affichées trop tôt** :
  - Pendant le streaming → Condition `!message.isStreaming` ajoutée
- **Messages d'un autre utilisateur** :
  - Store non réinitialisé → Reset au login/logout dans auth.js

#### Backend
- **`RerankResult.score` inexistant** :
  - Attribut `score` → Corrigé en `relevance_score`
- **Score > 1 (validation Pydantic)** :
  - Scores 0-10 du reranker → Normalisés `/10.0` pour 0-1
- **`batch_insert()` argument manquant** :
  - Un seul argument (batch) → Séparation chunks et vectors
- **`excerpt: null` dans sources** :
  - Texte du chunk non inclus → Ajout dans SourceReference

#### Infrastructure
- **Redémarrage nginx/frontend requis** :
  - DNS cache Nginx → Resolver Docker dynamique avec variable

### 🔧 Modifié

- **auth.js** :
  - Ajout reset du chat store au login
  - Ajout reset du chat store au logout
- **chat.js** :
  - Endpoint `/api/v1/chat/stream` (au lieu de `/chat/send`)
  - Support roles MAJUSCULE (USER, ASSISTANT)
  - Détection changement d'utilisateur
- **MessageBubble.vue** :
  - CSS `.user .message-text { color: #ffffff !important }`
  - Parser Markdown compact `parseListsCompact()`
  - Condition sources `&& !message.isStreaming`
- **SourcesList.vue** :
  - `expanded = ref(false)` (collapsé par défaut)
  - `excerptContent` cherche dans 15+ champs
  - Bouton "Voir document" supprimé → Preview chunk
- **ProfileStats.vue** :
  - Stats à 0 par défaut, chargement depuis API uniquement
- **nginx_dev.conf** :
  - Ajout `resolver 127.0.0.11 valid=10s`
  - Variables pour `proxy_pass` (résolution DNS dynamique)
- **indexing_tasks.py** :
  - Séparation `chunks_data` et `vectors_data`
  - Appel `batch_insert(chunks, vectors)`
- **chat_service.py** :
  - `result.relevance_score` au lieu de `result.score`
  - Normalisation score `/10.0` pour SourceReference
  - Ajout `excerpt` dans les sources

### 📊 Statistiques Sprint 8

- **Fichiers créés** : 8 fichiers frontend
  - ChatView.vue (~450 lignes)
  - MessageBubble.vue (~745 lignes)
  - SourcesList.vue (~485 lignes)
  - FeedbackButtons.vue (~200 lignes)
  - ConversationsList.vue (~350 lignes)
  - chat.js store (~890 lignes)
  - ProfileStats.vue (~540 lignes)
  - auth.js modifié (~250 lignes)
- **Fichiers corrigés** : 5 fichiers
  - nginx_dev.conf
  - indexing_tasks.py
  - chat_service.py
  - MessageBubble.vue (corrections V2)
  - SourcesList.vue (corrections V2)
- **Lignes de code** : ~3900 lignes
- **Corrections** : 12 bugs (7 frontend, 4 backend, 1 infra)
- **Durée** : 1 jour

### 🎯 Objectifs Sprint 8 - Atteints

- ✅ Interface Chat Vue.js complète
- ✅ Composants conversation réutilisables
- ✅ Affichage sources avec preview chunk
- ✅ Streaming SSE temps réel
- ✅ Feedbacks utilisateur (pouce haut/bas)
- ✅ Formatage Markdown des réponses
- ✅ Reset store au changement d'utilisateur
- ✅ Sources collapsées par défaut
- ✅ Résolution DNS Nginx dynamique
- ✅ Corrections UX multiples

### 📦 Fichiers Livrés

```
frontend/src/views/
├── ChatView.vue                 # Vue principale chat

frontend/src/components/chat/
├── MessageBubble.vue            # Bulle de message
├── SourcesList.vue              # Liste sources collapsable
├── FeedbackButtons.vue          # Boutons feedback
├── ConversationsList.vue        # Sidebar conversations

frontend/src/components/profile/
├── ProfileStats.vue             # Stats utilisateur

frontend/src/stores/
├── chat.js                      # Store Pinia chat
├── auth.js                      # Store auth (modifié)

backend/app/workers/
├── indexing_tasks.py            # Worker indexation (corrigé)

backend/app/services/
├── chat_service.py              # Service chat (corrigé)

nginx/
├── nginx_dev.conf               # Config Nginx (corrigé)
```

---

## [1.0.0-sprint7] - 2025-11-24

### ✨ Ajouté

#### Phase 1 : Schémas Chat (2025-11-23)
- **ChatRequest** :
  - Validation message (1-10000 caractères)
  - conversation_id optionnel (reprise conversation)
  - stream (défaut: true pour SSE)
  - category_filter optionnel
- **ChatResponse** :
  - conversation_id, message_id
  - content (réponse générée)
  - sources (liste documents avec scores)
  - token_count_input/output, cost_usd/xaf
  - cache_hit, response_time_seconds, model_used
- **StreamChunk** :
  - Types: token, metadata, sources, error, done
  - Format SSE compatible
- **SourceReference** :
  - document_id, title, category
  - page, chunk_index, relevance_score, excerpt
- **ConversationSummary**, **ConversationDetail** :
  - Gestion conversations avec messages

#### Phase 2 : Prompts Système (2025-11-23)
- **PromptBuilder** :
  - build_system_prompt() - Prompt BEAC strict
  - build_context_section() - Formatage chunks (SANS scores)
  - build_history_section() - Historique conversation
  - build_full_prompt() - Assemblage complet
  - detect_response_format() - Auto-détection format
- **ResponseFormat** (Enum) :
  - DEFAULT, TABLE, LIST, NUMBERED
  - CODE, COMPARISON, CHRONOLOGICAL, STEP_BY_STEP
- **Prompt système strict** :
  - Interdit hallucinations et recommandations
  - Interdit "à titre indicatif", "processus générique"
  - Utilisation UNIQUEMENT du contexte fourni
  - Citations obligatoires [Document X]
- **ChunkForPrompt**, **HistoryMessage** :
  - Dataclasses pour formatage prompt

#### Phase 3 : Generator LLM (2025-11-23)
- **MistralGenerator** :
  - generate() - Génération synchrone
  - generate_streaming() - AsyncGenerator SSE
  - generate_title() - Titre conversation (max 50 chars)
- **StreamedChunk** (dataclass) :
  - type: "token" | "metadata" | "error"
  - content: texte du token
  - metadata: GenerationMetadata optionnel
- **GenerationMetadata** :
  - tokens_input/output, cost_usd/xaf
  - model_used, response_time
- **Calcul coûts** :
  - Tarifs depuis DB (ConfigService)
  - Taux de change depuis exchange_rates
  - Support USD et XAF

#### Phase 4 : Endpoints Chat (2025-11-23)
- **POST /v1/chat** :
  - Création/reprise conversation
  - Mode synchrone et streaming SSE
  - Cache L1/L2 intégré
  - Token tracking automatique
- **GET /v1/chat/conversations** :
  - Liste conversations utilisateur
  - Pagination et tri
- **GET /v1/chat/conversations/{id}** :
  - Détails conversation avec messages
- **DELETE /v1/chat/conversations/{id}** :
  - Suppression conversation
- **POST /v1/chat/conversations/{id}/title** :
  - Génération titre automatique

#### Phase 5 : Tests Unitaires (2025-11-23)
- **test_schemas_sprint7.py** (~450 lignes, 35 tests) :
  - Validation ChatRequest, ChatResponse
  - StreamChunk, SourceReference
  - ConversationSummary, ConversationDetail
- **test_prompts.py** (~500 lignes, 40 tests) :
  - PromptBuilder complet
  - Détection format automatique
  - Formatage contexte et historique
- **test_chat_service.py** (~550 lignes, 35 tests) :
  - Pipeline RAG complet
  - Cache hit/miss
  - Token tracking
- **test_chat_endpoints.py** (~450 lignes, 25 tests) :
  - Endpoints HTTP
  - Authentification
  - Streaming SSE

### 🛠️ Corrigé

- **Erreur `content` vs `text`** :
  - Weaviate stocke le texte dans `content`, pas `text`
  - Retriever corrigé pour mapper `content` → `text`
  - Chunks maintenant transmis au LLM avec contenu
- **Erreur `_additional.score`** :
  - weaviate_client retournait score au mauvais niveau
  - Corrigé pour format `_additional.score` attendu par retriever
- **Erreur `OperationType.GENERATION`** :
  - Enum inexistant → remplacé par `RESPONSE_GENERATION`
- **Erreur `exchange_rate` NULL** :
  - Colonne NOT NULL non renseignée
  - Ajout récupération taux depuis DB
- **Erreur `ForeignKeyViolation cache_document_map`** :
  - document_ids Weaviate ≠ document_ids PostgreSQL
  - Ajout validation `_validate_document_ids()`
- **Erreur `ChunkForPrompt` arguments** :
  - Utilisait `content` au lieu de `text`
  - Corrigé mapping attributs
- **Erreur `build_system_prompt()` argument** :
  - Méthode sans paramètre, appelée avec `response_format`
  - Corrigé appel
- **Erreur `async for` requires `__aiter__`** :
  - Mistral SDK synchrone dans contexte async
  - Implémentation AsyncGenerator avec `run_in_executor`
- **Erreur scores 0%** :
  - Score non transmis correctement depuis Weaviate
  - Format `_additional.score` corrigé
- **Hallucinations et recommandations** :
  - Prompt système trop permissif
  - Nouveau prompt strict avec interdictions explicites
  - Température réduite de 0.7 à 0.2
- **Scores affichés aux utilisateurs** :
  - Template prompt affichait `Pertinence: X%`
  - Retiré du template (info interne uniquement)

### 🔧 Modifié

- **retriever.py** :
  - Propriétés Weaviate : `content` au lieu de `text`
  - Mapping `content` → `text` dans `_process_results()`
- **weaviate_client.py** :
  - Nouvelle méthode async `hybrid_search()`
  - Format retour avec `_additional.score`
- **prompts.py** :
  - Prompt système strict (interdictions explicites)
  - Template sans scores de pertinence
  - Instructions de fin renforcées
- **generator.py** :
  - AsyncGenerator compatible `async for`
  - Import depuis `mistral_client`
  - Interface StreamedChunk correcte
- **cache_service.py** :
  - Validation document_ids avant insertion
  - Protection ForeignKeyViolation
- **cache_statistics.py** :
  - Protection division par zéro
  - Protection None + int
- **chat_service.py** :
  - OperationType.RESPONSE_GENERATION
  - exchange_rate depuis DB

### 📊 Statistiques Sprint 7

- **Fichiers créés** : 8 fichiers
  - chat.py (schémas ~300 lignes)
  - prompts.py (~500 lignes)
  - generator.py (~580 lignes)
  - chat_service.py (~1130 lignes)
  - chat_endpoints.py (~250 lignes)
  - Tests (4 fichiers ~1950 lignes)
- **Fichiers corrigés** : 6 fichiers
  - retriever.py
  - weaviate_client.py
  - cache_service.py
  - cache_statistics.py
  - prompts.py (prompt strict)
  - chat_service.py
- **Lignes de code** : ~4700 lignes
- **Tests** : 135 tests (35 + 40 + 35 + 25)
- **Corrections** : 12 bugs majeurs
- **Durée** : 2 jours

### 🎯 Objectifs Sprint 7 - Atteints

- ✅ Generator LLM avec Mistral
- ✅ Streaming SSE fonctionnel
- ✅ Prompts système BEAC stricts
- ✅ Pipeline RAG complet bout-en-bout
- ✅ Cache L1/L2 intégré
- ✅ Token tracking et coûts USD/XAF
- ✅ Génération titres automatique
- ✅ Endpoints Chat REST
- ✅ Tests > 80% (135 tests)
- ✅ Corrections bugs intégration

### 📦 Fichiers Livrés

```
backend/app/schemas/
├── chat.py                  # Schémas Chat (ChatRequest, ChatResponse, etc.)

backend/app/rag/
├── prompts.py               # PromptBuilder + Prompt système strict
├── generator.py             # MistralGenerator + Streaming
├── retriever.py             # HybridRetriever (CORRIGÉ: content)

backend/app/services/
├── chat_service.py          # ChatService complet
├── cache_service.py         # CacheService (CORRIGÉ: validation FK)

backend/app/clients/
├── weaviate_client.py       # WeaviateClient (CORRIGÉ: _additional.score)

backend/app/api/v1/
├── chat.py                  # Endpoints Chat

backend/app/models/
├── cache_statistics.py      # (CORRIGÉ: protection None)

tests/
├── test_schemas_sprint7.py      # Tests schémas (35)
├── test_prompts.py              # Tests prompts (40)
├── test_chat_service.py         # Tests service (35)
├── test_chat_endpoints.py       # Tests endpoints (25)
```

### 🔄 Pipeline RAG Complet

```
Question utilisateur
       ↓
┌─────────────────────────┐
│  CACHE L1 (Hash exact)  │
│  SHA-256 normalisé      │
└───────────┬─────────────┘
            │
       HIT? ├─────────────────────────┐
            │ NO                      │ YES
            ↓                         ↓
┌─────────────────────────┐    ┌──────────────────┐
│  CACHE L2 (Similarité)  │    │  RETURN CACHED   │
│  Cosine > 0.95          │    │  + increment_hit │
└───────────┬─────────────┘    │  + reset_ttl     │
            │                   └──────────────────┘
       HIT? ├─────────────────────────┐
            │ NO                      │ YES
            ↓                         ↓
┌─────────────────────────┐    ┌──────────────────┐
│  EMBEDDING              │    │  RETURN SIMILAR  │
│  mistral-embed          │    │  + increment_hit │
└───────────┬─────────────┘    └──────────────────┘
            ↓
┌─────────────────────────┐
│  RECHERCHE HYBRIDE      │
│  BM25 + Semantic (α=0.7)│
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  RERANKING              │
│  Top 10 → Top 3         │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  GÉNÉRATION LLM         │
│  Mistral + Streaming    │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  SAVE TO CACHE          │
│  + Token tracking       │
└─────────────────────────┘
```

---

## [1.0.0-sprint6] - 2025-11-23

### ✨ Ajouté

#### Phase 1 : Retriever Hybride (2025-11-23)
- **HybridRetriever** :
  - Recherche hybride BM25 + sémantique
  - Paramètre alpha configurable (0=BM25, 1=semantic)
  - Filtres par catégorie, document_id
  - Score fusion pondéré
- **Configurations depuis DB** :
  - search.top_k (défaut: 10)
  - search.hybrid_alpha (défaut: 0.7)
- **RetrievedChunk** (dataclass) :
  - chunk_id, document_id, text, score
  - Métadonnées : title, category, page, chunk_index

#### Phase 2 : Reranker Mistral (2025-11-23)
- **MistralReranker** :
  - Évaluation pertinence avec mistral-small
  - Prompt JSON structuré (score 0-10 + reason)
  - Tri par score décroissant
  - Top N configurable depuis DB
- **RerankResult** :
  - chunk, relevance_score, reasoning
  - Méthodes : to_dict(), to_source_dict()
- **Configurations dynamiques** :
  - models.reranking.model_name, models.reranking.top_k

#### Phase 3 : Cache Service (2025-11-23)
- **CacheService** :
  - check_cache_level1() - Hash exact SHA-256
  - check_cache_level2() - Similarité cosine > 0.95
  - save_to_cache() - Sauvegarde avec mappings
  - invalidate_cache_for_document() - Invalidation cascade
  - get_statistics() - Stats agrégées
- **Configurations depuis DB** :
  - cache.query_ttl_seconds (défaut: 604800 = 7 jours)
  - cache.similarity_threshold (défaut: 0.95)

#### Phase 4 : Tests Complets (2025-11-23)
- **Tests Modèles Cache** (40 tests)
- **Tests Retriever & Reranker** (27 tests)
- **Tests CacheService** (41 tests)

### 📊 Statistiques Sprint 6

- **Fichiers créés** : 7 fichiers
- **Lignes de code** : ~3500 lignes
- **Tests** : 108 tests
- **Durée** : 2 jours

---

## [1.0.0-sprint5] - 2025-11-23

### ✨ Ajouté

#### Phase 1 : Client Mistral (2025-11-23)
- **MistralClient** :
  - generate_embeddings() - Embedding texte
  - generate_embeddings_batch() - Batch embeddings
  - process_image_ocr() - OCR images
  - chat_completion() - Chat LLM
- **Gestion erreurs et retry** :
  - Retry exponentiel (3 tentatives)
  - Timeout configurable
  - Logging détaillé

#### Phase 2 : Client Weaviate (2025-11-23)
- **WeaviateClient** :
  - create_collection() - Création schema
  - batch_insert() - Insertion batch
  - hybrid_search() - Recherche hybride
  - delete_document_chunks() - Suppression

#### Phase 3 : Workers Embedding (2025-11-23)
- **embedding_tasks.py** :
  - embed_chunks - Embedding par batch
  - Gestion erreurs par chunk
  - Mise à jour métadonnées

#### Phase 4 : Workers Indexation (2025-11-23)
- **indexing_tasks.py** :
  - index_to_weaviate - Indexation Weaviate
  - Batch insert avec retry
  - Nettoyage embeddings après indexation

### 📊 Statistiques Sprint 5

- **Fichiers créés** : 5 fichiers
- **Lignes de code** : ~2000 lignes
- **Durée** : 1 jour

---

## [1.0.0-sprint4] - 2025-11-22

### ✨ Ajouté

#### Phase 1 : Extraction Documents (2025-11-22)
- **DocumentProcessor** :
  - Extraction PDF (PyMuPDF + OCR fallback)
  - Extraction DOCX, XLSX, PPTX
  - Extraction TXT, MD, RTF
  - OCR images intégrées

#### Phase 2 : Workers Celery (2025-11-22)
- **processing_tasks.py** :
  - process_document - Extraction texte
  - Chaînage vers chunking
- **chunking_tasks.py** :
  - chunk_document - Découpage intelligent
  - Overlap configurable

### 📊 Statistiques Sprint 4

- **Fichiers créés** : 8 fichiers
- **Lignes de code** : ~1500 lignes
- **Formats supportés** : 10 formats
- **Durée** : 1 jour

---

## [1.0.0-sprint3] - 2025-11-22

### ✨ Ajouté

#### Phase 1 : Backend Catégories (2025-11-22)
- **CRUD catégories complet**
- **6 Schemas Pydantic**
- **Service CategoryService**
- **Permissions par rôle**

#### Phase 2 : Seeds Catégories (2025-11-22)
- **4 catégories initiales BEAC**

#### Phase 3 : Frontend Catégories (2025-11-22)
- **Store Pinia categories.js**
- **Composant CategoryForm.vue**
- **Vue admin/Categories.vue**

### 📊 Statistiques Sprint 3

- **Fichiers créés/modifiés** : 18 fichiers
- **Lignes de code** : ~2450 lignes
- **Tests** : 20 tests unitaires
- **Durée** : 1 jour

---

## [1.0.0-sprint2] - 2025-11-22

### ✨ Ajouté

#### Phase 1 : Authentification JWT (2025-11-22)
- Login avec access + refresh tokens
- Changement mot de passe obligatoire
- Logout avec invalidation token

#### Phase 2 : Gestion Utilisateurs (2025-11-22)
- CRUD utilisateurs complet (admin)
- Import Excel utilisateurs

#### Phase 3 : Interface Admin (2025-11-22)
- Dashboard admin
- Table utilisateurs paginée

### 📊 Statistiques Sprint 2

- **Fichiers créés/modifiés** : ~45 fichiers
- **Lignes de code** : ~4500 lignes
- **Tests** : 60+ tests
- **Durée** : 3 jours

---

## [1.0.0-sprint1] - 2025-11-21

### ✨ Ajouté

#### Phase 1 : Infrastructure Docker (2025-11-21)
- Docker Compose avec 6 services
- PostgreSQL, Redis, Weaviate, Backend, Frontend, Nginx

#### Phase 2 : Base de Données (2025-11-21)
- 10 modèles SQLAlchemy
- Alembic migrations
- 40+ indexes optimisés

#### Phase 3 : Tests Unitaires (2025-11-21)
- 33 tests unitaires
- Coverage >80%

### 📊 Statistiques Sprint 1

- **Fichiers créés** : ~65 fichiers
- **Lignes de code** : ~3000 lignes
- **Tests** : 33 tests
- **Coverage** : 90.86%
- **Durée** : 2 jours

---

## Notes de Version

### [1.0.0-sprint8] - 2025-11-24

**Résumé** : Interface Chat Vue.js complète avec streaming et corrections UX.

**Nouveautés** :
- 💬 Interface Chat complète (5 composants)
- 📡 Streaming SSE temps réel
- 📚 Sources collapsables avec preview chunk
- 👍 Feedbacks utilisateur
- 🔄 Reset store au changement utilisateur
- 🔧 12 corrections (frontend, backend, infra)

**Prérequis** :
- Sprint 1-7 complétés
- Backend avec endpoints `/v1/chat/stream`
- Weaviate avec chunks indexés

**Installation** :
```bash
# Frontend
cp sprint8-fixes-v2/components/chat/* frontend/src/components/chat/
cp sprint8-fixes-v2/components/profile/* frontend/src/components/profile/
cp sprint8-fixes-v2/stores/* frontend/src/stores/

# Backend
cp sprint8-fixes-v2/backend/workers/indexing_tasks.py backend/app/workers/

# Nginx
cp sprint8-fixes-v2/nginx/nginx_dev.conf nginx/

# Restart
docker-compose restart
```

### [1.0.0-sprint7] - 2025-11-24

**Résumé** : Pipeline RAG complet avec génération LLM et streaming SSE.

**Installation** :
```bash
docker-compose restart backend
```

---

## Conventions

### Types de Changements

- **Ajouté** : Nouvelles fonctionnalités
- **Modifié** : Changements dans les fonctionnalités existantes
- **Déprécié** : Fonctionnalités bientôt supprimées
- **Supprimé** : Fonctionnalités supprimées
- **Corrigé** : Corrections de bugs
- **Sécurité** : Correctifs de sécurité

---

## Liens

- [Documentation complète](README.md)
- [Guide de démarrage](GUIDE_DEMARRAGE.md)
- [Architecture technique](IROBOT_DOC_1_ARCHITECTURE_TECHNIQUE.md)
- [Plan de développement](IROBOT_DOC_2_PLAN_DEVELOPPEMENT_PARTIE_1.md)

---

**Maintenu par** : Équipe IroBot - BEAC  
**Format** : [Keep a Changelog](https://keepachangelog.com/)  
**Versioning** : [Semantic Versioning](https://semver.org/)