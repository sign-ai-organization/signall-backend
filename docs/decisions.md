# Decisiones

Registro de las decisiones que se van resolviendo entre las marcadas como
🛑 en `docs/plan-implementacion-backend.md`. Cada entrada es corta: qué se
decidió, por qué, y en qué subfase quedó registrada. No reemplaza al SDD —
si una decisión termina cambiando algo del diseño documentado ahí, ese
cambio se refleja en `docs/sdd.md`, y aquí queda solo el porqué.

Entradas más recientes al final.

---

## 1.3 — Herramienta de acceso a datos (DEC-15)

**Subfase:** 1.3 — Herramienta de acceso a datos (DEC-15)
**Decisión:** `asyncpg` directo, sin ORM. Migraciones como scripts `.sql`
versionados a mano.
**Por qué:** el modelo son dos tablas sin relaciones entre sí (`catalog`,
`semantic_cache`), y `CatalogRepository` carga todo el catálogo en memoria
al arrancar sin volver a consultar por fila — no hay joins, lazy loading
ni N+1 queries que un ORM (SQLAlchemy + Alembic) resuelva mejor aquí. Se
evaluó explícitamente frente a SQLAlchemy por preferencia previa con JPA
en Java; la diferencia de esfuerzo de setup es mínima (~10 min), pero
SQLAlchemy suma dependencias y piezas de configuración (Alembic, engine,
sesiones async) que no aportan valor real dado que no hay complejidad
relacional que gestionar.
**Fecha:** 2026-09-02
