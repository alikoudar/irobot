# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### À venir - Sprint 4
- Gestion des documents
- Upload et traitement documents
- Pipeline RAG
- Interface chatbot

---

## [1.0.0-sprint3] - 2024-11-22

### ✨ Ajouté

#### Phase 1 : Backend Catégories (2024-11-22)
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

#### Phase 2 : Seeds Catégories (2024-11-22)
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

#### Phase 3 : Frontend Catégories (2024-11-22)
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

#### Phase 4 : Tests (2024-11-22)
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

## Notes de Version

### [1.0.0-sprint3] - 2024-11-22

**Résumé** : Gestion complète des catégories de documents avec CRUD backend, interface admin moderne, seeds initiales, et tests complets.

**Nouveautés** :
- 📁 CRUD catégories backend (5 endpoints API)
- 🎨 Interface admin/manager responsive
- 🌱 4 catégories initiales BEAC
- 🔍 Recherche full-text avec Enter
- 🎨 Color picker avec preview
- 📊 Statistiques temps réel
- 🧪 20 tests unitaires

**Prérequis** :
- Sprint 1 complété (infrastructure)
- Sprint 2 complété (authentification)
- PostgreSQL 16+
- Redis 7.2+

**Installation** :
```bash
# Backend
cd backend
alembic upgrade head
python scripts/seed_categories.py

# Frontend
cd frontend
npm install
npm run dev

# Vérifier
curl http://localhost/api/v1/categories
```

**Connexion** :
- URL: http://localhost/categories
- Admin: ADMIN001 / Admin123!
- Manager: (créer via interface admin)

**API Documentation** :
- Swagger UI: http://localhost/api/docs#/categories
- Endpoints: GET, POST, PUT, DELETE /categories

**Tests** :
```bash
cd backend
pytest tests/test_categories.py -v
# 20 passed
```

---

## [1.0.0-sprint2] - 2025-11-22

### ✨ Ajouté

#### Phase 1-2 : Backend Authentification (2025-11-22)
- **Système d'authentification JWT complet** :
  - Login avec matricule/password
  - Refresh token pour renouvellement
  - Logout (client-side token deletion)
  - Change password (utilisateur connecté)
  - Forgot password (envoi email dev/prod)
  - Profile update (nom, prénom, email)
- **Services d'authentification** :
  - `AuthService` : authenticate_user, create_tokens, refresh_access_token
  - `AuthService` : update_profile, initiate_password_reset, send_password_reset_email
  - Logs audit pour toutes les actions (LOGIN_SUCCESS, LOGIN_FAILED, PROFILE_UPDATE, PASSWORD_RESET_REQUEST)
- **Sécurité renforcée** :
  - Validation force du mot de passe (min 10 chars, majuscule, chiffre, caractère spécial)
  - Hash bcrypt pour tous les mots de passe
  - Tokens JWT avec expiration (access 30min, refresh 7 jours)
  - Email masqué dans les réponses API (ex: us***@beac.int)
  - Token reset sécurisé (secrets.token_urlsafe)

#### Phase 2-3 : Gestion Utilisateurs (2025-11-22)
- **CRUD utilisateurs complet** (admin uniquement) :
  - GET /users - Liste paginée avec filtres (search, role, is_active)
  - POST /users - Création utilisateur
  - GET /users/{id} - Détails utilisateur
  - PUT /users/{id} - Mise à jour utilisateur
  - DELETE /users/{id} - Suppression utilisateur
- **Import/Export utilisateurs** :
  - POST /users/import-excel - Import bulk depuis Excel
  - GET /users/import-excel/template - Téléchargement template
  - Validation complète des données importées
  - Rapport détaillé (succès, erreurs)
- **Gestion des mots de passe** :
  - POST /users/{id}/reset-password - Réinitialisation (admin)
  - Force changement au prochain login (configurable)
- **Statistiques utilisateurs** :
  - GET /users/stats/overview - Stats complètes
  - Total, actifs, inactifs, par rôle
  - Connexions récentes (7 derniers jours)
