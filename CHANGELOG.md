# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### À venir - Sprint 8
- Interface Chat Vue.js
- Composants conversation
- Affichage sources et citations
- Tests E2E Playwright

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
│  PIPELINE RAG COMPLET   │    │  RETURN CACHED   │
│  1. Embedding question  │    │  (similarity)    │
│  2. Hybrid search (10)  │    └──────────────────┘
│  3. Reranking (3)       │
│  4. PromptBuilder       │  ← NOUVEAU Sprint 7
│  5. MistralGenerator    │  ← NOUVEAU Sprint 7
│  6. Streaming SSE       │  ← NOUVEAU Sprint 7
│  7. save_to_cache()     │
│  8. track_token_usage() │  ← NOUVEAU Sprint 7
└─────────────────────────┘
```

### ⚠️ Limitations Actuelles

- Frontend chat non développé (Sprint 8)
- WebSocket non implémenté (SSE utilisé)
- Historique conversation limité à 5 messages
- Pas de feedback utilisateur (Sprint 9)

### 🚀 Prochaines Étapes (Sprint 8)

1. **Interface Chat Vue.js** :
   - Composant ChatWindow.vue
   - Composant MessageBubble.vue
   - Composant SourceCard.vue

2. **Streaming Frontend** :
   - EventSource SSE
   - Affichage progressif tokens
   - Indicateur "typing..."

3. **Gestion Conversations** :
   - Liste conversations sidebar
   - Nouvelle conversation
   - Suppression conversation

4. **Tests E2E** :
   - Playwright tests
   - Scénarios complets

---

## [1.0.0-sprint6] - 2025-11-23

### ✨ Ajouté

#### Phase 1 : Modèles Cache (2025-11-23)
- **QueryCache** :
  - Stockage questions/réponses avec hash SHA-256
  - Embedding vectoriel 1024 dimensions pour similarité
  - TTL 7 jours configurable
  - Métriques : hit_count, tokens économisés, coûts USD/XAF
  - Méthodes : is_expired(), increment_hit(), reset_ttl()
- **CacheDocumentMap** :
  - Mapping N:N cache ↔ documents
  - Clés étrangères avec CASCADE
  - Index pour invalidation rapide
- **CacheStatistics** :
  - Statistiques journalières agrégées
  - hit_rate calculé automatiquement
  - Méthodes : increment_hit(), increment_miss(), get_summary()
- **Schémas Pydantic** :
  - QueryCacheCreate, QueryCacheResponse, CacheHitResponse
  - CacheStatisticsResponse, CacheDashboardStats
- **Migration Alembic** :
  - sprint6_001_cache_models.py
  - 3 tables avec index optimisés

#### Phase 2 : Retriever & Reranker (2025-11-23)
- **HybridRetriever** :
  - Recherche hybride BM25 + Sémantique dans Weaviate
  - Alpha configurable depuis DB (défaut: 0.75)
  - Top-K configurable depuis DB (défaut: 10)
  - Filtres par catégorie et documents
  - Singleton : get_retriever()
- **MistralReranker** :
  - Reranking avec mistral-small-latest
  - Scoring 0-10 avec reasoning
  - Top-N configurable depuis DB (défaut: 3)
  - Tarifs lus depuis DB
  - Singleton : get_reranker()
- **RetrievedChunk** :
  - Dataclass avec scores BM25/vector
  - Méthodes : to_dict(), to_source_dict()
- **RerankResult** :
  - Score de pertinence + explanation
- **Configurations dynamiques** :
  - search.top_k, search.hybrid_alpha
  - models.reranking.model_name, models.reranking.top_k
  - mistral.pricing.small

#### Phase 3 : Cache Service (2025-11-23)
- **CacheService** :
  - check_cache_level1() - Hash exact SHA-256
  - check_cache_level2() - Similarité cosine > 0.95
  - check_cache() - Combiné L1 puis L2
  - save_to_cache() - Sauvegarde avec mappings
  - invalidate_cache_for_document() - Invalidation cascade
  - invalidate_expired_cache() - Nettoyage périodique
  - get_statistics() - Stats agrégées
- **Utilitaires mathématiques** :
  - cosine_similarity() - Similarité vectorielle
  - compute_query_hash() - Hash normalisé
- **Configurations depuis DB** :
  - cache.query_ttl_seconds (défaut: 604800 = 7 jours)
  - cache.similarity_threshold (défaut: 0.95)
- **Singleton** : get_cache_service()

#### Phase 4 : Tests Complets (2025-11-23)
- **Tests Modèles Cache** (40 tests) :
  - QueryCache : création, hash, expiration, hits
  - CacheDocumentMap : création, relations
  - CacheStatistics : hit_rate, increment, summary
- **Tests Retriever & Reranker** (27 tests) :
  - Config depuis DB
  - Recherche hybride, filtres
  - Reranking, scoring
  - Pipeline intégré
- **Tests CacheService** (41 tests) :
  - Cosine similarity
  - Cache L1 hit/miss
  - Cache L2 hit/miss (similarité)
  - Sauvegarde, invalidation
  - TTL reset on hit
  - Statistiques

### 🔧 Modifié

- **Architecture configs** :
  - Toutes les configs RAG lues depuis system_configs via ConfigService
  - Pattern identique à mistral_client.py
  - Fallback si DB non disponible
- **Package app/rag/** :
  - Ajout retriever.py, reranker.py
  - Export dans __init__.py
- **Package app/services/** :
  - Ajout cache_service.py

### 📊 Statistiques Sprint 6

- **Fichiers créés** : 9 fichiers
  - query_cache.py (~250 lignes)
  - cache_document_map.py (~120 lignes)
  - cache_statistics.py (~280 lignes)
  - cache.py (schémas ~350 lignes)
  - retriever.py (~450 lignes)
  - reranker.py (~400 lignes)
  - cache_service.py (~550 lignes)
  - Migration Alembic (~250 lignes)
  - Tests simples (3 fichiers ~2000 lignes)
- **Lignes de code** : ~4650 lignes
- **Tests** : 108 tests (40 + 27 + 41)
- **Coverage** : >90%
- **Durée** : 7 jours

### 🎯 Objectifs Sprint 6 - Atteints

- ✅ Hybrid search fonctionnel (BM25 + Sémantique)
- ✅ Reranking avec Mistral OK
- ✅ Cache L1 (correspondance exacte via hash) OK
- ✅ Cache L2 (similarité > 0.95) OK
- ✅ Invalidation cache par document OK
- ✅ Stats cache calculées (hit_rate, tokens, coûts)
- ✅ Configs depuis DB (ConfigService)
- ✅ Tests > 80% (108 tests passés)

### 📦 Fichiers Livrés

```
backend/app/models/
├── query_cache.py           # Modèle cache Q/R
├── cache_document_map.py    # Mapping cache ↔ documents
├── cache_statistics.py      # Statistiques journalières

