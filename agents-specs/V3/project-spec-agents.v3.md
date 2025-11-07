# Agent Hub – Project Requirements Spec V3.0 (MVP Completo + Integración Backend)

## ⚠️ ARCHITECTURE CONTEXT (Agent Hub Scope)

**Este documento especifica SOLO el sistema de orquestación de agentes.**

**Arquitectura de 3 capas (contexto):**
Frontend (React/Ionic PWA) → **Agent Hub (Python)** → Backend Rails API

**Alcance de este proyecto (Agent Hub Python):**
- ✅ Recibe imagen como **bytes** (preferido) o URL (legacy) - **60% más rápido con bytes**
- ✅ **Upload a S3 asíncrono** - No bloquea clasificación (background task)
- ✅ Valida que haya residuo real en imagen (anti-troll)
- ✅ Clasifica residuo con **modelos de visión intercambiables** (GPT-4o, Gemini, Roboflow)
- ✅ **IMPLEMENTADO:** Roboflow Custom Model (waste-classifier entrenado)
- ✅ **NUEVO:** Detecta subtipo específico (PET_BOTTLE_500ML, ALUMINUM_CAN_355ML, etc.)
- ✅ **NUEVO:** Estima volumen y peso para cálculos ambientales precisos
- ✅ Mapea material a color según NTC 2184
- ✅ Genera feedback educativo con GPT-3.5
- ✅ **COMPLETADO:** Envía datos COMPLETOS al Backend Rails (incluye volumen/peso)
- ✅ Captura métricas comparativas por modelo (accuracy, latencia, costo)
- ✅ Permite switching de modelos sin modificar código
- ❌ NO gestiona usuarios ni autenticación
- ❌ NO persiste datos (solo el backend lo hace)
- ❌ NO genera dashboards

**Proyectos separados (fuera de alcance):**
- Backend Rails API (ya completado - Sprints 1 y 2)
- Frontend PWA (futuro Sprint 5)

---

## 0) Propósito V3.0 - Tesis Ingeniería Ambiental

Definir el **alcance funcional del Agent Hub** para apoyar investigación en **educación y gestión ambiental**:

### **Objetivo Principal (Tesis):**
Recolectar **datos ambientales precisos y relevantes** sobre generación de residuos en ambientes universitarios para:
1. **Educación ambiental**: Retroalimentación inmediata que refuerce comportamientos de reciclaje
2. **Recolección de datos**: Volumenes, tipos y frecuencia de residuos por facultad/ubicación
3. **Análisis ambiental**: Datos que soporten toma de decisiones en gestión de residuos
4. **Impacto cuantificado**: CO₂ evitado, recursos ahorrados, métricas ambientales verificables

### **Componente Técnico (Soporte):**
Sistema de IA que clasifica residuos desde imágenes y **genera datos ambientales estructurados** para análisis. Los aspectos técnicos (arquitectura, modelos, latencia) son **medios**, no fines - herramientas para lograr objetivos ambientales.

### **Alcance Agent Hub:**
Orquestador que: (a) clasifica residuos con IA; (b) **estima datos físicos necesarios** (volumen, peso) para cálculos ambientales precisos; (c) previene uso malicioso; (d) envía datos completos al Backend para persistencia y análisis.

## 1) Objetivos V3.0 (Tesis Ingeniería Ambiental)

### **Objetivos Ambientales (PRIORITARIOS - Tesis):**
1. **Recolección de datos ambientales**: Capturar tipo, volumen y peso de residuos con precisión suficiente para análisis ambiental
2. **Educación ambiental**: Proveer retroalimentación educativa que refuerce comportamientos de reciclaje correctos
3. **Cuantificación de impacto**: Generar datos que permitan calcular CO₂ evitado, agua/energía ahorrada, eficiencia de reciclaje
4. **Análisis por ubicación**: Datos estructurados para comparar generación de residuos entre facultades/estaciones
5. **Soporte a decisiones**: Información para optimizar ubicación de contenedores, campañas educativas, políticas ambientales

### **Objetivos Técnicos (SOPORTE - Desarrollo):**
- **Clasificación automática**: IA que identifica material del residuo sin intervención humana
- **Estimación física**: Volumen y peso aproximados para cálculos ambientales (no requiere precisión de laboratorio)
- **Integración completa**: Todos los datos al Backend Rails para persistencia y análisis
- **Experiencia fluida**: Respuesta <2s para no interrumpir comportamiento de reciclaje
- **Costo sostenible**: <$0.025 por scan para viabilidad a largo plazo

