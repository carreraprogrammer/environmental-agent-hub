# SPEC — Orquestación de Agentes (MVP académico, bajo costo)

**Nombre:** `agent-hub-mvp`  
**Propósito:** orquestar agentes para clasificar residuos desde foto (QR → app → backend → agentes) y devolver `{material, confidence, color, message}`.

## 1) Arquitectura (alto nivel)
- **Frontend (Ionic/React PWA)** → sube imagen a S3 (presigned URL) y llama a `POST /classify`.
- **Backend (Rails API)** → valida, genera `scan_id`/`idempotency_key`, delega a Agent Hub y persiste resultado en Postgres.
- **Agent Hub (Python/FastAPI)** → ejecuta pipeline de agentes (lineal, síncrono).
- **Storage:** S3 (imágenes), Postgres (resultados/telemetría).
- **LLM económico:** Groq/DeepSeek para mensajes (FeedbackCoach) solo texto.
- **Visión:** modelo ligero hospedado o API (Roboflow/ Rekognition). MVP: empieza con API.

## 2) Contratos
**Request → Agent Hub**
```json
{
  "scan_id": "uuid",
  "station_id": "FAC-ING-01",
  "image_url": "s3://.../scan.jpg",
  "tenant_id": "uninariño",
  "trace_id": "uuid",
  "idempotency_key": "uuid"
}
```
**Response ← Agent Hub**
```json
{
  "material": "PLASTIC|PAPER|GLASS|METAL|ORGANIC|OTHER",
  "confidence": 0.0,
  "color": "WHITE|GREEN|BLACK",
  "message": "string",
  "meta": { "model": "rekognition|custom", "latency_ms": 123 }
}
```

## 3) Pipeline de agentes (orden y reglas)
1. **Router**  
   - Rechaza si falta `tenant_id` o `image_url`.  
   - Propaga `trace_id`.  
2. **ValidateQR**  
   - Formato `station_id`, tamaño imagen (<= 5MB), MIME permitido.  
3. **Classifier (Visión)**  
   - Devuelve `{material, confidence}`.  
   - `confidence_threshold = 0.6`. Si `< 0.6` ⇒ `material="OTHER"`.  
4. **MapperColombia2184**  
   - Determinístico `material → color` (ej.: reciclables = **BLANCO**, orgánicos = **VERDE**, rechazo = **NEGRO**).  
5. **FeedbackCoach (LLM)**  
   - Genera `message` corto, educativo y claro (máx. 240 chars, sin culpar).  
6. **Assembler**  
   - Construye respuesta final y métricas (`latency_ms`, `model`).  
7. **Idempotencia**  
   - Si llega `idempotency_key` ya procesado, retornar misma respuesta (cache en Rails + encabezado `X-Idempotent: true`).

## 4) No funcionales
- **SLA objetivo:** Agent Hub p95 ≤ 300 ms (sin contar subida a S3).  
- **Seguridad:** `tenant_id` requerido; sin PII; CORS restringido a dominio de la PWA.  
- **Logs:** nivel info con `trace_id`, conteo por material, tasa `<threshold`.  
- **Tests mínimos:** unit (mapper, assembler), contract (pydantic), integración (flujo feliz + bajo umbral).

## 5) Estructura de proyecto (Python)
```
agent-hub/
  app/
    api/              # fastapi routers
      classify.py
    orchestrator/     # pipeline
      run.py
    agents/
      router.py
      validate_qr.py
      classifier.py   # adapta a Rekognition/Roboflow o modelo local
      mapper_col_2184.py
      feedback_coach.py
    rules/
      mapping.py      # material → color
      thresholds.py   # confidence = 0.6
    schemas/          # pydantic models
      inout.py
    utils/
      tracing.py
      idempotency.py  # stub (real cache queda en Rails)
  tests/
    test_mapper.py
    test_schemas.py
    test_pipeline_smoke.py
  pyproject.toml
  README.md
```
## 6) Endpoints
- `POST /classify` → recibe contrato; ejecuta pipeline; responde JSON.  
- `GET /health` → `{status:"ok", version:"x.y.z"}`.

## 7) Definition of Done (DoD)
- Contratos válidos (pydantic) y tests pasan.  
- Latencia p95 medida local ≤ 300 ms (sin red S3).  
- Manejo de umbral y fallback `OTHER` verificado.  
- Mensajes i18n-ready (sin hardcode de branding en código).  
- Rails persiste y el dashboard refleja los nuevos registros.

## 8) Roadmap (fases)
- **F1 (hoy):** orquestación lineal + API visión externa + LLM barato.  
- **F2:** worker/cola para picos; cache idempotente con Redis.  
- **F3:** modelo propio ligerito si reduces costo de visión.
