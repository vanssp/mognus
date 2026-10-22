# Edit Fields (после Webhook)

| Name | Expression |
|------|------------|
| `text` | `{{ $json.body.text }}` |
| `source` | `webhook` |
| `receivedAt` | `{{ $now.toISO() }}` |