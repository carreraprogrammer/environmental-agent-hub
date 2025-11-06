# Agent Hub – Project Requirements Spec V2.1 (MVP Académico + Experimentación)

## ⚠️ ARCHITECTURE CONTEXT (Agent Hub Scope)

**Este documento especifica SOLO el sistema de orquestación de agentes.**

**Arquitectura de 3 capas (contexto):**
Frontend (React/Ionic PWA) → **Agent Hub (Python)** ← Backend Rails API

**Alcance de este proyecto (Agent Hub Python):**
- ✅ Recibe imagen desde S3 y metadatos del request
- ✅ Valida que haya residuo real en imagen (anti-troll)
- ✅ Clasifica residuo con **modelos de visión intercambiables** (GPT-4, Claude, Gemini, custom)
- ✅ Mapea material a color según NTC 2184
- ✅ Genera feedback educativo con GPT-3.5
- ✅ Captura métricas comparativas por modelo (accuracy, latencia, costo)
- ✅ Permite switching de modelos sin modificar código
- ✅ Envía datos procesados al Backend Rails
- ❌ NO gestiona usuarios ni autenticación
- ❌ NO persiste datos (solo el backend lo hace)
- ❌ NO genera dashboards

**Proyectos separados (fuera de alcance):**
- Backend Rails API (ya completado - Sprints 1 y 2)
- Frontend PWA (futuro Sprint 5)

---

## 0) Propósito V2.1

Definir el **alcance funcional del Agent Hub** para: (a) orquestar agentes de IA que clasifiquen residuos desde imágenes con **latencia <2s** y **costo controlado**; (b) integrarse con el backend Rails para completar el flujo end-to-end; (c) prevenir uso malicioso mediante validación temprana; **(d) permitir experimentación científica comparando múltiples modelos de clasificación para validar hipótesis académicas sobre eficiencia, accuracy y costo**.

## 1) Objetivos V2.1 (Agent Hub)

- **Académico**: demostrar integración de IA aplicada a problema ambiental real para tesis de ingeniería ambiental
- **Investigación**: comparar múltiples modelos de clasificación (LLMs generalistas vs especializados) evaluando accuracy, latencia y costo para validar hipótesis científicas
- **Técnico**: entregar orquestador Python con pipeline de agentes especializados, robusto, económico y **agnóstico al modelo** (Adapter Pattern)
- **Operacional**: clasificar residuos con p95 latency <2s y costo <$0.015 por scan
- **Integración**: consumir el API del backend Rails para persistir resultados

## 2) Alcance MVP V2.1 - Agent Hub (5 días)

- **Pipeline de Validación**: PreValidator anti-troll con GPT-4o-mini
- **Pipeline de Clasificación**: Classifier con **arquitectura intercambiable** (Adapter Pattern)
- **Modelos soportados MVP**: GPT-4 Vision (baseline), Claude 3.5 Sonnet, GPT-4o
- **Lógica de Negocio**: Mapper material→color (NTC 2184 Colombia)
- **Feedback Educativo**: FeedbackCoach con GPT-3.5-turbo
- **API REST**: Endpoint `/classify` con FastAPI
- **Integración Backend**: Cliente HTTP para enviar datos procesados a Rails
- **Telemetría Científica**: Logs estructurados con modelo usado, latencia, costo y confidence por request

## 3) Historias de Usuario V2.1 (Agent Hub)

- Como **estudiante**, quiero escanear mi residuo y recibir clasificación + feedback en menos de 2 segundos para que la experiencia sea fluida
- Como **admin del sistema**, quiero prevenir requests maliciosos (trolls) para controlar costos de API OpenAI
- Como **backend Rails**, quiero recibir datos de clasificación procesados y confiables vía API para persistir y calcular métricas ambientales
- Como **investigador académico**, quiero comparar accuracy, latencia y costo de diferentes modelos de clasificación (GPT-4, Claude, Gemini, custom) para determinar cuál es óptimo para clasificación de residuos en contexto universitario y validar hipótesis de tesis
- Como **investigador**, quiero logs estructurados con trace_id y modelo usado para debugging y análisis de patrones de clasificación
- Como **gestor de presupuesto**, quiero que el costo por scan sea predecible y <$0.015 para mantener viabilidad económica del proyecto
- Como **desarrollador**, quiero cambiar el modelo de clasificación mediante configuración (sin modificar código) para experimentar rápidamente con diferentes opciones

## 4) Requisitos Funcionales

### 4.1 Validación de Imagen (PreValidator)