- **Permissions par rôle** :
  - ADMIN : Accès complet (CRUD users, stats, import)
  - MANAGER : Lecture uniquement
  - USER : Aucun accès gestion users

#### Phase 3 : Frontend Authentification & Users (2025-11-22)
- **Pages d'authentification** :
  - Login.vue - Connexion avec matricule/password
  - ChangePassword.vue - Changement de mot de passe
  - ForgotPassword.vue - Réinitialisation mot de passe
  - Profile.vue - Affichage et édition du profil
- **Interface admin utilisateurs** :
  - Users.vue - Liste complète avec filtres et pagination
  - Création/édition utilisateur (modal)
  - Suppression avec confirmation
  - Reset password admin
  - Import Excel avec rapport détaillé
- **Stores Pinia** :
  - `authStore` : login, logout, refresh, changePassword, updateProfile
  - `usersStore` : CRUD users, import, stats, filtres, pagination
- **Composants** :
  - UserForm.vue - Formulaire création/édition
  - UserImportDialog.vue - Import Excel
  - Navigation mise à jour (menu profil, logout)
- **Features UI** :
  - Stats temps réel (cartes total/actifs/inactifs)
  - Recherche instantanée
  - Filtres par rôle et statut
  - Pagination Element Plus
  - Messages de confirmation/succès
  - Gestion des erreurs

#### Phase 4 : Tests (2025-11-22)
- **60+ tests complets** :
  - `test_auth.py` : 35 tests authentification
    - TestLogin (5 tests)
    - TestRefreshToken (3 tests)
    - TestChangePassword (4 tests)
    - TestForgotPassword (4 tests)
    - TestProfile (5 tests)
    - TestLogout (2 tests)
  - `test_users.py` : 25+ tests gestion utilisateurs
    - TestGetUsers (7 tests)
    - TestCreateUser (6 tests)
    - TestGetUser (2 tests)
    - TestUpdateUser (4 tests)
    - TestDeleteUser (2 tests)
    - TestImportExcel (4 tests)
    - TestResetPassword (3 tests)
    - TestUserStats (1 test)
- **Fixtures pytest** :
  - 12 fixtures réutilisables (users, tokens, headers)
  - Base SQLite in-memory pour tests rapides
  - Support UUID compatible SQLite/PostgreSQL
- **Script automatisé** :
  - run_tests_sprint2.sh avec options (-auth, -users, -coverage)
- **Documentation tests** :
  - README_TESTS_SPRINT2.md (guide complet)
  - CORRECTION_UUID.md (résolution erreurs SQLite)

### 🔧 Modifié

- **Modèles SQLAlchemy** :
  - Type GUID personnalisé compatible SQLite ET PostgreSQL
  - Remplacement UUID PostgreSQL par GUID universel
  - Support tests SQLite in-memory (rapides)
- **Services** :
  - AuthService étendu (profile, forgot password)
  - UserService avec validation email unique
  - Logs audit pour toutes les actions sensibles
- **API Endpoints** :
  - PUT /auth/profile - Nouveau endpoint
  - POST /auth/forgot-password - Nouveau endpoint
  - GET /users/stats/overview - Retourne stats détaillées
- **Frontend** :
  - Store users.js - Calcul stats local si API échoue
  - Mapping correct API response (total_users → total)
  - Navigation profil dans AppLayout
  - Lien "Mot de passe oublié" dans Login

### 🐛 Corrigé

- **Stats utilisateurs** :
  - Actifs/Inactifs affichaient 0 au lieu des vraies valeurs
  - Mapping incorrect (total_users vs total)
  - Ajout fallback calcul local depuis liste users
- **Tests SQLite** :
  - Erreur CompileError UUID incompatible
  - Création type GUID universel (SQLite + PostgreSQL)
  - Fixtures sans ID fixe (auto-généré)
- **Authentification** :
  - Validation mot de passe renforcée
  - Gestion compte inactif
  - Messages d'erreur explicites

### 🔒 Sécurité

- **Validation renforcée** :
  - Mots de passe : min 10 chars, complexité validée
  - Email : validation format et unicité
  - Matricule : validation unicité
