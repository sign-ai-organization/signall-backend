# Decisiones

Registro de las decisiones que se van resolviendo entre las marcadas como
🛑 en `docs/plan-implementacion-backend.md`. Cada entrada es corta: qué se
decidió, por qué, y en qué subfase quedó registrada. No reemplaza al SDD —
si una decisión termina cambiando algo del diseño documentado ahí, ese
cambio se refleja en `docs/sdd.md`, y aquí queda solo el porqué.

Entradas más recientes al final.

---

## Ejemplo (borrar cuando se agregue la primera decisión real)

**Subfase:** 1.3 — Herramienta de acceso a datos (DEC-15)
**Decisión:** `asyncpg` directo, sin ORM.
**Por qué:** el modelo son dos tablas sin relaciones entre sí y
`CatalogRepository` carga todo en memoria al arrancar — un ORM añadía
complejidad de configuración sin beneficio real para este caso.
**Fecha:** —