### **Objetivos de Aprendizaje Personal (BONUS - No tesis):**
- Experimentar con arquitectura de agentes especializados
- Comparar modelos de IA (GPT-4o, Gemini, Roboflow) - **curiosidad técnica, no hipótesis central**
- Aplicar patrones de diseño avanzados (DDD, Adapter Pattern)

## 2) Alcance MVP V3.0 - Agent Hub (7 días)

### **Features Ambientales (CORE - Para Tesis):**
- ✅ **Clasificación automática**: Identifica tipo de residuo (PLASTIC, METAL, GLASS, PAPER, ORGANIC)
- ✅ **Estimación física**: Volumen y peso aproximados para cálculos ambientales
- ✅ **Retroalimentación educativa**: Mensajes que refuerzan comportamiento correcto
- ✅ **Integración Backend COMPLETA**: Envía TODOS los datos al Backend Rails para persistencia
- ✅ **Datos estructurados**: Material, volumen, peso, ubicación, fecha → listos para análisis
- ✅ **Prevención de datos inválidos**: Validación anti-troll para calidad de datos

### **Features Técnicas (SOPORTE - Necesarias pero no centrales):**
- ✅ **Pipeline de Validación**: PreValidator anti-troll
- ✅ **Pipeline de Clasificación**: Classifier con arquitectura intercambiable (experimentación)
- ✅ **Pipeline de Detección**: SubtypeDetector para características físicas
- ✅ **Pipeline de Estimación**: VolumeEstimator para datos físicos
- ✅ **Modelos soportados**: GPT-4o (preferido), Gemini 2.0 Flash, Roboflow Custom
- ✅ **Bytes Processing**: Imágenes como bytes (60% mejora latencia)
- ✅ **API REST**: Endpoint `/classify` con FastAPI

### **Features Experimentales (BONUS - Aprendizaje personal):**
- ✅ **Comparación de modelos**: Logs de accuracy, latencia, costo por modelo (curiosidad técnica)
- ✅ **Adapter Pattern**: Arquitectura que permite switching de modelos (práctica de diseño)
- ✅ **Telemetría**: Métricas detalladas por request (debugging/optimización)

### **Fuera de Alcance (Otros proyectos):**
- ❌ Backend Rails API (ya completado - Sprints 1 y 2)
- ❌ Frontend PWA (futuro Sprint 5)
- ❌ Dashboards de análisis (Backend + Frontend)

## 3) Historias de Usuario V3.0 (Enfoque Ambiental)

### **Perspectiva Ambiental (Tesis):**
- Como **estudiante universitario**, quiero escanear mi residuo y recibir **clasificación correcta + feedback educativo + impacto ambiental** en <2s para aprender mientras reciclo
- Como **investigador ambiental (tesista)**, quiero recolectar **datos estructurados** (tipo, volumen, peso, ubicación, fecha) de miles de scans para analizar patrones de generación de residuos
- Como **investigador ambiental**, quiero que el sistema **estime volumen y peso** con precisión razonable (±20-30%) para calcular impactos ambientales sin pesar cada residuo manualmente
- Como **gestor ambiental universitario**, quiero **comparar generación de residuos entre facultades** para focalizar campañas educativas en áreas problemáticas
- Como **investigador ambiental**, quiero **cuantificar CO₂ evitado, agua/energía ahorrada** con datos reales para reportes de sostenibilidad institucional
- Como **estudiante de ingeniería ambiental**, quiero demostrar que **datos automatizados pueden reemplazar mediciones manuales** para gestión de residuos a escala

### **Perspectiva Técnica (Soporte):**
- Como **backend Rails**, quiero recibir datos completos (material, volumen, peso) para calcular métricas ambientales sin estimaciones adicionales
- Como **admin del sistema**, quiero prevenir scans falsos (trolls) para mantener calidad de datos ambientales
- Como **sistema**, quiero clasificar con confianza >70% para garantizar datos confiables para análisis

### **Perspectiva Desarrollo Personal (Bonus):**
- Como **desarrollador tesista**, quiero experimentar con diferentes modelos de IA para aprender sobre trade-offs técnicos (no es hipótesis central de tesis)

## 4) Requisitos Funcionales

### 4.1 Validación de Imagen (PreValidator)

**RF-001**: El sistema DEBE validar que la imagen contenga un objeto físico (residuo) antes de clasificar
- **Regla**: Usar GPT-4o-mini ($0.00015/imagen) para detección rápida
- **Input**: Imagen como bytes (preferido) o URL (legacy)
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
  - **Roboflow Custom** (Roboflow) - **YA ENTRENADO**: $0.001/imagen, latencia ~300ms (modelo: environmental-assitant-agents/waste-classifier-louut-b9sot/1)
