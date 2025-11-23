# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### À venir - Sprint 7
- Generator LLM avec Mistral
- Streaming SSE
- Prompts système BEAC
- Pipeline RAG complet

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

### 🔄 Pipeline RAG Actuel

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
│  4. Generation (Sprint7)│
│  5. save_to_cache()     │
└─────────────────────────┘
```

### ⚠️ Limitations Actuelles

- Generator LLM non implémenté (Sprint 7)
- Streaming SSE non implémenté (Sprint 7)
- Frontend chat non développé (Sprint 8)
- Weaviate client mock dans les tests

### 🚀 Prochaines Étapes (Sprint 7)

1. **Generator LLM** :
   - MistralGenerator avec streaming
   - Prompts système BEAC
   - Context augmentation

2. **API Chat** :
   - POST /chat/message - Envoi message
   - GET /chat/stream - SSE streaming
   - Gestion conversations

3. **Token & Cost Tracking** :
   - Comptage précis tokens
   - Calcul coûts USD/XAF
   - Historique token_usage

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