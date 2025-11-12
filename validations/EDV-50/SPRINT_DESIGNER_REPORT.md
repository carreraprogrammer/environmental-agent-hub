# SPRINT DESIGNER REPORT - EDV-50

**Ticket:** EDV-50 - Implementar PreValidator Agent (Anti-Troll)
**Fecha:** $(date +"%Y-%m-%d")
**Owner:** Equipo Agent Hub

---

## Resumen
- Propósito: Validar imágenes entrantes y decidir binariamente si contienen residuos antes de invocar modelos caros.
- Beneficio: Reduce costo/latencia y bloquea abuso (selfies, paisajes, contenido inapropiado).
- Implementación: Agente `PreValidator` asíncrono con `gpt-4o-mini`, timeout 500ms, respuesta JSON parseada y fallback seguro.

---

## Entregables Implementados
- Agente: `environmental-agent-hub/app/agents/pre_validator.py`
- Esquema: `environmental-agent-hub/app/schemas/validation.py`
- Tests unitarios: `environmental-agent-hub/tests/unit/agents/test_pre_validator.py`
- Script de validación: `environmental-agent-hub/validations/EDV-50/validation-edv50.sh`

---

## Trazabilidad a Criterios de Aceptación

1) Schema
- Implementado `ValidationResult` con campos requeridos en `app/schemas/validation.py`.
- Validación: import checks en script (`validation-edv50.sh`) y uso en tests.

2) PreValidator Agent
- Clase `PreValidator` con método `async validate(image_data: bytes, trace_id: str) -> ValidationResult`.
- Usa `gpt-4o-mini`; `max_tokens=150`; `temperature=0.0`.
- Validación: greps del script revisan modelo/parámetros y firma del método comprobada indirectamente por ejecución de tests.

3) Prompt Engineering
- Prompt en español con: definición de residuos, instrucción de JSON, rechazo de selfies/paisajes/animales/borrosas.
- Validación: greps del script para fragmentos clave del prompt.

4) Performance
- Timeout 500ms con `asyncio.wait_for`; lanza `TimeoutError` al exceder.
- Costo objetivo `< $0.0003/request`: uso de `gpt-4o-mini` + respuesta corta en JSON.
- Validación: test de timeout; parámetros `max_tokens` y modelo verificados por script.

5) Parsing
- Parseo de JSON del response con manejo de code fences (```json) y fallback seguro `has_waste=True, confidence=0.5`.
- Logging de advertencia en fallback.
- Validación: tests específicos cubren JSON plano, ` ```json ` y fallback.

6) Logging
- Eventos: `pre_validator_started`, `pre_validator_complete`, `pre_validator_timeout`, `pre_validator_error`, `pre_validator_parse_error`.
- Incluyen `trace_id` y, cuando aplica, `has_waste`/`confidence`.
- Validación: greps del script; pruebas funcionales invocan el flujo.

7) Error Handling
- `TimeoutError` si excede 500ms; `ValueError` si la API falla; siempre log antes de propagar.
- Validación: tests de error/timeout.

8) Testing
- Unit tests cubren: residuo (True), selfie/paisaje (False), timeout, error API, parsing (JSON/markdown/fallback).
- Mock de OpenAI API con `AsyncMock`.
- Gate de cobertura >=90% en script con `--cov-fail-under=90` sobre `app.agents.pre_validator`.

---

## Metodología de Validación
- Estructura: comprobación de archivos requeridos (existencia y rutas) desde el script.
- Imports: verificación con el intérprete del proyecto (`venv`) para `PreValidator` y `ValidationResult`.
- Code Quality: greps para modelo/parámetros, eventos de logging y manejo de errores.
- Tests: ejecución focalizada de `tests/unit/agents/test_pre_validator.py` en modo verbose y gate de cobertura.
- Reproducibilidad: `validation-edv50.sh` deja un reporte en `validations/EDV-50/validation_report_edv50.md` con pass rate y criterios.

---

## Cobertura de Pruebas y Casos
- Casos cubiertos:
  - Residuo detectado → `has_waste=True` y confianza alta.
  - Selfie/Paisaje → `has_waste=False` y confianza baja.
  - Timeout de 500ms → `TimeoutError`.
  - Error en API → `ValueError`.
  - Parsing exitoso (JSON plano) y en code fences (```json).
  - Fallback de parsing con log de warning.
- Mocking:
  - Cliente OpenAI reemplazado por `AsyncMock` devolviendo estructuras `choices[0].message.content` controladas.
- Cobertura:
  - Gate `--cov-fail-under=90` en el script garantiza el umbral requerido.

---

## Coste y Performance
- Modelo: `gpt-4o-mini` con respuesta limitada (`max_tokens=150`, `temperature=0.0`).
- Latencia: 500ms límite por `asyncio.wait_for`; aborta rápidamente si el proveedor se demora.
- Costo estimado: ~0.0002 USD por request (basado en pricing público de `gpt-4o-mini` y payload corto) → cumple el umbral `< $0.0003`.

---

## Cómo Reproducir la Validación
- Ejecutar script: `bash validations/EDV-50/validation-edv50.sh` (usa el venv del repo, igual que EDV-49).
- Tests directos:
  - `venv/bin/pytest tests/unit/agents/test_pre_validator.py -v`
  - `venv/bin/pytest tests/unit/agents/test_pre_validator.py --cov=app.agents.pre_validator --cov-report=term --cov-fail-under=90 -q`
- Test manual (requiere `OPENAI_API_KEY`): ver snippet en la especificación del ticket para cargar una imagen real y comprobar respuesta.

---

## Riesgos y Mitigaciones
- Parsing no estructurado del proveedor → Fallback seguro asumiendo residuo y log de advertencia.
- Latencias variables del proveedor → Timeout agresivo + tratamiento de errores.
- Falsos positivos/negativos en casos ambiguos → Prompt engineering con reglas explícitas y posibilidad de ajustar few-shot si la accuracy baja <90%.

---

## Conclusión (DoD)
- Código implementado, con tests unitarios y validación automatizada.
- Prompt y parámetros ajustados a los criterios (JSON, español, `gpt-4o-mini`, 500ms, `max_tokens=150`, `temperature=0.0`).
- Manejo robusto de errores y logging estructurado con `trace_id`.
- Gate de cobertura >= 90% en el módulo del agente.

El ticket EDV-50 cumple los criterios de aceptación y está listo para su uso por el orquestador (EDV-58).