- **Output**: `{material: string, confidence: float, model_used: string}`
- **Criterio de aceptación**:
  - ✅ Confidence score entre 0.0 - 1.0
  - ✅ Latencia <1200ms para modelos LLM, <500ms para modelos especializados
  - ✅ Material válido o fallback a "OTHER"
  - ✅ Switching de modelo mediante configuración (ENV var o config file)
  - ✅ Telemetría registra modelo usado en cada request
  - ✅ **IMPLEMENTADO:** Adapters aceptan bytes O URLs (backward compatible)
- **Performance IMPLEMENTADO**: Procesamiento desde bytes reduce latencia ~300ms vs URL (elimina download)

**RF-004**: El sistema DEBE aplicar threshold de confianza
- **Regla**: Si `confidence < 0.6` → clasificar como "OTHER"
- **Regla**: Si `confidence < 0.3` → rechazar request (posible troll avanzado)
- **Razón**: Evitar clasificaciones incorrectas que afecten métricas ambientales

### 4.3 NUEVO - Detección de Subtipo (SubtypeDetector)

**RF-005**: El sistema DEBE detectar características específicas de residuos (NO códigos inventados)
- **CORRECCIÓN CRÍTICA**: SubtypeDetector detecta CARACTERÍSTICAS, NO genera waste_type_codes
- **Input**: imagen (bytes o URL) + material clasificado
- **Método**: Heurísticas basadas en análisis visual
- **Características detectadas**:
  ```yaml
  material_specific:  # Tipo específico de material
    - "aluminum"      # Aluminio (para metales)
    - "steel"         # Acero (para metales)
    - "PET"           # PET (para plásticos)
    - "HDPE"          # HDPE (para plásticos)
  
  container_type:     # Tipo de contenedor
    - "bottle"        # Botella
    - "can"           # Lata
    - "box"           # Caja
    - "jar"           # Frasco
  
  size:               # Tamaño relativo
    - "small"         # Pequeño
    - "standard"      # Estándar
    - "large"         # Grande
  
  color:              # Color (para vidrio principalmente)
    - "clear"         # Transparente
    - "colored"       # De color
    - "white"         # Blanco (para papel)
  ```
- **Output**: `{material_specific: str, container_type: str, size: str, color: str}`
- **Ejemplo Output**:
  ```json
  {
    "material_specific": "aluminum",
    "container_type": "can",
    "size": "standard",
    "color": null
  }
  ```
- **IMPORTANTE**: Estas características se mapean a waste_type_codes REALES del Backend
- **Fallback**: Si no puede determinar → valores null o "unknown"
- **Criterio de aceptación**:
  - ✅ Detecta al menos 2 características por residuo
  - ✅ Latencia <100ms (heurísticas, no IA)
  - ✅ Fallback graceful a valores genéricos

### 4.4 NUEVO - Estimación de Volumen y Peso (VolumeEstimator)

**RF-006**: El sistema DEBE estimar volumen y peso para cálculos ambientales precisos
- **Input**: imagen (bytes o URL) + material + características detectadas
- **Método MVP - Lookup Table** (Recomendada):
  - **Sin IA**: Mapeo determinístico basado en características → volumen/peso
  - **Output**: `{volume_ml: float, weight_g: float, estimation_method: "lookup"}`
  - **Latencia**: <10ms
- **Estimaciones base** (por características, NO por códigos inventados):
  ```yaml
  # Plásticos - Por size detectado
  PLASTIC_small: {volume_ml: 350, weight_g: 12}
  PLASTIC_standard: {volume_ml: 500, weight_g: 15}
  PLASTIC_large: {volume_ml: 1500, weight_g: 35}
  
  # Metales - Por container_type
  METAL_can_standard: {volume_ml: 355, weight_g: 15}
  METAL_can_large: {volume_ml: 500, weight_g: 18}
  
  # Vidrio - Por size y container_type
  GLASS_bottle_standard: {volume_ml: 330, weight_g: 180}
  GLASS_bottle_large: {volume_ml: 750, weight_g: 400}
  
  # Papel - Por size
  PAPER_standard: {volume_ml: 0, weight_g: 50}
  PAPER_large: {volume_ml: 0, weight_g: 150}
  ```
- **Backend Validation**: Backend validará que el volumen/peso sean físicamente posibles
- **Criterio de aceptación**:
  - ✅ Volumen estimado dentro de rangos aceptables (Backend valida con PhysicalEstimationCalculator)
  - ✅ Peso estimado coherente con densidad del material
  - ✅ Fallback a valores promedio si características incompletas
  - ✅ Nunca retornar volumen/peso = 0 para reciclables (usar mínimos)

### 4.5 Mapeo a Color (Mapper)

**RF-007**: El sistema DEBE mapear material a color según NTC 2184
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

