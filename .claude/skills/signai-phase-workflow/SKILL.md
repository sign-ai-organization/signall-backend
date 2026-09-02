---
name: signai-phase-workflow
description: Usar cuando se trabaje sobre el plan de implementación del backend de SignAI (docs/plan-implementacion-backend.md) — por ejemplo "sigamos con la siguiente subfase", "implementa la fase 2", "en qué subfase vamos", "termina esta subfase", "dame el commit de esto". También cuando el usuario pregunte qué sigue en el plan o pida el mensaje de commit de un trabajo recién terminado.
---

# Workflow de fases — SignAI Backend

Este skill guía cómo avanzar el plan de `docs/plan-implementacion-backend.md` de forma
consistente con `CLAUDE.md`, subfase por subfase.

## 1. Ubica en qué subfase estás

Antes de escribir nada, determina el estado real del proyecto:

- Revisa `docs/plan-implementacion-backend.md` para ver el orden de fases y subfases.
- Revisa `git log --oneline` para ver qué subfases ya tienen un commit aceptado
  (los mensajes siguen la convención `tipo(scope): descripción` definida en `CLAUDE.md`).
- La siguiente subfase pendiente es la primera, en el orden del plan, que no tenga
  un commit correspondiente todavía.

Si el usuario pide explícitamente una fase o subfase distinta a la que seguiría en
orden, trabaja esa, pero avisa si se está saltando algo que normalmente iría antes.

## 2. Antes de tocar código, revisa el tipo de subfase

El plan marca cada subfase con un tipo. Actúa distinto según cuál sea:

- **🛑 Decisión requerida**: no escribas código. Presenta las opciones tal como
  están en el plan, incluye la recomendación del plan si trae una, y espera a que
  el usuario decida. No asumas una resolución. Una vez decidida, se registra en
  `docs/decisions.md` (ver sección 4).
- **🗂️ Infraestructura / fuera de código**: son pasos que probablemente no puedes
  ejecutar tú (crear un recurso en la nube, por ejemplo). Dile al usuario
  exactamente qué tiene que hacer manualmente y qué necesitas de vuelta para
  continuar (ej. un connection string).
- **🔧 Código**: implementa exactamente lo que la subfase describe.
- **✅ Verificación**: no es un test formal. Sigue la sección "Verificación
  mientras se avanza" de `CLAUDE.md` — algo ligero y rápido, no elaborado.

Si la fase actual está marcada como "Bloqueada por Fase N" y esa fase anterior
no está resuelta, dilo y no avances aunque el usuario no lo haya notado.

## 3. Al implementar una subfase de código

- Usa los nombres exactos de clases y métodos que aparecen en `docs/sdd.md`.
- Sigue las reglas de diseño y convenciones de código de `CLAUDE.md` (inglés en
  código y comentarios, buenas prácticas generales, sin patrón Gateway, etc.).
- Si notas que una regla de diseño no tiene sentido al implementarla, dilo
  explícitamente antes de decidir qué hacer — no la rompas en silencio ni la
  sigas ciegamente si crees que está mal (ver `CLAUDE.md`).
- Implementa solo el alcance de esa subfase. Si al hacerlo notas algo que
  convendría mejorar o adelantar de una subfase siguiente, dilo como
  sugerencia explícita y espera confirmación antes de tocarlo — no lo
  implementes por tu cuenta dentro del mismo cambio.

## 4. Al terminar una subfase

- Verifica de forma ligera que lo implementado hace lo que el SDD describe para
  ese componente, antes de darla por terminada.
- Redacta tú el mensaje de commit, siempre en inglés, siguiendo la convención
  `tipo(scope): descripción`. Básate en lo que realmente se implementó en esta
  subfase, no en el texto exacto que sugiere el plan — el plan puede servirte
  de referencia para el tipo y el alcance (`feat`, `fix`, `chore`, etc.), pero
  la descripción final debe reflejar el código real, no la intención original.
- Si la subfase es de tipo 🛑 Decisión requerida y el usuario ya la resolvió,
  agrega una entrada en `docs/decisions.md` con el formato que ya trae el
  archivo, antes de sugerir el commit `docs(...)` correspondiente. El commit
  debe incluir ese archivo modificado.
- **Nunca ejecutes `git commit` ni `git push`.** Eso lo hace el usuario
  manualmente, siempre.
- Si la subfase es de decisión o infraestructura y no genera commit de código,
  dilo explícitamente en vez de sugerir un commit que no aplica.

## 5. Si solo preguntan por el estado

Si el usuario solo quiere saber en qué subfase van o qué sigue, respóndelo
directamente sin empezar a implementar nada.
