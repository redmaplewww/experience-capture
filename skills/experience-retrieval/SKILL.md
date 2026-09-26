---
name: experience-retrieval
description: Retrieve scoped, provenance-aware experience for an Agent task.
---

Call `/v1/experiences/search` with the current task context, scope, and query. Use conditions and conflict metadata before applying a result. Treat low-confidence or pending-review results as suggestions requiring confirmation.
