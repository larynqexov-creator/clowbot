# Outbox Preview Pack Spec v1

For every dispatched outbox message, dispatcher generates a Preview Pack:

1) **Markdown preview** stored as `Document(domain=outbox, doc_type=outbox_preview)`.
   - Contains YAML-like frontmatter (JSON per key) with summary fields.

2) **Raw preview** stored in object store (MinIO):
   - `preview.eml` for email
   - `preview.json` for telegram/github_issue adapter params

3) **Normalized payload** stored in object store:
   - `preview_payload.json` (full Outbox payload)

Object keys are saved under `outbox_messages.metadata.preview.object_keys`.

Renderer code: `app/outbox/preview.py`.