### 4.6 NUEVO - Mapeo a Código de Residuo (WasteTypeMapper)

**RF-008**: El sistema DEBE mapear características → waste_type_code REAL del Backend Rails
- **CORRECCIÓN CRÍTICA**: Usa códigos REALES del Backend (NO códigos inventados)
- **Input**: material, características detectadas, volumen estimado
- **Patrón Híbrido**:
  1. **Sincronizar catálogo** desde Backend API en startup (`GET /api/v1/waste_types`)
  2. **Fallback local**: Si Backend no disponible, usar `config/backend_waste_types.yaml`
  3. **Validación**: Verificar que código existe antes de enviar
- **Códigos REALES del Backend** (ejemplos de db/seeds/waste_types.rb):
  ```yaml
  # Plásticos - Por volumen
  PET_BOTTLE_500ML:     # 400-600ml
  PET_BOTTLE_1500ML:    # 1300-1700ml
  HDPE_BOTTLE:          # Genérico
  PLASTIC_OTHER:        # Fallback
  
  # Metales - Por material
  ALUMINUM_CAN:         # Aluminio (genérico, NO "ALUMINUM_CAN_355ML")
  STEEL_CAN:            # Acero
  
  # Vidrio - Por color
  GLASS_BOTTLE_CLEAR:   # Transparente
  GLASS_BOTTLE_COLORED: # De color
  
  # Papel
  PAPER_WHITE_A4:       # Papel blanco
  CARDBOARD_BOX:        # Cartón
  NEWSPAPER:            # Periódico
  
  # Orgánico
  FOOD_WASTE:           # Residuo alimentario
  ```
- **Mapeo inteligente**:
  ```python
  # Plásticos: por volumen
  if material == "PLASTIC" and 400 <= volume_ml <= 600:
      return "PET_BOTTLE_500ML"
  elif material == "PLASTIC" and 1300 <= volume_ml <= 1700:
      return "PET_BOTTLE_1500ML"
  
  # Metales: por material_specific
  elif material == "METAL" and characteristics["material_specific"] == "aluminum":
      return "ALUMINUM_CAN"
  elif material == "METAL" and characteristics["material_specific"] == "steel":
      return "STEEL_CAN"
  
  # Vidrio: por color
  elif material == "GLASS" and characteristics["color"] == "clear":
      return "GLASS_BOTTLE_CLEAR"
  
  # Papel: por container_type
  elif material == "PAPER" and characteristics["container_type"] == "box":
      return "CARDBOARD_BOX"
  ```
- **Fallback**: Si no hay match → usar genérico validado del catálogo
- **Criterio de aceptación**:
  - ✅ 100% de requests tienen waste_type_code válido
  - ✅ Código específico cuando subtipo+volumen son claros
  - ✅ Código genérico cuando datos son ambiguos
  - ✅ Latencia <10ms

### 4.7 Feedback Educativo (FeedbackCoach)

**RF-009**: El sistema DEBE generar mensaje educativo personalizado
- **Modelo**: GPT-3.5-turbo ($0.002/request)
- **Input**: material, subtipo, volumen, impacto_estimado
- **Restricciones**:
  - Máximo 240 caracteres
  - Tono amigable, sin culpar
  - Incluir dato específico (volumen, CO₂ ahorrado)
  - Lenguaje claro para estudiantes universitarios
- **Ejemplos mejorados**:
  - PET_BOTTLE_500ML → "¡Excelente! Tu botella de 500ml será reciclada. Evitas 0.15kg de CO₂ al ambiente 🌱"
  - ALUMINUM_CAN_355ML → "¡Perfecto! Esa lata ahorra 95% de energía vs producir aluminio nuevo ⚡"
  - ORGANIC → "¡Bien hecho! Tus residuos orgánicos se convertirán en compost nutritivo 🌿"
  - OTHER → "Este material va a rechazo. Intenta separar mejor. ¿Puedes identificar el material?"
- **Latencia**: <400ms

### 4.8 Orquestación (Pipeline)

**RF-010**: El sistema DEBE ejecutar agentes en orden secuencial ACTUALIZADO
1. Router → Valida request schema
2. PreValidator → Detecta residuo (abort si falla)
3. Classifier → Clasifica material
4. **NUEVO:** SubtypeDetector → Identifica subtipo específico
5. **NUEVO:** VolumeEstimator → Estima volumen y peso
6. Mapper → Material → Color
7. **NUEVO:** WasteTypeMapper → Material+subtipo+volumen → waste_type_code
8. FeedbackCoach → Genera mensaje educativo enriquecido
9. Assembler → Construye response
10. **ACTUALIZADO:** BackendIntegration → Envía datos COMPLETOS a Rails