**RF-001**: El sistema DEBE validar que la imagen contenga un objeto físico (residuo) antes de clasificar
- **Regla**: Usar GPT-4o-mini ($0.00015/imagen) para detección rápida
- **Input**: URL de imagen en S3
- **Output**: `{has_waste: boolean, reason: string}`
- **Criterio de aceptación**: 
  - ✅ Detecta mano vacía → `has_waste: false`
  - ✅ Detecta residuo en mano → `has_waste: true`
  - ✅ Latencia <500ms
  - ✅ False negatives <2% (no rechazar residuos reales)

**RF-002**: El sistema DEBE rechazar requests sin residuo válido
- **Response**: `400 Bad Request`
- **Body**: `{error_code: "NO_WASTE_DETECTED", message: "...", suggestion: "Acerca un residuo a la cámara"}`
- **Log**: Registrar intento con `trace_id` y razón de rechazo

### 4.2 Clasificación de Material (Classifier)

**RF-003**: El sistema DEBE clasificar residuos en categorías predefinidas usando modelos intercambiables
- **Categorías**: `PLASTIC`, `PAPER`, `GLASS`, `METAL`, `ORGANIC`, `OTHER`
- **Arquitectura**: Adapter Pattern (interface común para todos los modelos)
- **Input**: Imagen como `bytes` (preferido para performance) o `URL` (legacy/backward compatible)
- **Modelos soportados MVP**:
  - **GPT-4o** (OpenAI) - Preferido: $0.005/imagen, latencia ~600ms (base64 native support)
  - **Gemini 2.0 Flash** (Google) - Alternativa: $0.00/imagen, latencia ~700ms (PIL.Image support)
  - **Roboflow Custom** (Roboflow) - Especializado: $0.001/imagen, latencia ~300ms
- **Output**: `{material: string, confidence: float, model_used: string}`
- **Criterio de aceptación**:
  - ✅ Confidence score entre 0.0 - 1.0
  - ✅ Latencia <1200ms para modelos LLM, <500ms para modelos especializados
  - ✅ Material válido o fallback a "OTHER"
  - ✅ Switching de modelo mediante configuración (ENV var o config file)
  - ✅ Telemetría registra modelo usado en cada request
  - ✅ Adapters aceptan bytes O URLs (backward compatible)
- **Performance**: Procesamiento desde bytes reduce latencia ~300ms vs URL (elimina download)

**RF-004**: El sistema DEBE aplicar threshold de confianza
- **Regla**: Si `confidence < 0.6` → clasificar como "OTHER"
- **Regla**: Si `confidence < 0.3` → rechazar request (posible troll avanzado)
- **Razón**: Evitar clasificaciones incorrectas que afecten métricas ambientales

### 4.3 Mapeo a Color (Mapper)

**RF-005**: El sistema DEBE mapear material a color según NTC 2184
- **Mapeo determinístico**:
  ```
  PLASTIC  → WHITE (reciclable)
  PAPER    → WHITE (reciclable)
  GLASS    → WHITE (reciclable)
  METAL    → WHITE (reciclable)
  ORGANIC  → GREEN (compostable)
  OTHER    → BLACK (rechazo)
  ```
- **Sin IA**: Mapeo 100% determinístico (no usar LLM)
- **Latencia**: <5ms

### 4.4 Feedback Educativo (FeedbackCoach)

**RF-006**: El sistema DEBE generar mensaje educativo personalizado
- **Modelo**: GPT-3.5-turbo ($0.002/request)
- **Restricciones**:
  - Máximo 240 caracteres
  - Tono amigable, sin culpar
  - Lenguaje claro para estudiantes universitarios
  - Reforzar conducta positiva
- **Ejemplos**:
  - PLASTIC → "¡Excelente! Tu botella plástica será reciclada. Ayudas a reducir 82g de CO₂"
  - ORGANIC → "¡Bien hecho! Tus residuos orgánicos se convertirán en compost"
  - OTHER → "Este material va a rechazo. Intenta separar mejor tus residuos"
- **Latencia**: <400ms

### 4.5 Orquestación (Pipeline)

**RF-007**: El sistema DEBE ejecutar agentes en orden secuencial
1. Router → Valida request schema
2. PreValidator → Detecta residuo (abort si falla)
3. Classifier → Clasifica material
4. Mapper → Material → Color
5. FeedbackCoach → Genera mensaje
6. Assembler → Construye response
7. BackendIntegration → Envía a Rails (opcional según config)

**RF-008**: El sistema DEBE propagar `trace_id` en todos los pasos
- **Razón**: Debugging distribuido, correlación de logs

