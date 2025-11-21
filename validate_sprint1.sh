#!/bin/bash
# Script de validation Sprint 1

echo "🔍 VALIDATION SPRINT 1 - IROBOT"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_service() {
    local service=$1
    if docker-compose ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✅${NC} $service est UP"
        return 0
    else
        echo -e "${RED}❌${NC} $service est DOWN"
        return 1
    fi
}

check_url() {
    local url=$1
    local name=$2
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $name accessible ($url)"
        return 0
    else
        echo -e "${RED}❌${NC} $name non accessible ($url)"
        return 1
    fi
}

# Counter
passed=0
failed=0

echo "📦 1. Vérification des services Docker..."
echo "----------------------------------------"
for service in postgres redis weaviate backend frontend nginx; do
    if check_service "irobot-${service}-dev"; then
        ((passed++))
    else
        ((failed++))
    fi
done
echo ""

echo "🌐 2. Vérification des endpoints..."
echo "-----------------------------------"
if check_url "http://localhost/api/health" "Health check"; then
    ((passed++))
else
    ((failed++))
fi

if check_url "http://localhost/api/docs" "API Docs"; then
    ((passed++))
else
    ((failed++))
fi

if check_url "http://localhost" "Frontend"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "🗄️ 3. Vérification de la base de données..."
echo "-------------------------------------------"
tables_count=$(docker exec irobot-postgres-dev psql -U irobot_user -d irobot_dev -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

if [ "$tables_count" = "11" ]; then
    echo -e "${GREEN}✅${NC} 11 tables présentes dans PostgreSQL"
    ((passed++))
else
    echo -e "${RED}❌${NC} Nombre de tables incorrect: $tables_count (attendu: 11)"
    ((failed++))
fi

admin_count=$(docker exec irobot-postgres-dev psql -U irobot_user -d irobot_dev -t -c "SELECT COUNT(*) FROM users WHERE role='ADMIN';" 2>/dev/null | tr -d ' ')

if [ "$admin_count" = "1" ]; then
    echo -e "${GREEN}✅${NC} Utilisateur admin créé"
    ((passed++))
else
    echo -e "${RED}❌${NC} Utilisateur admin non trouvé"
    ((failed++))
fi
echo ""

echo "🧪 4. Lancement des tests..."
echo "---------------------------"
# Utiliser -T pour mode non-interactif
if docker-compose exec -T backend pytest tests/ -v --tb=short > /tmp/pytest_output.txt 2>&1; then
    # Extraire le nombre de tests passés
    tests_passed=$(grep "passed" /tmp/pytest_output.txt | tail -1 | grep -oP '\d+(?= passed)' || echo "")
    
    if [ -n "$tests_passed" ]; then
        echo -e "${GREEN}✅${NC} Tests passés: $tests_passed tests"
        ((passed++))
    else
        echo -e "${YELLOW}⚠️${NC} Tests OK mais impossible de compter"
        ((passed++))
    fi
    
    # Extraire le coverage
    coverage=$(grep "TOTAL" /tmp/pytest_output.txt | awk '{print $(NF-1)}' | tr -d '%' || echo "")
    
    if [ -n "$coverage" ]; then
        echo -e "${GREEN}✅${NC} Coverage: $coverage%"
        ((passed++))
    else
        echo -e "${YELLOW}⚠️${NC} Coverage non trouvé (tests OK)"
        ((passed++))
    fi
else
    echo -e "${RED}❌${NC} Échec des tests"
    echo "Dernières lignes de sortie:"
    tail -20 /tmp/pytest_output.txt
    ((failed+=2))
fi
echo ""

echo "📚 5. Vérification de la documentation..."
echo "----------------------------------------"
docs=("README.md" "CHANGELOG.md")
for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✅${NC} $doc présent"
        ((passed++))
    else
        echo -e "${RED}❌${NC} $doc manquant"
        ((failed++))
    fi
done
echo ""

echo "================================"
echo "📊 RÉSULTAT FINAL"
echo "================================"
total=$((passed + failed))
percentage=$((passed * 100 / total))

echo "Tests passés: $passed/$total ($percentage%)"

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ VALIDATION COMPLÈTE - SPRINT 1 PRÊT POUR COMMIT${NC}"
    echo ""
    echo "🎉 Prochaines étapes:"
    echo "  1. git add ."
    echo "  2. git commit -m '[Sprint 1] Infrastructure complète + DB + Tests + Documentation'"
    echo "  3. git tag v1.0.0-sprint1"
    echo "  4. git push origin main --tags"
    exit 0
else
    echo -e "${RED}❌ VALIDATION ÉCHOUÉE - $failed problème(s) détecté(s)${NC}"
    echo ""
    echo "Veuillez corriger les problèmes ci-dessus avant de committer."
    exit 1
fi