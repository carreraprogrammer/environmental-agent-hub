# EDV-47 · Cierre Técnico — ClassifierFactory (Factory Pattern)

## Resumen
- Implementado Factory Pattern para instanciar adapters de clasificación según configuración, habilitando cambio de modelo sin modificar código.
- Cobertura de modelos: `openai-gpt4` (gpt-4-vision-preview), `openai-gpt4o` (gpt-4o), `gemini`, `roboflow`, `claude` (placeholder con warning).
- Validación automática y suite de tests en verde; documentación y configuración actualizadas.
- Listo para mover ticket a DONE y hacer merge.

## Cambios Clave
- `app/factories/classifier_factory.py`: `create(model_override=None)` y `list_available()`, validación de modelo y logging estructurado.
- `app/core/config.py`: `CLASSIFIER_MODEL` con valores permitidos incluyendo `claude`.
- Tests:
  - Unitarios: `tests/unit/test_classifier_factory.py`
  - Integración (sin red por defecto): `tests/integration/test_classifier_factory_integration.py`
- Validación: `validations/EDV-47/validation-edv47.sh` + reporte `validations/EDV-47/validation_report_edv47.md`
- Pytest marker: `pyproject.toml` registra `integration`.
- README: guía de uso de Factory y setup de Roboflow.

## Criterios de Aceptación
- Factory Pattern:
  - create() y list_available() implementados
  - Lectura de `settings.CLASSIFIER_MODEL` y soporte de override
  - Mapeo y validación de modelos (ValueError en no soportados)
  - Logging estructurado al crear adapters (y warning para `claude`)
- Roboflow:
  - Adapter implementado y soportado por Factory
  - Variables en settings/documentación; integración real habilitable por env
- Testing:
  - Tests unitarios e integración (gated por `RUN_INTEGRATION_TESTS`)

## Validación y Resultados
- Script EDV-47: PASS 51 · FAIL 0 · WARN 2 (integración real opcional, verificación manual de dataset Roboflow).
- Tests: 39 passed, 6 skipped (integraciones reales deshabilitadas por defecto).
- Integración real disponible exportando `RUN_INTEGRATION_TESTS=1` y proveyendo credenciales.

## Decisiones de Diseño
- Interfaz de adapters orientada a `image_url` para alinear con arquitectura (subida asíncrona a S3 en pipeline).
- Logging estructurado consistente por adapter y evento (observabilidad).
- `claude` queda como placeholder explícito con warning para no bloquear el MVP.

## Riesgos y Notas
- `claude` aún no implementado a producción.
- Tests de integración real dependen de red/credenciales; están aislados por marker/env.
- Preservar privacidad de URLs presignados en logs.

## Tiempo Invertido (aprox.)
- ≈ 3 horas (implementación Factory, tests unitarios/integración, validación automatizada, documentación).