**RF-011**: El sistema DEBE propagar `trace_id` en todos los pasos
- **Razón**: Debugging distribuido, correlación de logs

**RF-012**: El sistema DEBE implementar idempotencia
- **Regla**: Mismo `idempotency_key` → retornar respuesta cacheada
- **TTL**: 5 minutos (en memoria, sin Redis para MVP)
- **Header**: `X-Idempotent: true` si es respuesta cacheada

**RF-013**: El sistema DEBE permitir switching de modelos sin modificar código
- **Configuración**: Variable de entorno `CLASSIFIER_MODEL` o archivo `config/models.yaml`
- **Valores permitidos**: `openai-gpt4o`, `gemini-flash`, `roboflow`
- **Hot reload**: Cambio efectivo al reiniciar servicio (sin redeploy)
- **Validación**: Si modelo no configurado → error al startup con mensaje claro
- **Default**: `openai-gpt4o` (preferido por performance)

**RF-014**: El sistema DEBE capturar métricas detalladas por modelo Y por agente
- **Campos obligatorios en logs**:
  - `model_used`: Nombre del modelo
  - `classification_result`: Material clasificado
  - `subtype_detected`: Subtipo identificado
  - `volume_estimated`: Volumen estimado
  - `confidence_score`: Score de confianza
  - `latency_ms`: Tiempo total y por agente
  - `cost_usd`: Costo del request (sum de todos los agentes)
  - `trace_id`: Para correlación

## 5) Requisitos No Funcionales

### 5.1 Performance

**RNF-001**: Latencia end-to-end ACTUALIZADA
- **p95 latency**: <3000ms (3 segundos) - Aumentado por nuevos agentes
- **p50 latency**: <2200ms
- **Timeout**: 8000ms (abort después de 8s)
- **Desglose por agente**:
  ```
  PreValidator:     ~450ms  (GPT-4o-mini)
  Classifier:       ~600ms  (GPT-4o)
  SubtypeDetector:  ~700ms  (GPT-4o)
  VolumeEstimator:  ~50ms   (lookup) / ~700ms (IA)
  WasteTypeMapper:  ~10ms   (determinístico)
  Mapper:           ~5ms    (determinístico)
  FeedbackCoach:    ~400ms  (GPT-3.5-turbo)
  Assembler:        ~10ms   (determinístico)
  BackendIntegration: ~200ms (HTTP a Rails)
  ═══════════════════════════════════════
  TOTAL MVP:       ~2.4s   (con lookup)
  TOTAL IA FULL:   ~3.1s   (con estimación IA)
  ```

**RNF-002**: Throughput
- **MVP**: 5 requests/segundo (reducido por complejidad)
- **Target producción**: 20 requests/segundo

### 5.2 Costos ACTUALIZADOS

**RNF-003**: Costo por scan exitoso
- **Opción A - MVP (Lookup)**:
  ```
  PreValidator:        $0.0002  (GPT-4o-mini)
  Classifier:          $0.0050  (GPT-4o)
  SubtypeDetector:     $0.0050  (GPT-4o)
  VolumeEstimator:     $0.0000  (lookup table)
  FeedbackCoach:       $0.0020  (GPT-3.5-turbo)
  ══════════════════════════════════════
  TOTAL:              ~$0.0122  (dentro de presupuesto)
  ```

- **Opción B - IA Completa**:
  ```
  PreValidator:        $0.0002  (GPT-4o-mini)
  Classifier:          $0.0050  (GPT-4o)
  SubtypeDetector:     $0.0050  (GPT-4o)
  VolumeEstimator:     $0.0050  (GPT-4o)
  FeedbackCoach:       $0.0020  (GPT-3.5-turbo)
  ══════════════════════════════════════
  TOTAL:              ~$0.0172  (ligeramente sobre presupuesto)
  ```

**RNF-004**: Ahorro anti-troll
- Sin validator: 100% requests → modelos caros
- Con validator: 30% trolls bloqueados en $0.0002
- **Estimado**: Con 100 requests/día (30% trolls) → ahorro $10.2/mes

### 5.3 Confiabilidad

**RNF-005**: Circuit breaker en APIs externas
- **Regla**: Si 3 fallos consecutivos → abrir circuito por 30s
- **Aplicar a**: OpenAI, Google, Roboflow APIs
- **Fallback**: Retornar error 503 con retry-after

**RNF-006**: Manejo de errores por agente
- **Timeout agente**: Abort después de timeout específico por agente
- **Rate limit**: Exponential backoff (1s, 2s, 4s), máx 3 reintentos
- **Estimación falla**: Usar valores por defecto del lookup table
- **Subtipo falla**: Usar tipo genérico por material

### 5.4 Observabilidad

