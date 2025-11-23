# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### À venir - Sprint 5
- Embedding chunks avec Mistral
- Indexing dans Weaviate (vectors + BM25)
- Token & cost tracking
- Periodic tasks (cleanup, stats)

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

### 🔄 Pipeline Document Actuel

```
Upload → PENDING
   ↓
Processing Worker → PROCESSING/EXTRACTION
   ↓
   ├── DocumentProcessor.process_document()
   ├── OCR images si nécessaire
   ├── Nettoyage caractères NULL
   └── Mise à jour: extracted_text, has_images, extraction_method
   ↓
Chunking Worker → PROCESSING/CHUNKING
   ↓
   ├── Nettoyage artefacts OCR
   ├── Découpage intelligent (1000 chars, 200 overlap)
   ├── Création chunks avec métadonnées
   └── Mise à jour: total_chunks, chunking_stats
   ↓
[En attente Sprint 5] → EMBEDDING → INDEXING → COMPLETED
```

### ⚠️ Limitations Actuelles

- Documents restent à l'étape CHUNKING (embedding non implémenté)
- weaviate_id temporaire (sera remplacé lors de l'indexing)
- Frontend gestion documents non encore développé

### 🚀 Prochaines Étapes (Sprint 5)

1. **Embedding Worker** :
   - embed_chunks() avec Mistral embed
   - Token counting précis
   - Cost tracking USD/XAF

2. **Indexing Worker** :
   - index_document() dans Weaviate
   - Batch insert optimisé
   - Mise à jour weaviate_id réel

3. **Tâches périodiques** :
   - update_exchange_rate() - Taux USD/XAF
   - cleanup_expired_cache() - Nettoyage cache
   - cleanup_old_logs() - Purge logs 90j

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
- **Migration Alembic** :
  - add_created_by_to_categories.py
  - Ajout colonne created_by (FK vers users)
  - Compatible PostgreSQL et SQLite

#### Phase 2 : Seeds Catégories (2025-11-22)
- **Script de seed** (seed_categories.py) :
  - 4 catégories initiales selon plan BEAC
  - Lettres Circulaires (#005CA9 - Bleu BEAC)
  - Décisions du Gouverneur (#C2A712 - Or BEAC)
  - Procédures et Modes Opératoires (#4A90E2 - Bleu clair)
  - Clauses et Conditions Générales (#50C878 - Vert émeraude)
  - Attribution created_by à l'admin
  - Idempotent (réexécutable sans erreur)
  - Rapport détaillé avec statistiques
- **Script de vérification** (verify_categories.py) :
  - Vérification structure table categories
  - Liste catégories avec détails complets
  - Statistiques globales (total, avec/sans documents)
  - Détection anomalies

#### Phase 3 : Frontend Catégories (2025-11-22)
- **Store Pinia categories.js** :
  - 10 actions CRUD et utilitaires
  - 4 getters computed (hasCategories, sortedCategories, categoryOptions)
  - Pagination dynamique (10, 20, 50, 100)
  - Recherche avec filtres
  - Gestion erreurs avec ElMessage
- **Composant CategoryForm.vue** :
  - Mode création/édition intelligent
  - Validation frontend complète
  - Color picker Element Plus avec preview temps réel
  - 8 couleurs BEAC prédéfinies en palette compacte
  - Tooltip au survol des couleurs
  - Responsive design
- **Vue admin/Categories.vue** :
  - Table paginée responsive avec stripe
  - Recherche full-text (Enter OU bouton)
  - 3 statistiques en temps réel (total, avec/sans docs)
  - CRUD complet via modals
  - Confirmation suppression
  - Loading states
  - Design couleurs BEAC
- **Vue manager/Categories.vue** :
  - Interface identique à admin
  - Permissions backend (même CRUD)
- **Router** :
  - 3 routes ajoutées (/categories, /admin/categories, /manager/categories)
  - Guards navigation avec requiresAuth et requiresManager
  - Correction route /categories (Categories.vue au lieu de Home.vue)
- **Icônes Element Plus** :
  - Folder, FolderOpened, Document, Plus, Search, Edit, Delete, etc.
  - Intégrées partout pour UX cohérente

#### Phase 4 : Tests (2025-11-22)
- **20 tests unitaires** (test_categories.py) :
  - TestGetCategories (5 tests)
  - TestCreateCategory (5 tests)
  - TestGetCategory (2 tests)
  - TestUpdateCategory (4 tests)
  - TestDeleteCategory (4 tests)
- **Fixtures pytest** :
  - category_data, created_category
  - Réutilisation fixtures users existantes
- **Coverage** :
  - Categories endpoints : >95%
  - Service : >90%
  - Modèle : 100%

### 🔧 Modifié

- **Modèle Category** :
  - Ajout colonne created_by (FK vers users.id)
  - Migration Alembic pour ajout colonne
  - Type UUID compatible PostgreSQL et SQLite
- **Router API** :
  - Enregistrement routes /categories dans router principal
  - Ordre routes : auth, users, **categories** (nouveau)
- **Frontend Router** :
  - Correction route /categories (pointait vers Home.vue)
  - Ajout 3 routes catégories (/, /admin, /manager)
- **AppLayout.vue** :
  - Ajout lien "Catégories" dans navigation sidebar
  - Import icône Folder
  - Position après "Documents", avant "Statistiques"

### 🛠️ Corrections UX

- **Formulaire CategoryForm compact** :
  - Palette couleurs redessinée en horizontal (au lieu de grille verticale)
  - Taille réduite : 40px × 40px (au lieu de 100px × 60px)
  - Économie hauteur : -200px (~22% de réduction)
  - Tooltip natif HTML au survol (plus léger que el-tooltip)
- **Recherche améliorée** :
  - Ajout @submit.prevent sur el-form
  - Support touche Enter ET bouton Rechercher
  - Bouton "Rechercher" en type="primary" (mise en évidence)
  - Clear (×) réinitialise et recherche automatiquement

### 🛠️ Corrigé

- **Route frontend** :
  - /categories pointait vers Home.vue au lieu de Categories.vue
  - Correction dans router/index.js
- **Erreur 404** :
  - GET /api/v1/categories retournait 404
  - Cause : Phase 1 (backend) non intégrée avant Phase 3 (frontend)
  - Solution : Ordre d'intégration corrigé (1→2→3)
- **Formulaire trop haut** :
  - Dépassait hauteur écran (palette 480px)
  - Réduit à 40px avec design horizontal
- **Warnings Vue** :
  - Icônes Element Plus rendues réactives
  - Solution documentée (markRaw optionnel)

### 📊 Statistiques Sprint 3

- **Fichiers créés/modifiés** : 18 fichiers
- **Lignes de code** : ~2450 lignes (backend + frontend + tests + seeds)
- **Tests** : 20 tests unitaires (115 au total avec Sprints 1-2)
- **Coverage** : >90% (catégories)
- **Endpoints API** : 5 endpoints catégories
- **Pages frontend** : 2 vues (admin, manager)
- **Stores Pinia** : 1 store (categories)
- **Composants** : 1 formulaire réutilisable
- **Scripts** : 2 scripts (seed, verify)
- **Catégories seed** : 4 catégories initiales BEAC
- **Documentation** : 15 fichiers (~50 pages)
- **Durée** : 1 jour

### 🎯 Objectifs Sprint 3 - Atteints

- ✅ CRUD catégories backend complet et testé
- ✅ Permissions admin/manager fonctionnelles
- ✅ Seeds catégories initiales (4 catégories BEAC)
- ✅ Interface frontend intuitive et responsive
- ✅ Store Pinia avec gestion état complète
- ✅ Formulaire avec color picker et validation
- ✅ Recherche avec Enter et pagination
- ✅ Tests unitaires (20 tests, >90% coverage)
- ✅ Migration Alembic (add_created_by)
- ✅ Documentation exhaustive (15 fichiers)
- ✅ Corrections UX (formulaire compact, recherche Enter)
- ✅ Design BEAC respecté (couleurs officielles)

### 📦 Packages Livrés

- **sprint3_phases1_2_3_complete.zip** (76 KB) - Archive complète 3 phases
- **sprint3_phase1_complete.zip** (42 KB) - Backend catégories complet
- **sprint3_phase2_seeds.zip** (13 KB) - Scripts seeds et vérification
- **sprint3_phase3_frontend.zip** (28 KB) - Frontend Vue.js complet
- **Documentation** (15 fichiers MD) - Guides, rapports, synthèses

### 🔄 Refactoring Recommandé (Optionnel)

**Éliminer duplication admin/manager** :
- Créer composant partagé `CategoriesManagement.vue`
- Convertir vues en wrappers légers (250→7 lignes)
- Respecter principe DRY
- Documentation : REFACTORING_DRY_CATEGORIES.md

**Statut** : Optionnel, peut être fait en Sprint 4

---

## [1.0.0-sprint2] - 2025-11-22

### ✨ Ajouté

#### Phase 1 : Authentification JWT (2025-11-22)
- Login avec access + refresh tokens
- Changement mot de passe obligatoire (first login)
- Logout avec invalidation token
- Refresh token automatique
- Middleware vérification JWT
- Guards Vue Router

#### Phase 2 : Gestion Utilisateurs (2025-11-22)
- CRUD utilisateurs complet (admin)
- Import Excel utilisateurs
- Activation/désactivation comptes
- Reset mot de passe (email dev/prod)
- Page profil utilisateur
- Statistiques utilisateurs

#### Phase 3 : Interface Admin (2025-11-22)
- Dashboard admin
- Table utilisateurs paginée
- Modals création/édition
- Confirmation actions critiques
- Design BEAC

### 📊 Statistiques Sprint 2

- **Fichiers créés/modifiés** : ~45 fichiers
- **Lignes de code** : ~4500 lignes
- **Tests** : 60+ tests (95 au total)
- **Endpoints API** : 15+ endpoints
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

### [1.0.0-sprint4] - 2025-11-23

**Résumé** : Pipeline extraction documents complet avec OCR Mistral, chunking intelligent, et nettoyage texte.

**Nouveautés** :
- 📄 Extraction tous formats (PDF, DOCX, XLSX, PPTX, TXT, MD, RTF)
- 🔍 OCR Mistral pour images intégrées
- ✂️ Chunking intelligent avec overlap
- 🧹 Nettoyage artefacts OCR automatique
- 📊 Métadonnées enrichies (langue, titre, OCR)
- ⚡ Pipeline asynchrone Celery

**Prérequis** :
- Sprint 1-3 complétés
- Clé API Mistral configurée
- Celery workers démarrés

**Installation** :
```bash
# Appliquer migration
docker-compose exec backend alembic upgrade head

# Copier les fichiers
cp document_processor.py backend/app/rag/
cp ocr_processor.py backend/app/rag/
cp text_cleaner.py backend/app/rag/
cp processing_tasks.py backend/app/workers/
cp chunking_tasks.py backend/app/workers/

# Restart workers
docker-compose restart celery-worker-processing celery-worker-chunking
```

**Test** :
```bash
# Upload document via API
curl -X POST "http://localhost/api/v1/documents/upload" \
  -H "Authorization: Bearer TOKEN" \
  -F "files=@document.pdf" \
  -F "category_id=UUID"

# Vérifier statut
curl "http://localhost/api/v1/documents/{id}/status" \
  -H "Authorization: Bearer TOKEN"
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

### Format des Entrées

```
## [Version] - YYYY-MM-DD

### Ajouté
- Description du changement

### Modifié
- Description de la modification

### Corrigé
- Description du bug corrigé
```

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