backend/app/schemas/
├── cache.py                 # Schémas Pydantic cache

backend/app/rag/
├── retriever.py             # HybridRetriever
├── reranker.py              # MistralReranker
├── __init__.py              # Exports package

backend/app/services/
├── cache_service.py         # CacheService complet

backend/alembic/versions/
├── sprint6_001_cache_models.py  # Migration tables cache

tests/
├── test_cache_models_simple.py      # Tests modèles (40)
├── test_retriever_reranker_simple.py # Tests RAG (27)
├── test_cache_service_simple.py     # Tests service (41)
```

---

## [1.0.0-sprint4] - 2025-11-23

### ✨ Ajouté

#### Phase 1 : Pipeline Extraction Documents (2025-11-23)
- **DocumentProcessor hybride** :
  - Extraction texte natif PDF (pypdf)
  - Extraction DOCX (python-docx)
  - Extraction PPTX (python-pptx)
  - Extraction XLSX (openpyxl)
  - Extraction TXT, MD, RTF
  - OCR Mistral pour images intégrées
  - Détection automatique PDF scanné vs natif
  - Méthode d'extraction : TEXT, OCR, HYBRID, FALLBACK
- **MistralOCRClient** :
  - extract_text_from_image() - OCR image unique
  - extract_text_from_pdf() - OCR PDF complet
  - batch_process_images() - OCR batch
  - Support formats : PNG, JPG, JPEG, WEBP, GIF
  - Retour Markdown structuré (tableaux, titres)

#### Phase 2 : Workers Celery (2025-11-23)
- **Processing Worker** (celery-worker-processing) :
  - extract_document_text() - Extraction hybride
  - Nettoyage caractères NULL (\u0000) pour PostgreSQL
  - Estimation pages pour DOCX/TXT (2500 chars/page)
  - Mise à jour colonnes OCR (has_images, image_count, etc.)
  - Retry automatique (max 3, backoff exponentiel)
- **Chunking Worker** (celery-worker-chunking) :
  - chunk_document() - Découpage intelligent
  - Nettoyage artefacts OCR (--Mo, \-n, etc.)
  - Préservation structure (tableaux, listes)
  - Métadonnées enrichies par chunk
  - Détection langue document
  - Génération weaviate_id temporaire

#### Phase 3 : Modèle Document enrichi (2025-11-23)
- **Nouvelles colonnes OCR** :
  - has_images (BOOLEAN) - Document avec images OCR
  - image_count (INTEGER) - Nombre d'images traitées
  - ocr_completed (BOOLEAN) - OCR effectué
  - extraction_method (VARCHAR) - TEXT, OCR, HYBRID, FALLBACK
- **Migration Alembic** :
  - 20241124_add_ocr_columns.py
  - Index sur extraction_method et has_images
  - Compatible documents existants

#### Phase 4 : Module Text Cleaner (2025-11-23)
- **text_cleaner.py** :
  - sanitize_text_for_postgres() - Supprime \u0000
  - remove_ocr_artifacts() - Nettoie artefacts OCR
  - normalize_whitespace() - Normalise espaces
  - clean_punctuation() - Corrige ponctuation
  - detect_document_language() - Détection fr/en
  - extract_document_title() - Extraction titre

### 🔧 Modifié

- **Modèle Document** :
  - Ajout 4 colonnes OCR (has_images, image_count, ocr_completed, extraction_method)
  - Enums en MAJUSCULES (DocumentStatus, ProcessingStage, ExtractionMethod)
  - Méthodes helper : update_extraction_info(), update_chunking_info()
- **Modèle Chunk** :
  - weaviate_id généré temporairement (UUID)
  - Métadonnées enrichies (has_ocr_content, has_table, document_language)
- **Configuration Celery** :
  - Queue "processing" pour extraction
  - Queue "chunking" pour découpage
  - Retry avec backoff exponentiel

### 🛠️ Corrigé

- **Erreur PostgreSQL \u0000** :
  - Caractères NULL dans texte extrait
  - Solution : sanitize_text_for_postgres() avant stockage
- **Erreur weaviate_id NOT NULL** :
  - Contrainte NOT NULL sur chunks.weaviate_id
  - Solution : UUID temporaire généré au chunking
- **Estimation pages DOCX** :
  - Retournait toujours 1 page
  - Solution : Estimation basée sur caractères (2500/page)
- **Artefacts OCR** :
  - Fragments "--Mo", "\-n" dans texte
  - Solution : Module text_cleaner avec regex

### 📊 Statistiques Sprint 4

- **Fichiers créés** : 8 fichiers
  - document_processor.py (~400 lignes)
  - ocr_processor.py (~150 lignes)
  - processing_tasks.py (~350 lignes)
  - chunking_tasks.py (~300 lignes)
  - text_cleaner.py (~200 lignes)
  - Migration Alembic (~80 lignes)
- **Lignes de code** : ~1500 lignes
- **Workers Celery** : 2 workers (processing, chunking)
- **Formats supportés** : 10 formats (PDF, DOCX, XLSX, PPTX, TXT, MD, RTF, PNG, JPG, etc.)
- **Durée** : 1 jour

### 🎯 Objectifs Sprint 4 - Atteints

- ✅ Extraction texte tous formats (PDF, DOCX, XLSX, PPTX, TXT, MD, RTF)
- ✅ OCR Mistral pour images intégrées
- ✅ Détection automatique PDF scanné
- ✅ Pipeline asynchrone Celery (processing → chunking)
- ✅ Chunking intelligent avec overlap
- ✅ Nettoyage artefacts OCR
- ✅ Métadonnées enrichies (langue, titre, has_ocr)
- ✅ Estimation pages pour formats sans pagination
- ✅ Colonnes OCR en base (has_images, extraction_method)
- ✅ Enums MAJUSCULES (norme projet)

### 📦 Fichiers Livrés

```
backend/app/rag/
├── document_processor.py      # Extraction hybride
├── ocr_processor.py           # Client Mistral OCR
├── text_cleaner.py            # Nettoyage texte