**RNF-007**: Logging estructurado
- **Formato**: JSON
- **Nivel**: INFO en producción, DEBUG en desarrollo
- **Campos obligatorios**: `trace_id`, `timestamp`, `agent_name`, `latency_ms`, `cost_usd`
- **NUEVO - Por agente**:
  ```json
  {
    "trace_id": "uuid",
    "timestamp": "2025-11-07T10:30:00Z",
    "agent": "SubtypeDetector",
    "action": "detect_subtype",
    "material": "PLASTIC",
    "subtype_detected": "PET_BOTTLE_500ML",
    "confidence": 0.85,
    "latency_ms": 720,
    "cost_usd": 0.005
  }
  ```

**RNF-008**: Métricas por agente Y por modelo
- **Por agente**: Latencia, tasa de error, costo acumulado
- **Por modelo**: Accuracy, latencia, costo, distribución de confidence
- **NUEVO - Por subtipo**: Accuracy de detección de subtipos
- **NUEVO - Por volumen**: Precisión de estimaciones vs ground truth

## 6) Contratos de Integración ACTUALIZADOS

### 6.1 Input: Request desde Frontend (ACTUALIZADO)

**Opción A - Bytes (Preferido para performance):**
```json
POST /classify
Content-Type: multipart/form-data

{
  "scan_id": "uuid",
  "station_id": "FAC-ING-01",
  "image": <binary file>,                  // PREFERIDO: imagen como bytes
  "tenant_id": "unarino",
  "trace_id": "uuid",
  "idempotency_key": "uuid"
}
```

**Opción B - URL (Legacy/Backward compatible):**
```json
POST /classify
Content-Type: application/json

{
  "scan_id": "uuid",
  "station_id": "FAC-ING-01",
  "image_url": "https://s3.amazonaws.com/bucket/scan.jpg",  // LEGACY
  "tenant_id": "unarino",
  "trace_id": "uuid",
  "idempotency_key": "uuid"
}
```

**Nota:** Upload a S3 ocurre en **background** (no bloquea response). Performance con bytes: **60% más rápido**.

### 6.2 Output: Response exitosa ACTUALIZADA

```json
200 OK

{
  "material": "PLASTIC",
  "subtype": "PET_BOTTLE_500ML",           // NUEVO
  "confidence": 0.89,
  "color": "WHITE",
  "volume_ml": 500,                        // NUEVO
  "weight_g": 15.2,                        // NUEVO
  "waste_type_code": "PET_BOTTLE_500ML",   // NUEVO
  "message": "¡Excelente! Tu botella de 500ml será reciclada. Evitas 0.15kg de CO₂ 🌱",
  "meta": {
    "model_used": "openai/gpt-4o",
    "model_provider": "openai",
    "latency_ms": 1850,                    // ACTUALIZADO: <2s con bytes
    "cost_usd": 0.0122,                    // ACTUALIZADO
    "validator_passed": true,
    "estimation_method": "lookup",          // NUEVO: "lookup" | "ai"
    "input_format": "bytes",                // NUEVO: "bytes" | "url"
    "s3_upload_status": "pending",          // NUEVO: "pending" | "completed" | "failed"
    "agents_executed": [                    // NUEVO: trazabilidad
      "router", "prevalidator", "classifier", 
      "subtypedetector", "volumeestimator", 
      "mapper", "wastetypemapper", "feedbackcoach", "assembler"
    ]
  }
}
```

### 6.3 Output: Response error (UNCHANGED)

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

## 7) Integración con Backend Rails COMPLETADA

### 7.1 Flujo de integración

**Agent Hub llama a Backend (Modo síncrono):**
```
Frontend → Agent Hub → [Pipeline completo] → Backend Rails
                ↓
            Response ← Agent Hub ← [Environmental data] ← Backend Rails
```

### 7.2 Autenticación (Estado Actual MVP)

**Backend Rails - ScansController:**
- ✅ **Actualmente NO requiere autenticación** (`skip_before_action :authenticate_user!`)
- ✅ Solo requiere `idempotency_key` para prevenir duplicados
- ✅ Validación de parámetros (confidence, trace_id)
- 🔮 **Futuro post-MVP**: Implementar X-Service-Key para autenticación service-to-service

**Agent Hub - BackendIntegration:**
- ✅ Envía requests sin X-Service-Key (no requerido actualmente)
- ✅ Incluye X-Idempotency-Key (REQUERIDO)
- ✅ Incluye X-Trace-Id para rastreo
- 🔮 **Preparado** para agregar X-Service-Key cuando Backend lo requiera

### 7.3 Cliente HTTP para Backend ACTUALIZADO

**Endpoint Backend**: `POST /api/v1/scans`