**RF-009**: El sistema DEBE implementar idempotencia
- **Regla**: Mismo `idempotency_key` → retornar respuesta cacheada
- **TTL**: 5 minutos (en memoria, sin Redis para MVP)
- **Header**: `X-Idempotent: true` si es respuesta cacheada

**RF-010**: El sistema DEBE permitir switching de modelos sin modificar código
- **Configuración**: Variable de entorno `CLASSIFIER_MODEL` o archivo `config/models.yaml`
- **Valores permitidos**: `openai-gpt4`, `openai-gpt4o`, `claude`, `gemini`, `roboflow`
- **Hot reload**: Cambio efectivo al reiniciar servicio (sin redeploy)
- **Validación**: Si modelo no configurado → error al startup con mensaje claro
- **Default**: `openai-gpt4` (baseline)
- **Criterio de aceptación**:
  - ✅ Cambiar ENV var y reiniciar → modelo cambia
  - ✅ Logs muestran modelo activo al inicio
  - ✅ Error descriptivo si modelo inválido

**RF-011**: El sistema DEBE capturar métricas detalladas por modelo
- **Campos obligatorios en logs**:
  - `model_used`: Nombre del modelo (ej: "openai/gpt-4-vision-preview")
  - `model_provider`: Provider (ej: "openai", "anthropic")
  - `classification_result`: Material clasificado
  - `confidence_score`: Score de confianza
  - `latency_ms`: Tiempo de clasificación
  - `cost_usd`: Costo del request
  - `trace_id`: Para correlación
- **Agregación**: Script para generar CSV con métricas comparativas
- **Export**: Formato compatible con análisis en Python/Excel para tesis
- **Criterio de aceptación**:
  - ✅ Cada request loggea modelo usado
  - ✅ Script `export_metrics.py` genera CSV con comparativas
  - ✅ CSV incluye: modelo, accuracy, latencia_avg, costo_total, requests_count

## 5) Requisitos No Funcionales

### 5.1 Performance

**RNF-001**: Latencia end-to-end
- **p95 latency**: <2000ms (2 segundos)
- **p50 latency**: <1500ms
- **Timeout**: 5000ms (abort después de 5s)

**RNF-002**: Throughput
- **MVP**: 10 requests/segundo
- **Target producción**: 50 requests/segundo

### 5.2 Costos

**RNF-003**: Costo por scan exitoso
- **PreValidator**: $0.0002 (GPT-4o-mini)
- **Classifier**: $0.0100 (GPT-4 Vision)
- **FeedbackCoach**: $0.0020 (GPT-3.5-turbo)
- **Total**: $0.0122 (~$0.015 con overhead)

**RNF-004**: Ahorro anti-troll
- **Sin validator**: 100% requests → GPT-4 → $0.01 cada uno
- **Con validator**: 30% trolls bloqueados en $0.0002 → ahorro 98% en trolls
- **Estimado**: Con 100 requests/día (30% trolls) → ahorro $8.40/mes

### 5.3 Confiabilidad

**RNF-005**: Circuit breaker en OpenAI API
- **Regla**: Si 3 fallos consecutivos → abrir circuito por 30s
- **Fallback**: Retornar error 503 con retry-after

**RNF-006**: Manejo de errores
- **Timeout OpenAI**: Abort después de 10s, log error, responder 504
- **Rate limit OpenAI**: Exponential backoff (1s, 2s, 4s), máx 3 reintentos
- **Imagen corrupta**: Validar antes de enviar a OpenAI, responder 400

### 5.4 Observabilidad

**RNF-007**: Logging estructurado
- **Formato**: JSON
- **Nivel**: INFO en producción, DEBUG en desarrollo
- **Campos obligatorios**: `trace_id`, `timestamp`, `agent_name`, `latency_ms`, `cost_usd`
- **Ejemplo**:
  ```json
  {
    "trace_id": "uuid",
    "timestamp": "2025-10-24T10:30:00Z",
    "agent": "PreValidator",
    "action": "validate_image",
    "result": "has_waste",
    "latency_ms": 450,
    "cost_usd": 0.0002
  }
  ```

**RNF-008**: Métricas por agente Y por modelo
- **Por agente**:
  - Latencia promedio por agente
  - Tasa de error por agente
  - Costo acumulado por agente
  - Contador de requests válidos vs trolls bloqueados
