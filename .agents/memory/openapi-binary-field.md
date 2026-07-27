---
name: OpenAPI binary file fields break lib typecheck
description: Using format:binary in OpenAPI spec generates zod.instanceof(File) which fails TypeScript typecheck in Node.js lib packages.
---

Orval generates `zod.instanceof(File)` for `format: binary` fields and `Blob` for multipart file types. These are browser-only types and are not in scope for the `lib/api-zod` package (which has no `"dom"` lib in tsconfig). The downstream `pnpm run typecheck:libs` step fails with TS2304.

**Why:** `lib/api-zod` is a composite Node.js lib, not a browser bundle. It doesn't have DOM types.

**How to apply:** Never use `type: string, format: binary` or multipart file schemas in `lib/api-spec/openapi.yaml`. For file upload endpoints, either omit the request body from the spec or represent the file as a plain string field (e.g. `filename: string`). The actual multipart handling can be done in the FastAPI route with `UploadFile = File(...)` without a typed OpenAPI schema.
