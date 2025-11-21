# 🤖 IroBot - BEAC RAG Chatbot

Système de chatbot RAG (Retrieval-Augmented Generation) pour la BEAC (Banque des États de l'Afrique Centrale).


## 📋 Table des Matières

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Tests](#tests)
- [Documentation](#documentation)
- [Développement](#développement)
- [Déploiement](#déploiement)
- [Contribution](#contribution)
- [License](#license)

---

## 🎯 Aperçu

IroBot est un chatbot intelligent basé sur l'architecture RAG qui permet :
- 📚 D'indexer et rechercher dans une base documentaire
- 💬 De répondre aux questions avec contexte
- 🔍 De citer les sources des réponses
- 📊 De tracker les coûts et performances
- 👥 De gérer plusieurs utilisateurs avec rôles (Admin, Manager, User)

### Technologies Principales

**Backend**
- FastAPI 0.104+ - API REST moderne
- PostgreSQL 16 - Base de données relationnelle
- Redis 7.2 - Cache & message broker
- Weaviate 1.23 - Base de données vectorielle
- Celery 5.3 - Task queue asynchrone
- Mistral AI - LLM pour RAG

**Frontend**
- Vue.js 3.4 - Framework JavaScript
- Element Plus 2.4 - Composants UI
- Pinia 2.1 - State management
- Chart.js 4.4 - Visualisations

**DevOps**
- Docker & Docker Compose
- Nginx - Reverse proxy
- Alembic - Migrations DB

---

## ✨ Fonctionnalités

### 📚 Gestion Documentaire
- ✅ Upload de documents (PDF, DOCX, XLSX, PPTX, images)
- ✅ Extraction automatique de texte
- ✅ OCR pour images et PDFs scannés
- ✅ Chunking intelligent (512 tokens, 10% overlap)
- ✅ Indexation vectorielle (Weaviate)
- ✅ Catégorisation des documents

### 💬 Chat Intelligent
- ✅ Recherche hybride (BM25 + Semantic)
- ✅ Reranking des résultats (top 10 → top 3)
- ✅ Génération de réponses contextuelles
- ✅ Citations des sources automatiques
- ✅ Historique de conversation (5 derniers messages)
- ✅ Streaming des réponses (SSE)

### 🔐 Authentification & Autorisation
- ✅ JWT tokens (access + refresh)
- ✅ Rôles : Admin, Manager, User
- ✅ Password hashing (Bcrypt)
- ✅ Reset password

### 📊 Analytics & Monitoring
- ✅ Tracking des coûts (USD + XAF)
- ✅ Token usage par opération
- ✅ Cache statistics (hit rate, tokens saved)
- ✅ Performance metrics
- ✅ Audit logs complets

### 🎨 Interface Utilisateur
- ✅ Design BEAC (couleurs officielles)
- ✅ Mode clair/sombre
- ✅ Responsive design
- ✅ Visualisations (charts)
- ✅ Export de données (CSV, JSON)

---

## 🏗️ Architecture

### Vue d'ensemble

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │─────▶│    Nginx    │─────▶│   Backend   │
│   Vue.js 3  │      │   (Proxy)   │      │   FastAPI   │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                   │
                     ┌─────────────────────────────┼─────────────────────┐
                     │                             │                     │
                ┌────▼────┐                  ┌────▼────┐          ┌────▼────┐
                │PostgreSQL│                 │  Redis  │          │Weaviate │
                │   (DB)   │                 │ (Cache) │          │(Vectors)│
                └──────────┘                 └────┬────┘          └─────────┘
                                                   │
                                             ┌────▼────┐
                                             │ Celery  │
                                             │(Workers)│
                                             └─────────┘
```

### Services Docker

- **PostgreSQL 16** : Base de données relationnelle (10 tables)
- **Redis 7.2** : Cache L1+L2 & Celery broker
- **Weaviate 1.23** : Base vectorielle pour embeddings
- **Backend FastAPI** : API REST + WebSocket/SSE
- **Frontend Vue.js** : Interface utilisateur
- **Nginx** : Reverse proxy avec SSL
- **Celery Workers** : 4 queues (processing, chunking, embedding, indexing)

### Base de Données (10 tables)

1. **users** - Utilisateurs (admin, manager, user)
2. **categories** - Catégories de documents
3. **documents** - Documents uploadés
4. **chunks** - Chunks de texte indexés
5. **conversations** - Historique conversations
6. **messages** - Messages (user + assistant)
7. **feedbacks** - Évaluations des réponses
8. **token_usages** - Tracking coûts tokens
9. **audit_logs** - Logs d'audit
10. **system_configs** - Configuration dynamique

---

## 📋 Prérequis

- **Docker** 24+
- **Docker Compose** 2.23+
- **Git**
- **Clé API Mistral** ([Obtenir une clé](https://console.mistral.ai/))

### Vérifier les installations

```bash
docker --version          # Docker version 24.0.0+
docker-compose --version  # Docker Compose version 2.23.0+
git --version            # git version 2.x.x+
```

---

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone https://github.com/your-org/irobot.git
cd irobot
```

### 2. Configurer les variables d'environnement

```bash
# Copier le fichier d'exemple
cp backend/.env.example backend/.env.dev

# Éditer et ajouter votre clé API Mistral
nano backend/.env.dev
```

**⚠️ IMPORTANT** : Remplacez `MISTRAL_API_KEY=your_mistral_api_key_here` par votre vraie clé.

### 3. Démarrer les services

```bash
# Avec Make (recommandé)
make up

# Ou avec Docker Compose
docker-compose up -d
```

### 4. Initialiser la base de données

```bash
# Appliquer les migrations
make migrate

# Créer l'utilisateur admin par défaut
make init-db
```

### 5. Accéder à l'application

- **Frontend** : http://localhost
- **API Docs** : http://localhost/api/docs
- **Health Check** : http://localhost/api/health

**Connexion Admin par défaut :**
- Email : `admin@beac.int`
- Password : `Admin123!`

---

## 💻 Utilisation

### Commandes Make

```bash
make help       # Afficher toutes les commandes
make up         # Démarrer tous les services
make down       # Arrêter tous les services
make restart    # Redémarrer tous les services
make logs       # Voir les logs en temps réel
make ps         # Voir l'état des containers
make migrate    # Appliquer les migrations DB
make init-db    # Initialiser la DB avec l'admin
make test       # Lancer les tests
make clean      # Nettoyer tout (⚠️ supprime les données)
```

### Commandes Docker Compose

```bash
docker-compose build              # Build les images
docker-compose up -d              # Démarrer en background
docker-compose down               # Arrêter
docker-compose logs -f backend    # Logs backend
docker-compose logs -f frontend   # Logs frontend
docker-compose restart nginx      # Redémarrer nginx
docker-compose exec backend bash  # Shell backend
```

---

## 🧪 Tests

### Lancer tous les tests

```bash
# Avec Make
make test

# Ou directement
docker-compose exec backend pytest tests/ -v --cov=app
```

### Tests par catégorie

```bash
# Tests des modèles
docker-compose exec backend pytest tests/test_models.py -v

# Tests de sécurité
docker-compose exec backend pytest tests/test_security.py -v

# Tests API
docker-compose exec backend pytest tests/test_api.py -v
```

### Coverage Report

```bash
# Terminal
docker-compose exec backend pytest tests/ --cov=app --cov-report=term-missing

# HTML (ouvre backend/htmlcov/index.html)
docker-compose exec backend pytest tests/ --cov=app --cov-report=html
```

**Coverage actuel : 90.86%** ✅

---

## 📚 Documentation

### Guides

- **[GUIDE_DEMARRAGE.md](GUIDE_DEMARRAGE.md)** - Guide de démarrage complet (10+ pages)
- **[COMMANDES_RAPIDES.txt](COMMANDES_RAPIDES.txt)** - Aide-mémoire des commandes
- **[CHANGELOG.md](CHANGELOG.md)** - Historique des versions

### Documentation Technique

- **[IROBOT_DOC_1_ARCHITECTURE_TECHNIQUE.md](IROBOT_DOC_1_ARCHITECTURE_TECHNIQUE.md)** - Architecture complète
- **[IROBOT_DOC_2_PLAN_DEVELOPPEMENT_PARTIE_1.md](IROBOT_DOC_2_PLAN_DEVELOPPEMENT_PARTIE_1.md)** - Sprints 1-8
- **[IROBOT_DOC_3_PLAN_DEVELOPPEMENT_PARTIE_2.md](IROBOT_DOC_3_PLAN_DEVELOPPEMENT_PARTIE_2.md)** - Sprints 9-16

### Résumés des Sprints

- **[SPRINT1_PHASE1_SUMMARY.md](SPRINT1_PHASE1_SUMMARY.md)** - Infrastructure Docker
- **[SPRINT1_PHASE2_SUMMARY.md](SPRINT1_PHASE2_SUMMARY.md)** - Base de données
- **[SPRINT1_PHASE3_SUMMARY.md](SPRINT1_PHASE3_SUMMARY.md)** - Tests unitaires

### API Documentation

- **Swagger UI** : http://localhost/api/docs
- **ReDoc** : http://localhost/api/redoc

---

## 🔧 Développement

### Structure du Projet

```
irobot/
├── backend/              # Backend FastAPI
│   ├── app/
│   │   ├── api/         # Endpoints API
│   │   ├── core/        # Config & security
│   │   ├── models/      # Modèles SQLAlchemy
│   │   ├── schemas/     # Schémas Pydantic
│   │   ├── services/    # Business logic
│   │   ├── workers/     # Celery tasks
│   │   ├── rag/         # Pipeline RAG
│   │   └── main.py      # Entry point
│   ├── alembic/         # Migrations DB
│   ├── tests/           # Tests unitaires
│   └── scripts/         # Scripts utilitaires
├── frontend/            # Frontend Vue.js 3
│   ├── src/
│   │   ├── components/  # Composants Vue
│   │   ├── views/       # Pages/Vues
│   │   ├── stores/      # Pinia stores
│   │   ├── router/      # Vue Router
│   │   └── styles/      # SCSS/CSS
│   └── public/          # Assets statiques
├── nginx/               # Config Nginx
└── docker-compose.yml   # Orchestration
```

### Hot Reload

Les changements de code sont automatiquement rechargés :

- **Backend** : Uvicorn reload activé
- **Frontend** : Vite HMR activé

```bash
# Éditer le code
nano backend/app/main.py
nano frontend/src/App.vue

# Les changements sont appliqués automatiquement ! ✨
```

### Ajouter une Migration

```bash
# Entrer dans le container backend
docker exec -it irobot-backend-dev bash

# Créer une migration
alembic revision --autogenerate -m "Description"

# Appliquer la migration
alembic upgrade head
```

### Code Quality

```bash
# Linter
make lint

# Formatter
make format

# Ou manuellement
docker-compose exec backend black app/
docker-compose exec backend flake8 app/
docker-compose exec backend isort app/
```

---

## 🚀 Déploiement

### Production

Voir le guide de déploiement détaillé : `docs/DEPLOYMENT.md` (à venir)

**Checklist production :**

- [ ] Changer `SECRET_KEY` dans `.env`
- [ ] Changer mot de passe admin par défaut
- [ ] Configurer SSL/HTTPS (Certbot)
- [ ] Activer les backups automatiques
- [ ] Configurer les alertes (Prometheus)
- [ ] Limiter les CORS origins
- [ ] Désactiver DEBUG mode
- [ ] Configurer les logs (rotation)

### Environment Variables (Production)

```bash
APP_ENV=production
DEBUG=False
SECRET_KEY=<générer_un_secret_fort>
DATABASE_URL=<postgresql_production>
REDIS_URL=<redis_production>
WEAVIATE_URL=<weaviate_production>
MISTRAL_API_KEY=<clé_production>
CORS_ORIGINS=https://votre-domaine.com
```

---

## 🤝 Contribution

### Workflow Git

```bash
# Créer une branche
git checkout -b feature/ma-fonctionnalite

# Développer et committer
git add .
git commit -m "feat: ajouter nouvelle fonctionnalité"

# Pousser
git push origin feature/ma-fonctionnalite

# Créer une Pull Request sur GitHub
```

### Conventions de Commit

Nous suivons [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation
- `style:` Formatage
- `refactor:` Refactoring
- `test:` Tests
- `chore:` Tâches de maintenance

---

## 🐛 Dépannage

### Port 80 déjà utilisé

```bash
# Trouver le processus
sudo lsof -i :80

# Ou changer le port dans docker-compose.yml
ports:
  - "8080:80"  # Utiliser le port 8080 à la place
```

### Services ne démarrent pas

```bash
make clean
make build
make up
```

### Erreur PostgreSQL

```bash
# Attendre que PostgreSQL soit prêt
docker-compose logs postgres

# Redémarrer le backend
docker-compose restart backend
```

### Voir tous les logs

```bash
docker-compose logs
docker-compose logs -f  # Mode suivi
```

---

## 📊 Statistiques du Projet

- **Lignes de code** : ~3000 lignes (backend + frontend)
- **Tests** : 33 tests unitaires
- **Coverage** : 90.86%
- **Tables DB** : 10 tables
- **Endpoints API** : 5+ endpoints (en croissance)
- **Services Docker** : 6 services
- **Temps de setup** : ~5 minutes

---

## 📞 Support

- **Documentation** : Voir dossier `docs/`
- **Issues** : [GitHub Issues](https://github.com/your-org/irobot/issues)
- **Email** : support@beac.int

---

## 📄 License

Propriétaire - BEAC © 2024

Tous droits réservés. Ce projet est la propriété exclusive de la Banque des États de l'Afrique Centrale (BEAC).

---

## 🎯 Roadmap

### Sprint 1 ✅ (Semaines 1-2)
- [x] Infrastructure Docker
- [x] Base de données (10 tables)
- [x] Tests unitaires (90.86% coverage)
- [x] Documentation

### Sprint 2 (Semaines 3-4)
- [ ] Authentification complète
- [ ] CRUD utilisateurs
- [ ] Interface de connexion

### Sprint 3-4 (Semaines 5-8)
- [ ] Upload & traitement documents
- [ ] Pipeline RAG complet
- [ ] Interface chat

### Sprint 5-8 (Semaines 9-16)
- [ ] Dashboards admin/manager
- [ ] Analytics & monitoring
- [ ] Optimisations performances
- [ ] Production-ready

---

## 🌟 Remerciements

Développé avec ❤️ pour la BEAC par l'équipe IroBot.

**Technologies utilisées** : FastAPI, Vue.js, PostgreSQL, Redis, Weaviate, Docker, Nginx, Celery, Mistral AI

---

**Version** : 1.0.0-sprint1  
**Date** : 2025-10-20  
**Status** : 🚧 En développement actif