- **Por modelo de clasificación**:
  - Latencia promedio por modelo (p50, p95, p99)
  - Accuracy por modelo (requiere ground truth dataset)
  - Costo acumulado por modelo
  - Distribución de confidence scores por modelo
  - F1-score por categoría y modelo (cuando hay ground truth)
  - Confusion matrix por modelo (para análisis en tesis)

### 5.5 Seguridad

**RNF-009**: Sin PII (Personal Identifiable Information)
- **No almacenar**: Imágenes, nombres de usuarios, ubicaciones GPS
- **Solo almacenar**: `trace_id`, resultados de clasificación, métricas agregadas

**RNF-010**: CORS restringido
- **Whitelist**: Solo dominio del frontend PWA
- **No permitir**: Requests desde dominios externos

**RNF-011**: Rate limiting
- **Límite**: 100 requests/minuto por `tenant_id`
- **Response**: 429 Too Many Requests con header `Retry-After`

## 6) Contratos de Integración

### 6.1 Input: Request desde Frontend/Backend

```json
POST /classify

{
  "scan_id": "uuid",
  "station_id": "FAC-ING-01",
  "image_url": "https://s3.amazonaws.com/bucket/scan.jpg",
  "tenant_id": "unarino",
  "trace_id": "uuid",
  "idempotency_key": "uuid"
}
```

**Validaciones:**
- `scan_id`: UUID válido
- `station_id`: formato `FAC-XXX-##`
- `image_url`: URL válida de S3, accesible públicamente (presigned)
- `tenant_id`: requerido, string no vacío
- `trace_id`: UUID válido
- `idempotency_key`: UUID válido

### 6.2 Output: Response exitosa

```json
200 OK

{
  "material": "PLASTIC",
  "confidence": 0.89,
  "color": "WHITE",
  "message": "¡Excelente! Tu botella plástica será reciclada. Ayudas a reducir 82g de CO₂",
  "meta": {
    "model_used": "openai/gpt-4-vision-preview",
    "model_provider": "openai",
    "latency_ms": 1350,
    "cost_usd": 0.0122,
    "validator_passed": true
  }
}
```

### 6.3 Output: Response error (troll detectado)

```json
400 Bad Request

{
  "error_code": "NO_WASTE_DETECTED",
  "message": "No se detectó un residuo en la imagen",
  "suggestion": "Acerca un objeto (botella, papel, lata, etc.) a la cámara y vuelve a escanear",
  "meta": {
    "validator_reason": "empty_hand",
    "cost_usd": 0.0002
  }
}
```

### 6.4 Output: Response error (baja confianza)

```json
422 Unprocessable Entity

{
  "error_code": "LOW_CONFIDENCE",
  "message": "No se pudo clasificar el residuo con suficiente confianza",
  "suggestion": "Acerca más el objeto a la cámara o mejora la iluminación",
  "meta": {
    "confidence": 0.25,
    "cost_usd": 0.0122
  }
}
```

## 7) Integración con Backend Rails

### 7.1 Flujo de integración (opcional)

**Modo A: Agent Hub llama a Backend** (Recomendado para MVP)
```
Frontend → Agent Hub → Backend Rails
                ↓
            Response ← Agent Hub
```

**Flujo:**
1. Frontend llama `POST /classify` en Agent Hub
2. Agent Hub procesa imagen
3. Agent Hub llama `POST /api/v1/scans` en Backend Rails
4. Backend persiste y calcula impacto ambiental
5. Backend responde a Agent Hub con datos enriquecidos
6. Agent Hub responde a Frontend

**Modo B: Backend orquesta** (Alternativa)
```
Frontend → Backend Rails → Agent Hub
                ↓
            Response ← Backend
```

**Decisión MVP: Usar Modo A** (Agent Hub llama a Backend)

### 7.2 Cliente HTTP para Backend

**Endpoint Backend**: `POST /api/v1/scans`

**Request que Agent Hub envía:**
```json
{
  "scan_id": "uuid",
  "station_id": "FAC-ING-01",
  "waste_type_code": "PET_BOTTLE_500ML",  // Mapear desde material
  "confidence": 0.89,
  "estimated_volume_ml": 500,  // Valor fijo por ahora (futuro: agente estimador)
  "estimated_weight_g": 15.2,  // Valor fijo por ahora
  "image_url": "s3://...",
  "trace_id": "uuid",
  "idempotency_key": "uuid",
  "tenant_id": "unarino"
}
```