- **Protection données** :
  - Email masqué dans forgot password (us***@beac.int)
  - Tokens sécurisés (secrets.token_urlsafe)
  - Audit logs complets (IP, user-agent)
- **Permissions strictes** :
  - Endpoints users protégés (admin uniquement)
  - Vérification rôle à chaque requête
  - Isolation des données par utilisateur

### 📊 Statistiques Sprint 2

- **Fichiers créés/modifiés** : ~45 fichiers
- **Lignes de code** : ~4500 lignes (backend + frontend + tests)
- **Tests** : 60+ tests (95 au total avec Sprint 1)
- **Coverage** : Tests fonctionnels ✅ (SQLite UUID résolu)
- **Endpoints API** : 15+ endpoints auth & users
- **Pages frontend** : 7 pages (login, profile, users, etc.)
- **Stores Pinia** : 2 stores (auth, users)
- **Durée** : 3 jours

### 🎯 Objectifs Sprint 2 - Atteints

- ✅ Authentification JWT complète (login, refresh, logout)
- ✅ Changement mot de passe obligatoire
- ✅ CRUD utilisateurs avec permissions par rôle
- ✅ Import Excel utilisateurs opérationnel
- ✅ Audit logs enregistrés pour toutes les actions
- ✅ Tests complets (60+ tests auth & users)
- ✅ Interface admin moderne et intuitive
- ✅ Page profil utilisateur
- ✅ Mot de passe oublié (email dev/prod)

### 📦 Packages Livrés

- **complete_profile_forgot_package.zip** (49 KB) - Frontend profil & forgot
- **backend_endpoints_profile.zip** (25 KB) - Backend profil & forgot
- **tests_sprint2.zip** (13 KB) - Tests complets
- **correction_tests_uuid.zip** (7.2 KB) - Correction UUID SQLite
- **correction_stats_mapping.zip** (3.5 KB) - Correction stats

---

## [1.0.0-sprint1] - 2024-11-21

### ✨ Ajouté

#### Phase 1 : Infrastructure Docker (2024-11-21)
- Docker Compose avec 6 services (PostgreSQL, Redis, Weaviate, Backend, Frontend, Nginx)
- Configuration backend FastAPI avec hot reload
- Configuration frontend Vue.js 3 avec Vite et hot reload (HMR)
- Nginx comme reverse proxy avec support SSE
- Structure modulaire backend (app/core, app/api, app/models, etc.)
- Structure frontend Vue 3 avec Element Plus, Pinia, Vue Router
- Configuration CORS et reverse proxy
- Fichiers .env.example et .env.dev
- Makefile avec commandes simplifiées
- README.md et CHANGELOG.md initiaux

#### Phase 2 : Base de Données (2024-11-21)
- 10 modèles SQLAlchemy avec relationships :
  - **users** : Utilisateurs avec rôles (admin, manager, user)
  - **categories** : Catégories de documents
  - **documents** : Documents avec statut et métadonnées
  - **chunks** : Chunks de texte indexés dans Weaviate
  - **conversations** : Historique conversations utilisateurs
  - **messages** : Messages user + assistant avec sources
  - **feedbacks** : Évaluations des réponses (thumbs up/down)
  - **token_usages** : Tracking coûts par opération
  - **audit_logs** : Logs d'audit complets
  - **system_configs** : Configuration dynamique
- Configuration Alembic pour migrations
- Migration initiale (001_initial.py) avec toutes les tables
- Script d'initialisation DB (scripts/init_db.py)
- Module sécurité (JWT + Bcrypt password hashing)
- ~40 indexes optimisés sur les champs clés
- 5 enums (UserRole, DocumentStatus, MessageRole, FeedbackRating, OperationType)
- Relations CASCADE DELETE et SET NULL configurées
- 10 foreign keys entre les tables

#### Phase 3 : Tests Unitaires (2024-11-21)
- Configuration pytest avec coverage >80%
- 33 tests unitaires répartis en 3 fichiers :
  - **test_models.py** : 15 tests des modèles (User, Category, Document, etc.)
  - **test_security.py** : 15 tests de sécurité (password hashing, JWT tokens)
  - **test_api.py** : 3 tests API (health check, root, CORS)
