---
name: experience-review
description: Review, approve, reject, and retire proposed experience.
---

Use `GET /v1/reviews` and `POST /v1/reviews/{id}`. Approval is a deterministic state transition; preserve the audit evidence and never delete the historical version.