**Response que Backend devuelve:**
```json
{
  "scan_id": "uuid",
  "environmental_impact": {
    "recyclable": true,
    "carbon_footprint_avoided_kg": 0.082,
    "recycling_efficiency": 0.85,
    "environmental_score": 8.5
  },
  "response": {
    "color": "WHITE",
    "message": "¡Excelente! Clasificación correcta",
    "points_awarded": 12
  }
}
```

**Manejo de errores Backend:**
- `422`: `waste_type_code` inválido → Agent Hub debe loggear y retornar error genérico
- `500`: Error interno Backend → Agent Hub reintenta 1 vez, luego responde sin datos ambientales
- `timeout`: >3s → Agent Hub responde sin datos ambientales

## 8) Casos Edge y Reglas de Negocio

### 8.1 Múltiples objetos en imagen

**Regla**: Detectar y pedir "un objeto a la vez"

**Prompt PreValidator actualizado:**
```
¿Hay EXACTAMENTE UN objeto (residuo) en la imagen?
- YES: Un solo objeto claro
- NO: Múltiples objetos, mano vacía, o fondo solo
```

**Response si múltiples**: 
```json
{
  "error_code": "MULTIPLE_OBJECTS",
  "message": "Se detectaron múltiples objetos",
  "suggestion": "Escanea un solo residuo a la vez"
}
```

### 8.2 Imagen borrosa o mal iluminada

**Regla**: Classifier retorna `confidence < 0.6` → mapear a OTHER

**Feedback especial**:
- Si `confidence < 0.4`: "Mejora la iluminación o acerca más el objeto"

### 8.3 Residuos no catalogados

**Regla**: Si Classifier retorna material no en lista → mapear a OTHER

**Feedback**: "Material no identificado. Deposita en contenedor negro (rechazo)"

### 8.4 Foto de una foto (spoof)

**Regla**: PreValidator debe detectar esto

**Prompt actualizado**:
```
¿Es un objeto FÍSICO real (no una pantalla, foto impresa, o dibujo)?
```

### 8.5 Timeout de OpenAI

**Regla**: Abort después de 10s, responder 504 Gateway Timeout

**Response**:
```json
{
  "error_code": "CLASSIFICATION_TIMEOUT",
  "message": "El servicio de clasificación tardó demasiado",
  "suggestion": "Intenta de nuevo en unos segundos"
}
```

## 9) Métricas de Éxito (Agent Hub)

- ✅ p95 latency <2000ms en flujo completo
- ✅ Tasa de trolls bloqueados >90%
- ✅ False negatives (residuos reales rechazados) <2%
- ✅ Costo promedio por scan <$0.015
- ✅ Integración exitosa con Backend (>95% requests llegan a Rails)
- ✅ 0 errores de clasificación catastróficos (crashes)
- ✅ Logs estructurados con trace_id en 100% de requests
- ✅ **Switching de modelos funcional** sin modificar código
- ✅ **Métricas comparativas exportables** para análisis en tesis

## 10) Experimentación y Comparación de Modelos

**Objetivo académico:** Evaluar diferentes modelos de clasificación para determinar el balance óptimo entre accuracy, latencia y costo en el contexto específico de clasificación de residuos universitarios.

**Hipótesis a validar:**
- H1: Modelos especializados (Roboflow custom) superan a LLMs generalistas en accuracy
- H2: GPT-4o ofrece mejor balance costo/performance que GPT-4 Vision
- H3: Claude 3.5 Sonnet tiene mejor razonamiento contextual que GPT-4 en casos ambiguos
- H4: Latencia de modelos especializados es 3x menor que LLMs generalistas

### 10.1 Modelos a Evaluar

| Modelo | Provider | Costo/img | Latencia esperada | Disponibilidad MVP |
|--------|----------|-----------|-------------------|--------------------|
| **GPT-4 Vision** | OpenAI | $0.010 | 1000ms | ✅ Baseline |
| **GPT-4o** | OpenAI | $0.005 | 600ms | ✅ MVP |
| **Claude 3.5 Sonnet** | Anthropic | $0.008 | 800ms | ✅ MVP |
| **Gemini Pro Vision** | Google | $0.002 | 700ms | ⏳ Fase 2 |
| **Roboflow Custom** | Roboflow | $0.001 | 300ms | ⏳ Fase 2 |

**Justificación de selección:**
- **GPT-4 Vision**: Baseline académico, modelo más usado en literatura
- **GPT-4o**: Versión optimizada, evaluar si sacrifica accuracy por velocidad
- **Claude 3.5**: Alternativa antropic, evaluar razonamiento contextual
- **Gemini/Roboflow**: Futuro, evaluar especialización vs generalización

### 10.2 Métricas de Evaluación

