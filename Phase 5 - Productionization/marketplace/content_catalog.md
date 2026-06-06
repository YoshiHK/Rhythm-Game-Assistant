### Content Catalog

Defines how content is created, stored, and distributed.

---

### Content Lifecycle

```
draft → published → updated → consumed → deprecated
```

---

### Mapping to Events

Each stage MUST emit:

| Stage | Event |
|------|------|
| created | content_created |
| updated | content_updated |
| published | content_published |
| consumed | content_consumed |

---

### Requirements

- content_id MUST be stable
- versioning MUST be tracked
- provenance_id MUST link to interaction

---

### Invariants

- content is immutable per version
- changes produce new version
- consumption does not alter content

---

Content catalog ensures:
> structured and traceable content lifecycle