# Backend Integration Tests

Tests de integración end-to-end entre el Python Hub y el Rails Backend.

## 🎯 Objetivo

Validar que la clasificación de residuos se guarda correctamente en la base de datos Rails, incluyendo:

- Datos de clasificación (material, confianza, subtipo)
- Propiedades físicas (volumen, peso)
- Metadata (station_id, tenant_id, timestamps)
- Validaciones del backend (rechaza datos inválidos)

## 📋 Prerequisites

1. **Rails Backend corriendo**:
   ```bash
   cd /path/to/rails/backend
   rails s  # Inicia en localhost:3000
   ```

2. **Variables de entorno configuradas**:
   ```bash
   export BACKEND_API_URL="http://localhost:3000/api/v1"
   export BACKEND_SERVICE_TOKEN="your-test-token"  # Opcional
   export BACKEND_ORGANIZATION_ID="test-org-id"    # Opcional
   ```

3. **Base de datos de test seeded**:
   ```bash
   cd /path/to/rails/backend
   rails db:test:prepare
   rails db:seed
   ```

## 🚀 Ejecución

### Opción 1: Script automatizado (RECOMENDADO)

```bash
# Desde environmental-agent-hub/
./scripts/test_backend_integration.sh
```

Este script:
- ✅ Verifica que Rails esté corriendo
- ✅ Muestra configuración actual
- ✅ Ejecuta todos los tests de integración
- ✅ Reporta resultados detallados

### Opción 2: pytest directo

```bash
# Tests específicos
pytest tests/integration/test_backend_integration.py -v --backend

# Solo health check
pytest tests/integration/test_backend_integration.py::test_backend_health_check -v --backend

# Solo test de guardado
pytest tests/integration/test_backend_integration.py::test_pipeline_saves_classification_to_rails -v --backend
```

## 📊 Tests Incluidos

### 1. `test_pipeline_saves_classification_to_rails`

**Objetivo**: Validar que una clasificación completa se guarde en Rails.

**Flujo**:
1. Ejecuta pipeline con mock classifier
2. Verifica respuesta correcta
3. Query Rails API para verificar guardado
4. Valida campos: material, confidence, subtype, station_id

**Importancia**: Este es el test MÁS CRÍTICO para tu tesis.

### 2. `test_backend_rejects_invalid_data`

**Objetivo**: Validar que Rails rechace datos inválidos.

**Casos**:
- Volumen negativo
- Material inválido
- Campos faltantes

**Importancia**: Demuestra que el backend valida correctness.

### 3. `test_backend_health_check`

**Objetivo**: Verificar conectividad básica con Rails.

**Importancia**: Pre-check rápido antes de ejecutar tests complejos.

## 🔧 Troubleshooting

### Error: "Rails backend not accessible"

**Causa**: Rails no está corriendo en localhost:3000.

**Solución**:
```bash
cd /path/to/rails/backend
rails s
```

### Error: "Connection refused"

**Causa**: Puerto incorrecto o Rails en diferente puerto.

**Solución**: Actualiza BACKEND_API_URL:
```bash
export BACKEND_API_URL="http://localhost:3000/api/v1"  # Si Rails está en 3000
```

### Error: "404 Not Found on /api/v1/scans"

**Causa**: Ruta del endpoint incorrecta.

**Solución**: Verifica las rutas de Rails:
```bash
cd /path/to/rails/backend
rails routes | grep scans
```

Actualiza el test con la ruta correcta.

### Error: "Timeout connecting to Rails"

**Causa**: Rails está lento o procesando mucho.

**Solución**: Aumenta el timeout en el test:
```python
async with httpx.AsyncClient(timeout=10.0) as client:  # De 5.0 a 10.0
```

## 🎓 Para tu Tesis

### Captura de pantalla recomendada

```bash
# Ejecuta y captura output completo
./scripts/test_backend_integration.sh > backend_integration_results.txt

# Incluye en tesis:
# - Screenshot del output verde (tests passing)
# - Logs de Rails mostrando INSERT INTO scans
# - Query manual mostrando datos guardados
```

### Métricas para reportar

1. **End-to-end latency**: Pipeline + Backend save
2. **Data integrity**: Todos los campos se guardan correctamente
3. **Validation coverage**: Backend rechaza datos inválidos
4. **Reliability**: Tests pasan consistentemente

### Narrativa para tesis

> "Implementé tests de integración end-to-end que validan la comunicación
> entre el Hub Python y el Backend Rails. Los tests verifican que:
>
> 1. Clasificaciones se guardan correctamente en PostgreSQL
> 2. Todos los campos (material, confidence, metadata) son persistidos
> 3. Backend valida datos inválidos (volumen negativo, material inexistente)
> 4. Latency end-to-end < 2s (target: sub-second)
>
> Estos tests son críticos para producción, garantizando que no se pierdan
> datos de clasificación y que la integridad referencial se mantenga."

## 📝 Notas Adicionales

- Los tests usan **mocks** para el classifier (no consumen API keys reales)
- Los tests **NO modifican** data en producción (solo test DB)
- Cada test hace **cleanup** de datos generados
- Los tests pueden correrse en **CI/CD** con Rails en Docker

## 🔄 Integración Continua

Para integrar en GitHub Actions:

```yaml
# .github/workflows/backend_integration.yml
name: Backend Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v2

      - name: Setup Rails Backend
        run: |
          cd ../rails-backend
          bundle install
          rails db:test:prepare
          rails s -d  # Daemon mode

      - name: Setup Python Hub
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt

      - name: Run Backend Integration Tests
        run: ./scripts/test_backend_integration.sh
```

---

**¿Preguntas?** Revisa la documentación de cada test en el archivo fuente.