**Autenticación**: 
- **Header**: `X-Service-Key: <service_key>`
- **Purpose**: Service-to-service authentication (NO user authentication)
- **Config**: `BACKEND_SERVICE_KEY` en `.env`

**Request que Agent Hub envía ACTUALIZADO:**
```json
{
  "scan": {
    "scan_id": "uuid",
    "station_id": "FAC-ING-01",
    "waste_type_code": "ALUMINUM_CAN",          // CÓDIGO REAL del Backend (NO "ALUMINUM_CAN_355ML")
    "confidence_score": 0.89,
    "estimated_volume_ml": 355,                 // PRECISO ahora
    "estimated_weight_g": 15.2,                 // PRECISO ahora
    "estimation_method": "lookup",              // NUEVO
    "agent_metadata": {                         // NUEVO: metadata para debugging
      "material": "METAL",
      "characteristics": {
        "material_specific": "aluminum",
        "container_type": "can",
        "size": "standard"
      },
      "trace_id": "uuid"
    },
    "tenant_id": "unarino"
  }
}
```

**Headers enviados:**
```http
X-Service-Key: <service_key>
X-Trace-Id: <trace_id>
X-Idempotency-Key: <idempotency_key>
Content-Type: application/json
```

**Response que Backend devuelve (REAL del Backend Rails):**
```json
{
  "scan_id": "uuid",
  "environmental_impact": {
    "recyclable": true,
    "co2_saved_kg": 0.152,                    // Backend usa "co2_saved_kg" (NO "carbon_footprint_avoided_kg")
    "recycling_efficiency": 0.85,
    "environmental_score": 8.5,
    "water_saved_liters": 0.8,
    "energy_saved_kwh": 0.05
  },
  "response": {
    "color": "WHITE",
    "message": "¡Excelente! Clasificación correcta",
    "points_awarded": 15
  }
}
```

**Error Responses del Backend:**
- **422 Unprocessable Entity**: Validation error (waste_type_code inválido, volumen imposible)
- **401 Unauthorized**: X-Service-Key inválido
- **500 Internal Server Error**: Error del backend (reintentar)

**Retry Strategy:**
- **422, 401**: NO reintentar (error de Agent Hub)
- **500, 503, timeout**: Reintentar hasta 3 veces con exponential backoff

## 8) Casos Edge y Reglas de Negocio ACTUALIZADAS

### 8.1 Múltiples objetos en imagen

**Regla**: Detectar y pedir "un objeto a la vez"

**Prompt PreValidator actualizado:**
```
¿Hay EXACTAMENTE UN objeto (residuo) en la imagen?
- YES: Un solo objeto claro
- NO: Múltiples objetos, mano vacía, o fondo solo
```

### 8.2 NUEVO - Características no identificables

**Regla**: Si SubtypeDetector falla, usar valores genéricos

**Fallback**:
```python
if not characteristics or all(v is None for v in characteristics.values()):
    characteristics = {
        "material_specific": "unknown",
        "container_type": "unknown",
        "size": "standard",
        "color": None
    }
```

### 8.3 NUEVO - Código no existe en Backend

**Regla**: Validar contra catálogo del Backend antes de enviar

**Validación**:
```python
valid_codes = waste_type_mapper.get_valid_codes()
if waste_type_code not in valid_codes:
    logger.error("invalid_waste_type_code", code=waste_type_code)
    waste_type_code = get_fallback_code(material)
```

### 8.4 NUEVO - Volumen fuera de rango

**Validaciones**:
```python
if volume_ml < 10 or volume_ml > 5000:
    volume_ml = DEFAULT_VOLUMES[material]
    
if weight_g < 1 or weight_g > 2000:
    weight_g = DEFAULT_WEIGHTS[material]
```

### 8.4 NUEVO - Backend Rails no disponible

**Regla**: Agent Hub puede responder sin datos ambientales

**Fallback**:
1. Intentar llamada a Backend (timeout 3s)
2. Si falla: responder solo con datos de clasificación
3. Log error para retry manual posterior
4. Response incluye `backend_integration: false`

## 9) Métricas de Éxito ACTUALIZADAS

- ✅ p95 latency <3000ms en flujo completo
- ✅ Tasa de trolls bloqueados >90%
- ✅ False negatives (residuos reales rechazados) <2%
- ✅ Costo promedio por scan <$0.025
- ✅ **NUEVO:** Accuracy de detección de subtipos >75%
- ✅ **NUEVO:** Precisión de estimación de volumen ±25%
- ✅ **NUEVO:** 100% de requests generan waste_type_code válido
- ✅ Integración exitosa con Backend (>95% requests llegan a Rails)
- ✅ 0 errores de clasificación catastróficos (crashes)
- ✅ Logs estructurados con trace_id en 100% de requests
- ✅ Switching de modelos funcional sin modificar código
- ✅ Métricas comparativas exportables para análisis en tesis