backend/app/workers/
├── processing_tasks.py        # Worker extraction
├── chunking_tasks.py          # Worker chunking

backend/alembic/versions/
├── 20241124_add_ocr_columns.py  # Migration OCR
```

---

## [1.0.0-sprint3] - 2025-11-22

### ✨ Ajouté

#### Phase 1 : Backend Catégories (2025-11-22)
- **CRUD catégories complet** :
  - GET /categories - Liste paginée avec recherche
  - POST /categories - Création catégorie
  - GET /categories/{category_id} - Détails catégorie
  - PUT /categories/{category_id} - Modification catégorie
  - DELETE /categories/{category_id} - Suppression catégorie
- **Modèle Category** :
  - Champs : id, name, description, color, created_by, timestamps
  - Relation vers User (créateur)
  - Validation unicité du nom
- **6 Schemas Pydantic** :
  - CategoryBase, CategoryCreate, CategoryUpdate
  - CategoryResponse, CategoryWithStats, CategoryList
- **Service CategoryService** :
  - 8 méthodes (get_categories, create, update, delete, etc.)
  - Pagination et recherche full-text
  - Statistiques (count documents par catégorie)
- **Permissions par rôle** :
  - Admin : CRUD complet
  - Manager : CRUD complet
  - User : Aucun accès (403 Forbidden)

#### Phase 2 : Seeds Catégories (2025-11-22)
- **4 catégories initiales BEAC** :
  - Lettres Circulaires (#005CA9 - Bleu BEAC)
  - Décisions du Gouverneur (#C2A712 - Or BEAC)
  - Procédures et Modes Opératoires (#4A90E2 - Bleu clair)
  - Clauses et Conditions Générales (#50C878 - Vert émeraude)

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
- Changement mot de passe obligatoire (first login)
- Logout avec invalidation token
- Refresh token automatique

#### Phase 2 : Gestion Utilisateurs (2025-11-22)
- CRUD utilisateurs complet (admin)
- Import Excel utilisateurs
- Activation/désactivation comptes
- Reset mot de passe

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
- Hot reload activé

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

### [1.0.0-sprint7] - 2025-11-24

**Résumé** : Pipeline RAG complet avec génération LLM et streaming SSE.

**Nouveautés** :
- 🤖 Generator Mistral avec streaming SSE
- 📝 Prompts système BEAC stricts (anti-hallucination)
- 💬 Endpoints Chat REST complets
- 📊 Token tracking et calcul coûts
- 🔧 12 corrections bugs intégration
- ✅ 135 tests unitaires

**Prérequis** :
- Sprint 1-6 complétés
- Clé API Mistral configurée
- Weaviate avec chunks indexés

**Installation** :
```bash
# Copier les fichiers corrigés
cp retriever_fixed.py backend/app/rag/retriever.py
cp prompts_fixed.py backend/app/rag/prompts.py
cp generator_fixed.py backend/app/rag/generator.py
cp weaviate_client_fixed.py backend/app/clients/weaviate_client.py
cp cache_service_fixed.py backend/app/services/cache_service.py