**Primarias (para comparación científica):**
- **Accuracy**: % clasificaciones correctas vs ground truth
- **Precision**: Por categoría (ej: precision de "PLASTIC" = TP / (TP + FP))
- **Recall**: Por categoría (ej: recall de "PLASTIC" = TP / (TP + FN))
- **F1-Score**: Media armónica de precision y recall por categoría
- **Latencia p95**: Tiempo de respuesta percentil 95
- **Costo/scan**: Costo real promedio por request

**Secundarias (para análisis):**
- **Confusion Matrix**: Matriz NxN de categorías (visualizar errores comunes)
- **Confidence distribution**: Distribución de scores de confianza por modelo
- **Error analysis**: Categorías con más errores por modelo
- **Cost-Accuracy ratio**: Accuracy / costo (eficiencia económica)
- **Speed-Accuracy ratio**: Accuracy / latencia (eficiencia temporal)

### 10.3 Ground Truth Dataset

**Construcción del dataset:**
1. **Tamaño**: 50-100 imágenes de prueba
2. **Distribución balanceada**:
   - 10-20 imágenes por categoría (PLASTIC, PAPER, GLASS, METAL, ORGANIC)
   - Incluir casos ambiguos (5-10 imágenes)
3. **Etiquetado**:
   - 2 expertos ambientales etiquetan independientemente
   - Consenso en casos de discrepancia
   - Documentar casos ambiguos con justificación
4. **Contexto**:
   - Imágenes capturadas en contexto universitario real
   - Iluminación variable (interior/exterior)
   - Ángulos diversos (frontal, lateral, cenital)
5. **Formato**:
   ```json
   {
     "image_id": "test_001",
     "image_url": "s3://bucket/ground-truth/test_001.jpg",
     "true_label": "PLASTIC",
     "true_sublabel": "PET_BOTTLE",
     "confidence": 1.0,
     "ambiguity_notes": "Botella parcialmente aplastada",
     "labelers": ["expert_1", "expert_2"],
     "consensus": true
   }
   ```

**Almacenamiento:**
- CSV: `ground_truth_dataset.csv` en repositorio
- Imágenes: S3 bucket `agent-hub/ground-truth/`

### 10.4 Protocolo de Experimentación

**Fase 1: Baseline (Día 1-2)**
1. Implementar GPT-4 Vision como baseline
2. Ejecutar 50 requests de ground truth
3. Capturar métricas base
4. Generar confusion matrix baseline

**Fase 2: Comparación (Día 3-4)**
1. Cambiar `CLASSIFIER_MODEL=openai-gpt4o`
2. Ejecutar mismos 50 requests
3. Cambiar `CLASSIFIER_MODEL=claude`
4. Ejecutar mismos 50 requests
5. Generar CSVs comparativos

**Fase 3: Análisis (Día 5)**
1. Script `analyze_models.py` genera tablas comparativas
2. Graficar accuracy vs latencia vs costo
3. Identificar modelo óptimo según criterio multi-objetivo
4. Documentar hallazgos para tesis

### 10.5 Configuración de Modelos

**Archivo: `config/models.yaml`**
```yaml
# Configuración de modelos de clasificación
active_model: "openai-gpt4"  # Cambiar para experimentos

models:
  openai-gpt4:
    provider: "openai"
    model_name: "gpt-4-vision-preview"
    api_key_env: "OPENAI_API_KEY"
    cost_per_image: 0.010
    max_tokens: 100
    temperature: 0.0  # Determinístico
    enabled: true
    
  openai-gpt4o:
    provider: "openai"
    model_name: "gpt-4o"
    api_key_env: "OPENAI_API_KEY"
    cost_per_image: 0.005
    max_tokens: 100
    temperature: 0.0
    enabled: true
    
  claude:
    provider: "anthropic"
    model_name: "claude-3-5-sonnet-20241022"
    api_key_env: "ANTHROPIC_API_KEY"
    cost_per_image: 0.008
    max_tokens: 100
    temperature: 0.0
    enabled: true
    
  gemini:
    provider: "google"
    model_name: "gemini-pro-vision"
    api_key_env: "GOOGLE_API_KEY"
    cost_per_image: 0.002
    enabled: false  # Fase 2
    
  roboflow:
    provider: "roboflow"
    model_id: "waste-classifier-v1"
    api_key_env: "ROBOFLOW_API_KEY"
    cost_per_image: 0.001
    enabled: false  # Fase 2

# Prompt template común para todos los modelos
classification_prompt: |
  Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:
  - PLASTIC: Botellas, envases, bolsas plásticas
  - PAPER: Papel, cartón, periódicos
  - GLASS: Botellas de vidrio, frascos
  - METAL: Latas de aluminio, acero
  - ORGANIC: Restos de comida, material vegetal
  - OTHER: Si no encaja claramente en las anteriores
  
  Responde SOLO con el nombre de la categoría en mayúsculas.
  Si tienes dudas, usa OTHER.
```

