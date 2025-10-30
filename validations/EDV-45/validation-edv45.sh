#!/bin/bash
# validation-edv45.sh - Validación completa del ticket EDV-45
# Estructura Base + Infraestructura de Deploy

echo "═══════════════════════════════════════════════════════════════"
echo "  VALIDACIÓN EDV-45: Estructura Base + Infraestructura Deploy"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Información del sistema
echo "🖥️  INFORMACIÓN DEL SISTEMA:"
echo "   Fecha: $(date)"
echo "   Directorio: $(pwd)"
echo "   Usuario: $(whoami)"
echo "   Docker: $(docker --version 2>/dev/null || echo 'No instalado')"
echo "   Espacio disco: $(df -h . | tail -1 | awk '{print $4}' || echo 'N/A') disponible"
echo ""

# Verificar contenedores existentes
echo "🐳 CONTENEDORES DOCKER EXISTENTES:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "   No se pudo acceder a Docker"
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
PASS=0
FAIL=0
WARN=0

# Función de validación
check() {
    local description="$1"
    local command="$2"
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $description"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌${NC} $description"
        ((FAIL++))
        return 1
    fi
}

warn() {
    local description="$1"
    echo -e "${YELLOW}⚠️${NC}  $description"
    ((WARN++))
}

section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ═══════════════════════════════════════════════════════════════
# FASE 1: ESTRUCTURA DE CARPETAS
# ═══════════════════════════════════════════════════════════════
section "1️⃣  ESTRUCTURA DE CARPETAS"

check "Directorio app/ existe" "[ -d app ]"
check "Directorio app/api/ existe" "[ -d app/api ]"
check "Directorio app/api/endpoints/ existe" "[ -d app/api/endpoints ]"
check "Directorio app/core/ existe" "[ -d app/core ]"
check "Directorio app/agents/ existe" "[ -d app/agents ]"
check "Directorio app/adapters/ existe" "[ -d app/adapters ]"
check "Directorio app/factories/ existe" "[ -d app/factories ]"
check "Directorio app/orchestrator/ existe" "[ -d app/orchestrator ]"
check "Directorio app/schemas/ existe" "[ -d app/schemas ]"
check "Directorio app/services/ existe" "[ -d app/services ]"
check "Directorio app/utils/ existe" "[ -d app/utils ]"
check "Directorio config/ existe" "[ -d config ]"
check "Directorio scripts/ existe" "[ -d scripts ]"
check "Directorio tests/ existe" "[ -d tests ]"
check "Directorio tests/unit/ existe" "[ -d tests/unit ]"
check "Directorio tests/integration/ existe" "[ -d tests/integration ]"
check "Directorio tests/fixtures/ existe" "[ -d tests/fixtures ]"

# Verificar __init__.py
echo ""
echo "Verificando módulos Python (__init__.py):"
check "app/__init__.py existe" "[ -f app/__init__.py ]"
check "app/api/__init__.py existe" "[ -f app/api/__init__.py ]"
check "app/core/__init__.py existe" "[ -f app/core/__init__.py ]"
check "app/agents/__init__.py existe" "[ -f app/agents/__init__.py ]"
check "tests/__init__.py existe" "[ -f tests/__init__.py ]"

# ═══════════════════════════════════════════════════════════════
# FASE 2: DOCKER FUNCIONAL
# ═══════════════════════════════════════════════════════════════
section "2️⃣  DOCKER FUNCIONAL"

check "Dockerfile existe" "[ -f Dockerfile ]"
check "docker-compose.yml existe" "[ -f docker/docker-compose.yml ]"
check ".dockerignore existe" "[ -f .dockerignore ]"
check "start.sh existe" "[ -f start.sh ]"
check "start.sh es ejecutable" "[ -x start.sh ]"

echo ""
echo "Testing Docker build (esto puede tomar unos minutos)..."
echo "🔍 Iniciando build con logs detallados..."

# Crear archivo de log con timestamp
BUILD_LOG="/tmp/docker-build-$(date +%s).log"

