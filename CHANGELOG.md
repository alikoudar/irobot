# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### À venir - Sprint 2
- Authentification complète (login, refresh, logout)
- CRUD utilisateurs (admin)
- Interface de connexion frontend
- Tests d'intégration authentication

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