**Variables de entorno alternativas:**
```bash
# Switching rápido por ENV var (sin editar YAML)
CLASSIFIER_MODEL=openai-gpt4o
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 10.6 Scripts de Análisis

**Script 1: `scripts/run_experiment.py`**
```python
"""
Ejecuta experimento completo:
1. Carga ground truth dataset
2. Ejecuta clasificación con modelo activo
3. Captura métricas
4. Genera CSV de resultados
"""
```

**Script 2: `scripts/analyze_models.py`**
```python
"""
Analiza resultados de múltiples modelos:
1. Lee CSVs de experimentos
2. Calcula accuracy, precision, recall, F1
3. Genera confusion matrices
4. Produce tabla comparativa
5. Genera gráficos para tesis
"""
```

**Script 3: `scripts/export_metrics.py`**
```python
"""
Exporta métricas de logs a CSV:
1. Lee logs estructurados JSON
2. Filtra por modelo
3. Agrupa métricas (latencia, costo, confidence)
4. Exporta CSV compatible con Excel/Python
"""
```

### 10.7 Arquitectura Intercambiable (Adapter Pattern)

**Requisito técnico:** Implementar interface común para todos los modelos

```python
# Pseudocódigo (detalle en architecture-spec)
class ClassifierAdapter(ABC):
    @abstractmethod
    async def classify(image: bytes | str) -> ClassificationResult
        """
        Classify from bytes (preferred) or URL (legacy).
        Bytes format reduces latency ~300ms by eliminating download step.
        """
    
    @property
    @abstractmethod
    def model_name() -> str
    
    @property
    @abstractmethod
    def cost_per_request() -> float