## 10) Experimentación y Comparación de Modelos ACTUALIZADA

**Objetivo académico:** Evaluar diferentes modelos de clasificación Y estimación para determinar el balance óptimo entre accuracy, latencia y costo en clasificación completa de residuos.

**Hipótesis actualizadas:**
- H1: Modelos especializados (Roboflow) superan a LLMs en accuracy de subtipo
- H2: GPT-4o ofrece mejor balance costo/performance que modelos más pesados
- H3: Estimación por IA vs lookup table: ¿justifica el costo extra?
- H4: Pipeline completo (10 agentes) mantiene latencia <3s

### 10.1 Modelos a Evaluar ACTUALIZADOS

| Modelo | Provider | Costo/img | Latencia esperada | Disponibilidad MVP | Estado |
|--------|----------|-----------|-------------------|--------------------|--------|
| **GPT-4o** | OpenAI | $0.005 | 600ms (bytes) / 900ms (URL) | ✅ Preferido | ✅ IMPLEMENTADO |
| **Gemini 2.0 Flash** | Google | $0.00 | 700ms (bytes) / 1100ms (URL) | ✅ Alternativa | ✅ IMPLEMENTADO |
| **Roboflow Custom** | Roboflow | $0.001 | 300ms | ✅ Especializado | ✅ IMPLEMENTADO (waste-classifier-louut-b9sot/1) |

**Nota**: Latencias con **bytes processing** son 60% más rápidas que con URLs (elimina paso de download).

### 10.2 Métricas de Evaluación AMPLIADAS

**Primarias**:
- **Material Accuracy**: % materiales correctos
- **Subtype Accuracy**: % subtipos correctos
- **Volume Accuracy**: Precisión estimación (±% del real)
- **End-to-end Latency**: Tiempo total pipeline
- **Cost per scan**: Costo real total

**Secundarias**:
- **Precision/Recall por subtipo**
- **Volume estimation error distribution**
- **Backend integration success rate**
- **User satisfaction** (calidad del feedback)

## 11) Out of Scope ACTUALIZADO

- ❌ Fine-tuning de modelos desde scratch
- ❌ Estimación de peso físico real con CV clásico (usar estimaciones)
- ❌ Múltiples idiomas (solo español para MVP)
- ❌ Analytics en tiempo real con dashboards
- ❌ Frontend PWA (proyecto separado)
- ❌ Autenticación/autorización
- ❌ Redis para cache distribuido
- ❌ **NUEVO:** Detección de objetos múltiples simultáneos
- ❌ **NUEVO:** Estimación de volumen por análisis de profundidad 3D
- ❌ **NUEVO:** Reconocimiento de marcas específicas de productos

## 12) Roadmap Post-MVP

**Fase 2** (después de tesis):
- Modelo custom especializado en subtipos
- Estimación de volumen con análisis 3D
- A/B testing automático entre modelos
- Dashboard de analytics ambientales

**Fase 3** (escalamiento):
- Fine-tuning con datos recolectados
- Detección de múltiples objetos simultáneos
- Modelo edge para clasificación offline
- Integración con más sistemas ambientales

---

## 13) Definición de Éxito del Proyecto ACTUALIZADA

**Para la tesis:**
- ✅ Sistema completo funcional con estimación de volumen
- ✅ Mínimo 100 scans reales con datos ambientales calculados
- ✅ Comparación científica de modelos incluyendo accuracy de subtipos
- ✅ Documentación académica con arquitectura completa

**Para CV/portfolio:**
- ✅ Proyecto deployado con pipeline completo de 10 agentes
- ✅ Demo funcional mostrando estimación de impacto ambiental
- ✅ Métricas de precisión documentadas
- ✅ Arquitectura escalable y modular

---

**Versión:** 3.0  
**Fecha:** 2025-11-07  
**Changelog v3.0:**
- ✅ Agregado SubtypeDetector agent para tipos específicos
- ✅ Agregado VolumeEstimator agent (lookup + opción IA)
- ✅ Agregado WasteTypeMapper para códigos Backend Rails
- ✅ Actualizado pipeline de 7 a 10 agentes
- ✅ Actualizado response con datos completos (volumen, peso, subtipo)
- ✅ Actualizado contratos de integración Backend Rails
- ✅ Ajustados costos y latencias para pipeline expandido
- ✅ Ampliadas métricas de éxito incluyendo estimaciones
- ✅ Corregida desconexión entre Agent Hub y Backend Rails

**Próximo paso:** Crear `architecture-spec-agents.v3.0.md`