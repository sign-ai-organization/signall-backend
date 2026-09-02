---
name: signai-sdd-conformance
description: Usar cada vez que se implemente o modifique una clase, método, atributo o enum del backend que tenga equivalente en docs/sdd.md, y también cuando el usuario pida explícitamente revisar o auditar que el código coincida con el SDD — por ejemplo "revisa que esto coincida con el SDD", "verifica el diseño", "auditemos el código contra el SDD".
---

# Verificación de fidelidad código ↔ SDD

`CLAUDE.md` ya establece que los nombres de clases y métodos deben coincidir
exactamente con `docs/sdd.md`. Este skill es el chequeo mecánico de esa regla:
comparar lo que existe en el código contra lo que dice el diagrama correspondiente,
y señalar cualquier diferencia en vez de dejarla pasar o corregirla en silencio.

## Cuándo se dispara

- Al terminar de implementar o modificar una clase, método, atributo o enum que
  tenga equivalente en el SDD (que es prácticamente todo el dominio de este
  proyecto).
- Cuando el usuario pida explícitamente una auditoría de conformidad, revisando
  el código ya existente contra el SDD completo, no solo lo nuevo.

## Qué se compara

Contra el diagrama correspondiente en `docs/sdd.md` (y su imagen en
`docs/diagrams/` si hace falta precisión visual):

- Nombre exacto de la clase o interfaz.
- Firma de cada método: nombre, parámetros, tipos, tipo de retorno.
- Nombre y tipo de cada atributo.
- Valores exactos de enums (ej. `PhraseType`: `AFFIRMATIVE`, `YES_NO_QUESTION`,
  `CONTENT_QUESTION`, `NEGATIVE`, `IMPERATIVE` — en inglés, tal como está en el
  diagrama, no traducidos).
- Relaciones de dependencia que el diagrama muestra (ej. qué clase depende de
  cuál) cuando sean relevantes para lo que se está revisando.

## Qué hacer si algo no coincide

No corrijas nada por tu cuenta, en ninguna dirección. Detente y reporta:

- Qué archivo y símbolo del código no coincide.
- Qué dice exactamente el SDD en ese punto (cita la firma o el valor tal cual
  aparece en el diagrama).
- La diferencia específica (nombre distinto, parámetro faltante, tipo
  distinto, etc.).

Deja que el usuario decida si el código está mal o si el SDD necesita
actualizarse — no asumas ninguna de las dos. Si hay varias discrepancias,
repórtalas todas juntas en vez de una por una.

## Qué no hacer

- No evalúes si una decisión de diseño del SDD "tiene sentido" (eso ya lo
  cubre `CLAUDE.md` en general) — este skill es solo fidelidad mecánica de
  nombres, firmas y valores, no una revisión de si el diseño es bueno.
- No marques como discrepancia algo que el SDD deja explícitamente abierto o
  pendiente (ver la sección de decisiones abiertas de `CLAUDE.md`).
- Si no encuentras el símbolo correspondiente en el SDD (por ejemplo, código
  interno sin equivalente en los diagramas, como helpers privados), no lo
  reportes como discrepancia — el SDD no pretende cubrir cada detalle interno.