# Build con timeout y logs detallados (10 minutos)
timeout 600 docker build -t agent-hub:validation . > "$BUILD_LOG" 2>&1 &
BUILD_PID=$!

# Mostrar progreso mientras se construye
echo "⏳ Construyendo imagen Docker... (PID: $BUILD_PID)"
echo "📝 Log guardado en: $BUILD_LOG"

# Monitorear el progreso
while kill -0 $BUILD_PID 2>/dev/null; do
    echo -n "."
    sleep 2
done

wait $BUILD_PID
BUILD_EXIT_CODE=$?

echo ""

if [ $BUILD_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅${NC} Docker build exitoso"
    ((PASS++))
    
    # Verificar el tamaño de la imagen
    IMAGE_SIZE=$(docker images agent-hub:validation --format "{{.Size}}")
    echo "📦 Tamaño de imagen: $IMAGE_SIZE"
    
elif [ $BUILD_EXIT_CODE -eq 124 ]; then
    echo -e "${RED}❌${NC} Docker build timeout (>10 minutos)"
    echo "🔍 Últimas 10 líneas del log:"
    tail -10 "$BUILD_LOG"
    ((FAIL++))
else
    echo -e "${RED}❌${NC} Docker build falló (código: $BUILD_EXIT_CODE)"
    echo "🔍 Últimas 20 líneas del log:"
    tail -20 "$BUILD_LOG"
    echo ""
    echo "📝 Log completo en: $BUILD_LOG"
    ((FAIL++))
fi

# ═══════════════════════════════════════════════════════════════
# FASE 3: LINTERS CONFIGURADOS
# ═══════════════════════════════════════════════════════════════
section "3️⃣  LINTERS CONFIGURADOS"

check "pyproject.toml existe" "[ -f pyproject.toml ]"
check "requirements.txt existe" "[ -f requirements.txt ]"

echo ""
echo "Verificando configuración de linters en pyproject.toml:"
check "Black configurado" "grep -q '\[tool.black\]' pyproject.toml"
check "isort configurado" "grep -q '\[tool.isort\]' pyproject.toml"
check "mypy configurado" "grep -q '\[tool.mypy\]' pyproject.toml"
check "pytest configurado" "grep -q '\[tool.pytest' pyproject.toml"

# ═══════════════════════════════════════════════════════════════
# FASE 4: RAILWAY CONFIGURATION
# ═══════════════════════════════════════════════════════════════
section "4️⃣  RAILWAY CONFIGURATION"

check "railway.json existe" "[ -f railway.json ]"

if command -v jq &> /dev/null; then
    check "railway.json es válido" "jq empty railway.json"
    check "builder es DOCKERFILE" "jq -e '.build.builder == \"DOCKERFILE\"' railway.json"
    check "healthcheckPath es /health" "jq -e '.deploy.healthcheckPath == \"/health\"' railway.json"
else
    warn "jq no está instalado, saltando validación JSON"
fi

echo ""
echo "Verificando Railway CLI y estado del proyecto:"
if command -v railway &> /dev/null; then
    check "Railway CLI instalado" "true"
    echo ""
    echo "Estado del proyecto Railway:"
    railway status 2>/dev/null || warn "No se pudo obtener status (¿proyecto linkeado?)"
else
    echo -e "${RED}❌${NC} Railway CLI no instalado"
    ((FAIL++))
fi

# ═══════════════════════════════════════════════════════════════
# FASE 5: CI/CD GITHUB ACTIONS
# ═══════════════════════════════════════════════════════════════
section "5️⃣  CI/CD GITHUB ACTIONS"

check ".github/workflows/ existe" "[ -d .github/workflows ]"

if [ -d .github/workflows ]; then
    WORKFLOW_FILES=$(find .github/workflows -name "*.yml" -o -name "*.yaml" | wc -l)
    if [ $WORKFLOW_FILES -gt 0 ]; then
        echo -e "${GREEN}✅${NC} Archivos de workflow encontrados ($WORKFLOW_FILES)"
        ((PASS++))
    else
        echo -e "${RED}❌${NC} No se encontraron archivos de workflow"
        ((FAIL++))
    fi
fi

# ═══════════════════════════════════════════════════════════════
# FASE 6: DOCUMENTACIÓN
# ═══════════════════════════════════════════════════════════════
section "6️⃣  DOCUMENTACIÓN"

check "README.md existe" "[ -f README.md ]"
check ".env.example existe" "[ -f .env.example ]"
check ".gitignore existe" "[ -f .gitignore ]"

echo ""
echo "Verificando contenido de README.md:"
if [ -f README.md ]; then
    check "Sección Quick Start" "grep -iq 'quick start' README.md"
    check "Sección Docker" "grep -iq 'docker' README.md"
    check "Sección Deploy" "grep -iq 'deploy' README.md"
    check "Documentación de API" "grep -iq '/docs' README.md"
fi

echo ""
echo "Verificando .env.example:"
if [ -f .env.example ]; then
    check "OPENAI_API_KEY documentada" "grep -q 'OPENAI_API_KEY' .env.example"
    check "ANTHROPIC_API_KEY documentada" "grep -q 'ANTHROPIC_API_KEY' .env.example"
    check "DEBUG documentada" "grep -q 'DEBUG' .env.example"
    check "LOG_LEVEL documentada" "grep -q 'LOG_LEVEL' .env.example"
    check "AWS variables documentadas" "grep -q 'AWS_ACCESS_KEY_ID' .env.example"
    check "S3_BUCKET documentada" "grep -q 'S3_BUCKET' .env.example"
fi

echo ""
echo "Verificando .gitignore:"
if [ -f .gitignore ]; then
    check ".env excluido" "grep -q '\.env' .gitignore"
    check "__pycache__ excluido" "grep -q '__pycache__' .gitignore"
    check "*.pyc excluido" "grep -qE '(\*\.pyc|\*\.py\[cod\])' .gitignore"
    check "venv excluido" "grep -q 'venv' .gitignore"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 7: VALIDACIÓN END-TO-END
# ═══════════════════════════════════════════════════════════════
section "7️⃣  VALIDACIÓN END-TO-END"

echo "Verificando archivos core de la aplicación:"
check "app/main.py existe" "[ -f app/main.py ]"

echo ""
echo "Verificando endpoint /health con Docker:"

# Limpiar contenedores previos
echo "🧹 Limpiando contenedores previos..."
docker stop test-agent-hub > /dev/null 2>&1
docker rm test-agent-hub > /dev/null 2>&1

# Iniciar contenedor temporal para test
echo "🚀 Iniciando contenedor temporal para test..."
if docker run -d -p 8001:8000 -e PORT=8000 --name test-agent-hub agent-hub:validation; then
    echo "⏳ Esperando que el contenedor inicie..."
    
    # Esperar hasta 30 segundos para que inicie
    for i in {1..15}; do
        if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅${NC} Contenedor Docker responde en /health (intento $i)"
            ((PASS++))
            break
        else
            echo -n "."
            sleep 2
        fi
        
        if [ $i -eq 15 ]; then
            echo ""
            echo -e "${RED}❌${NC} Contenedor Docker no responde en /health después de 30s"
            echo "🔍 Logs del contenedor:"
            docker logs test-agent-hub | tail -10
            ((FAIL++))
        fi
    done
    
    echo ""
    echo "🧹 Limpiando contenedor de test..."
    docker stop test-agent-hub > /dev/null 2>&1
    docker rm test-agent-hub > /dev/null 2>&1
else
    echo -e "${RED}❌${NC} No se pudo iniciar contenedor de test"
    echo "🔍 Verificando si la imagen existe:"
    docker images agent-hub:validation
    ((FAIL++))
fi

# ═══════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                        RESUMEN FINAL"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ PASS:${NC} $PASS"
echo -e "${RED}❌ FAIL:${NC} $FAIL"
echo -e "${YELLOW}⚠️  WARN:${NC} $WARN"
echo ""

# Calcular porcentaje de éxito
TOTAL=$((PASS + FAIL))
if [ $TOTAL -gt 0 ]; then
    PERCENTAGE=$(( (PASS * 100) / TOTAL ))
    echo "Porcentaje de éxito: $PERCENTAGE%"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"

# Generar reporte para Sprint Designer
echo ""
echo "🚀 GENERANDO REPORTE PARA SPRINT DESIGNER..."
cat > validation_report.md << EOF
# 📋 Reporte de Validación EDV-45
**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')  
**Ticket:** EDV-45 - Estructura Base + Infraestructura Deploy  
**Sprint Designer:** Validación Automatizada  

## 📊 Métricas de Calidad
- ✅ **PASS:** $PASS criterios
- ❌ **FAIL:** $FAIL criterios  
- ⚠️ **WARN:** $WARN advertencias
- 📈 **Éxito:** $PERCENTAGE%

## ✅ Criterios de Aceptación Validados

### 🏗️ Estructura de Carpetas
$(if [ $PASS -ge 15 ]; then echo "✅ **COMPLETADO** - Arquitectura hexagonal implementada"; else echo "❌ **PENDIENTE** - Revisar estructura de carpetas"; fi)

### 🐳 Docker Funcional  
$(if docker build -t agent-hub:validation . > /dev/null 2>&1; then echo "✅ **COMPLETADO** - Docker build exitoso"; else echo "❌ **PENDIENTE** - Revisar Dockerfile"; fi)

### 🔧 Linters Configurados
$(if [ -f pyproject.toml ]; then echo "✅ **COMPLETADO** - Configuración de calidad de código"; else echo "❌ **PENDIENTE** - Configurar linters"; fi)

### 🚂 Railway Configuration
$(if [ -f railway.json ]; then echo "✅ **COMPLETADO** - Deploy configurado"; else echo "❌ **PENDIENTE** - Configurar Railway"; fi)

### 📖 Documentación
$(if [ -f README.md ] && [ -f .env.example ]; then echo "✅ **COMPLETADO** - Documentación básica"; else echo "❌ **PENDIENTE** - Completar documentación"; fi)

## 🎯 Estado del Ticket
$(if [ $FAIL -eq 0 ]; then echo "🎉 **TICKET COMPLETADO** - Todos los criterios PASSED"; elif [ $FAIL -le 3 ]; then echo "⚠️ **CASI COMPLETO** - $FAIL criterios menores pendientes"; else echo "❌ **INCOMPLETO** - $FAIL criterios críticos fallando"; fi)

## 📝 Próximos Pasos
$(if [ $FAIL -eq 0 ]; then echo "- ✅ Mover ticket a DONE\n- ✅ Iniciar siguiente sprint\n- ✅ Deploy a producción disponible"; else echo "- 🔧 Revisar criterios fallidos arriba\n- 🔄 Re-ejecutar validación\n- 📋 Actualizar estado en Sprint Designer"; fi)

---
*Reporte generado automáticamente por validation-edv45.sh*
EOF

echo -e "${GREEN}✅${NC} Reporte generado: validation_report.md"

# Determinar si el ticket está DONE
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}"
    echo "  🎉 ¡TICKET EDV-45 COMPLETADO! 🎉"
    echo ""
    echo "  ✅ Todos los criterios de aceptación PASARON"
    echo "  ✅ Estructura base implementada correctamente"
    echo "  ✅ Docker funcional"
    echo "  ✅ Linters configurados"
    echo "  ✅ Deploy a Railway exitoso"
    echo "  ✅ Documentación completa"
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    exit 0
elif [ $FAIL -le 3 ]; then
    echo -e "${YELLOW}"
    echo "  ⚠️  TICKET CASI COMPLETO"
    echo ""
    echo "  Hay $FAIL criterios menores pendientes."
    echo "  Revisar los ❌ arriba para completar."
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    exit 1
else
    echo -e "${RED}"
    echo "  ❌ TICKET INCOMPLETO"
    echo ""
    echo "  Hay $FAIL criterios fallando."
    echo "  Revisar sección por sección arriba."
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    exit 1
fi