```

**Beneficios:**
- ✅ Cambiar modelo sin tocar código de negocio
- ✅ Testear cada adapter independientemente
- ✅ Agregar nuevos modelos sin modificar pipeline
- ✅ SOLID principles (Open/Closed, Dependency Inversion)

### 10.8 Resultados Esperados (para Tesis)

**Tabla comparativa esperada:**

| Modelo | Accuracy | F1-Score | Latencia p95 | Costo/100 scans | Recomendación |
|--------|----------|----------|--------------|-----------------|---------------|
| GPT-4 Vision | 87% | 0.85 | 1200ms | $1.00 | Baseline |
| GPT-4o | 84% | 0.82 | 650ms | $0.50 | Mejor costo/velocidad |
| Claude 3.5 | 89% | 0.87 | 850ms | $0.80 | Mejor accuracy |
| Gemini Pro | ? | ? | ? | ? | Pendiente |
| Roboflow | ? | ? | ? | ? | Pendiente |

**Insight para tesis:**
> "Los resultados demuestran que modelos LLM generalistas (GPT-4, Claude) logran accuracy entre 84-89%, mientras que GPT-4o ofrece el mejor balance costo-velocidad sacrificando solo 3% de accuracy. Claude 3.5 Sonnet demostró 2% mayor accuracy que GPT-4 Vision, validando su capacidad de razonamiento contextual superior en casos ambiguos. Para producción en contexto universitario con presupuesto limitado, se recomienda GPT-4o como solución óptima."

### 10.9 Criterios de Validación Científica

**Para incluir en tesis:**
- ✅ Mínimo 50 imágenes de ground truth
- ✅ Mínimo 3 modelos comparados
- ✅ Métricas estadísticamente significativas
- ✅ Documentación de metodología experimental
- ✅ Análisis de casos edge y errores
- ✅ Discusión de trade-offs (accuracy vs costo vs latencia)
- ✅ Recomendaciones basadas en evidencia

**Limitaciones a documentar:**
- Ground truth limitado a 50-100 imágenes (restricción de tiempo/presupuesto)
- Contexto específico universitario (resultados no generalizables)
- Modelos evaluados en punto temporal específico (pueden mejorar)
- Confidence scores de LLMs son aproximaciones (no probabilísticos)

## 10) Suposiciones y Dependencias (Agent Hub)

- Backend Rails API ya funciona y acepta `POST /api/v1/scans`
- Imágenes ya están en S3 (Frontend se encarga de upload)
- OpenAI API disponible (gpt-4-vision-preview, gpt-4o-mini, gpt-3.5-turbo)
- S3 presigned URLs válidas por al menos 5 minutos
- Python 3.11+ en ambiente de deployment
- Railway/Render con soporte Docker

## 11) Riesgos & Mitigaciones (Agent Hub)

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Costos OpenAI se disparan | Media | Alto | PreValidator + rate limiting + alertas |
| Falsos negativos altos | Media | Medio | Ajustar threshold, logs detallados |
| Latencia >2s | Media | Alto | Timeout agresivo, paralelizar donde sea posible |
| OpenAI API caída | Baja | Alto | Circuit breaker + fallback response |
| Trolls evolucionan (fotos de fotos) | Media | Medio | Mejorar prompt PreValidator iterativamente |

## 12) Plan de Validación (Agent Hub)

- Tests unitarios de cada agente (mocks de OpenAI)
- Tests de contrato de API (FastAPI test client)
- Tests de integración con Backend Rails (sandbox)
- Tests de performance (k6 o locust): 50 requests/s durante 1 minuto
- Validación de costos: 100 requests reales, verificar costo <$1.50
- Prueba con imágenes reales (10 casos por categoría)
- Prueba anti-troll (mano vacía, foto de foto, múltiples objetos)

## 13) Entregables (Agent Hub)

- API FastAPI deployada en Railway/Render
- Endpoint `/classify` funcional con validación completa
- Cliente HTTP para integración con Backend Rails
- Tests con coverage >70%
- Documentación OpenAPI/Swagger en `/docs`
- Logs estructurados JSON
- README con instrucciones de setup y deploy
- Variables de entorno documentadas (`.env.example`)

## 14) Out of Scope (Agent Hub - Futuro)

- ❌ Entrenamiento de modelos custom desde scratch (usar APIs por ahora)
- ❌ Fine-tuning de modelos (usar modelos pre-entrenados)
- ❌ Estimación de volumen/peso física con CV clásico (hardcodear valores por material)
- ❌ Múltiples idiomas (solo español para MVP)
- ❌ Analytics en tiempo real con dashboards (solo logs)
- ❌ Frontend PWA (proyecto separado)
- ❌ Autenticación/autorización (asumir requests ya validados)
- ❌ Redis para cache distribuido (usar cache in-memory para MVP)
- ❌ A/B testing automático entre modelos (comparación manual por ahora)

**Nota sobre modelos:**
- ✅ Gemini Pro Vision: Agregar en Fase 2 si tiempo permite
- ✅ Roboflow Custom: Agregar en Fase 2 si se entrena modelo especializado
- ✅ Otros modelos: Arquitectura preparada para agregar fácilmente

## 15) Roadmap Post-MVP

**Fase 2** (después de tesis):
- Modelo custom ligero para clasificación (reducir costo)
- Agente Estimador para volumen/peso real (CV clásico + heurísticas)
- Redis para cache distribuido
- Worker asíncrono (Celery) para picos de carga
- Dashboard de analytics para admins

**Fase 3** (escalamiento):
- Fine-tuning de GPT-4 con datos recolectados
- A/B testing de prompts
- Modelo edge para clasificación offline (TensorFlow Lite)
- Soporte multi-región

---

## 16) Definición de Éxito del Proyecto

**Para la tesis:**
- ✅ Sistema completo funcional (Frontend → Agent Hub → Backend)
- ✅ Mínimo 100 scans reales recolectados en piloto universitario
- ✅ Métricas ambientales calculadas y validadas
- ✅ Documentación académica con arquitectura y resultados

**Para CV/portfolio:**
- ✅ Proyecto deployado y accesible públicamente
- ✅ GitHub con README profesional y arquitectura clara
- ✅ Demo funcional en video (2-3 minutos)
- ✅ Casos de uso documentados con screenshots

---

**Versión:** 2.1  
**Fecha:** 2025-10-24  
**Changelog v2.1:**
- ✅ Agregada arquitectura intercambiable de modelos (Adapter Pattern)
- ✅ Agregada sección completa de Experimentación (Sección 10)
- ✅ RF-010: Switching de modelos sin código
- ✅ RF-011: Telemetría científica por modelo
- ✅ RNF-008 ampliado: Métricas por modelo
- ✅ Historia de usuario: Investigador comparando modelos
- ✅ Protocolos de experimentación y análisis
- ✅ Scripts de análisis para tesis

**Próximo paso:** Crear `architecture-spec-agents.v2.md`