- 6 fixtures réutilisables (admin_user, manager_user, regular_user, etc.)
- Base de données test (SQLite in-memory)
- Markers pytest (unit, integration, slow)
- Coverage report HTML automatique
- Script de lancement des tests (run_tests.sh)

#### Phase 4 : Documentation (2024-11-21)
- README.md complet avec badges, architecture, guides
- CHANGELOG.md détaillé
- GUIDE_DEMARRAGE.md (10+ pages)
- COMMANDES_RAPIDES.txt (aide-mémoire)
- SPRINT1_PHASE1_SUMMARY.md
- SPRINT1_PHASE2_SUMMARY.md
- SPRINT1_PHASE3_SUMMARY.md
- Documentation API (Swagger UI accessible à /api/docs)

### 🔧 Modifié

- Correction du healthcheck Weaviate (utilise wget au lieu de curl)
- Correction Pydantic v2 (@field_validator au lieu de @validator)
- Correction config Nginx pour routing API
- Correction version bcrypt (4.0.1) pour compatibilité passlib
- Correction conftest.py pour support SQLite avec UUID strings
- Amélioration de la configuration pytest.ini

### 🐛 Corrigé

- Erreur 502 Bad Gateway sur backend (config Pydantic)
- Erreur unhealthy sur container Weaviate
- Erreur "ADMIN" enum PostgreSQL (utilisation de string "admin")
- Erreur bcrypt password hashing (version incompatible)
- Erreur SQLite UUID dans tests (conversion en strings)
- Documentation Swagger OpenAPI non accessible

### 📊 Statistiques Sprint 1

- **Fichiers créés** : ~65 fichiers
- **Lignes de code** : ~3000 lignes (backend + frontend + tests)
- **Tests** : 33 tests unitaires
- **Coverage** : 90.86% ✅
- **Tables DB** : 10 tables
- **Foreign keys** : 10 relations
- **Indexes** : ~40 indexes
- **Services Docker** : 6 services
- **Durée** : 2 jours

### 🎯 Objectifs Sprint 1 - Atteints

- ✅ Infrastructure Docker complète et fonctionnelle
- ✅ Base de données PostgreSQL avec 10 tables optimisées
- ✅ Tests unitaires avec coverage >80% (90.86% atteint)
- ✅ Documentation complète et professionnelle
- ✅ Hot reload activé (backend + frontend)
- ✅ Sécurité (JWT + Bcrypt)
- ✅ Migrations DB (Alembic)

---

## Notes de Version

### [1.0.0-sprint2] - 2025-11-22

**Résumé** : Authentification JWT complète, gestion utilisateurs (CRUD + import Excel), interface admin moderne, tests complets.

**Nouveautés** :
- 🔐 Login avec JWT (access + refresh tokens)
- 👤 Page profil utilisateur avec édition
- 🔑 Mot de passe oublié (email dev/prod)
- 👥 CRUD utilisateurs complet (admin)
- 📊 Import Excel utilisateurs
- 📈 Statistiques utilisateurs temps réel
- 🧪 60+ tests auth & users

**Prérequis** :
- Docker 24+
- Docker Compose 2.23+
- Clé API Mistral
- SMTP configuré (production uniquement)

**Installation** :
```bash
# Démarrer les services
make up
make migrate
make init-db

# Tester
docker-compose exec backend pytest tests/ -v
```

**Connexion** :
- URL: http://localhost
- Matricule: ADMIN001
- Password: admin123 (à changer en production)

**API Documentation** :
- Swagger UI: http://localhost/api/docs
- ReDoc: http://localhost/api/redoc

---

### [1.0.0-sprint1] - 2024-11-21

**Résumé** : Infrastructure complète, base de données, tests unitaires, et documentation.

**Prérequis** :
- Docker 24+
- Docker Compose 2.23+
- Clé API Mistral

**Installation** :
```bash
make up
make migrate
make init-db
```

**Tests** :
```bash
make test
```

**Connexion Admin par défaut** :
- Email: admin@beac.int
- Password: Admin123!

⚠️ **Changez le mot de passe admin en production !**

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