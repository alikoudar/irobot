#!/bin/bash

# Script de lancement des tests - Sprint 2
# IroBot - BEAC

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║          TESTS SPRINT 2 - Auth & Users                    ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    echo "Usage: ./run_tests_sprint2.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -a, --all          Lancer tous les tests"
    echo "  -auth              Lancer tests d'authentification uniquement"
    echo "  -users             Lancer tests de gestion utilisateurs uniquement"
    echo "  -c, --coverage     Générer rapport de coverage"
    echo "  -v, --verbose      Mode verbose"
    echo "  -h, --help         Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  ./run_tests_sprint2.sh -a              # Tous les tests"
    echo "  ./run_tests_sprint2.sh -auth -v        # Tests auth en mode verbose"
    echo "  ./run_tests_sprint2.sh -c              # Tous les tests avec coverage"
}

# Options par défaut
RUN_ALL=false
RUN_AUTH=false
RUN_USERS=false
COVERAGE=false
VERBOSE=""

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            RUN_ALL=true
            shift
            ;;
        -auth)
            RUN_AUTH=true
            shift
            ;;
        -users)
            RUN_USERS=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Option inconnue: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Si aucune option, afficher l'aide
if [ "$RUN_ALL" = false ] && [ "$RUN_AUTH" = false ] && [ "$RUN_USERS" = false ]; then
    show_help
    exit 0
fi

# Vérifier que le container backend est en cours d'exécution
if ! docker-compose ps backend | grep -q "Up"; then
    echo -e "${RED}❌ Le container backend n'est pas en cours d'exécution${NC}"
    echo "Lancez d'abord: docker-compose up -d backend"
    exit 1
fi

echo -e "${GREEN}✅ Container backend actif${NC}"
echo ""

# Commande de base
CMD="docker-compose exec backend pytest"

# Tests d'authentification
if [ "$RUN_AUTH" = true ] || [ "$RUN_ALL" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}🔐 Tests d'authentification${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [ "$COVERAGE" = true ]; then
        $CMD tests/test_auth.py $VERBOSE --cov=app --cov-report=term-missing
    else
        $CMD tests/test_auth.py $VERBOSE
    fi
    
    AUTH_EXIT=$?
    echo ""
fi

# Tests de gestion utilisateurs
if [ "$RUN_USERS" = true ] || [ "$RUN_ALL" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}👥 Tests de gestion utilisateurs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [ "$COVERAGE" = true ]; then
        $CMD tests/test_users.py $VERBOSE --cov=app --cov-report=term-missing
    else
        $CMD tests/test_users.py $VERBOSE
    fi
    
    USERS_EXIT=$?
    echo ""
fi

# Tests complets (si --all ou --coverage)
if [ "$RUN_ALL" = true ] && [ "$COVERAGE" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}📊 Génération du rapport de coverage complet${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    $CMD tests/test_auth.py tests/test_users.py $VERBOSE \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html
    
    COVERAGE_EXIT=$?
    
    if [ $COVERAGE_EXIT -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Rapport HTML généré dans backend/htmlcov/index.html${NC}"
    fi
fi

# Résumé
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                        RÉSUMÉ                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ "$RUN_AUTH" = true ] || [ "$RUN_ALL" = true ]; then
    if [ $AUTH_EXIT -eq 0 ]; then
        echo -e "${GREEN}✅ Tests d'authentification : SUCCÈS${NC}"
    else
        echo -e "${RED}❌ Tests d'authentification : ÉCHEC${NC}"
    fi
fi

if [ "$RUN_USERS" = true ] || [ "$RUN_ALL" = true ]; then
    if [ $USERS_EXIT -eq 0 ]; then
        echo -e "${GREEN}✅ Tests de gestion utilisateurs : SUCCÈS${NC}"
    else
        echo -e "${RED}❌ Tests de gestion utilisateurs : ÉCHEC${NC}"
    fi
fi

echo ""

# Exit code final
if [ "$RUN_AUTH" = true ] && [ $AUTH_EXIT -ne 0 ]; then
    exit 1
fi

if [ "$RUN_USERS" = true ] && [ $USERS_EXIT -ne 0 ]; then
    exit 1
fi

exit 0