# Réduire température (recommandé)
docker exec -it irobot-db-1 psql -U irobot -d irobot_db -c "
UPDATE system_configs 
SET value = '{\"model_name\": \"mistral-medium-latest\", \"max_tokens\": 2048, \"temperature\": 0.2}'
WHERE key = 'models.generation';
"

# Vider le cache
docker exec -it irobot-db-1 psql -U irobot -d irobot_db -c "DELETE FROM query_cache;"

# Restart
docker-compose restart backend
```

### [1.0.0-sprint6] - 2025-11-23

**Résumé** : Recherche hybride et cache intelligent 2 niveaux.

**Nouveautés** :
- 🔍 Recherche hybride BM25 + Sémantique
- 🎯 Reranking Mistral (top 10 → top 3)
- 💾 Cache L1 (hash exact) + L2 (similarité > 95%)
- ⚡ Invalidation automatique par document
- 📊 Statistiques cache (hit_rate, économies)
- ⚙️ Configs dynamiques depuis DB

**Prérequis** :
- Sprint 1-4 complétés
- Clé API Mistral configurée
- Weaviate opérationnel

**Installation** :
```bash
# Appliquer migration
docker-compose exec backend alembic upgrade head

# Copier les fichiers
cp query_cache.py cache_document_map.py cache_statistics.py backend/app/models/
cp cache.py backend/app/schemas/
cp retriever.py reranker.py backend/app/rag/
cp cache_service.py backend/app/services/

# Restart services
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