# API Error Codes Reference

This document lists the standard HTTP error codes used across the **get‑stockdata** service APIs, along with a brief description and typical scenarios.

| Code | Name | Description |
|------|------|-------------|
| **400** | Bad Request | The request is malformed or missing required parameters. |
| **404** | Not Found | The requested resource (e.g., stock code) does not exist. |
| **429** | Too Many Requests | Rate limit exceeded. Clients should back‑off and retry later. |
| **500** | Internal Server Error | Unexpected server error; check logs for details. |
| **504** | Gateway Timeout | Upstream data source (e.g., AkShare) timed out. |

**Guidelines**
- All error responses follow the JSON schema:
  ```json
  {
    "success": false,
    "error": {
      "code": 400,
      "message": "Missing required parameter: codes"
    }
  }
  ```
- Include a human‑readable `message` field to aid debugging.
- For validation errors, use `400` with details about the offending fields.
- For missing data, return `404` with the missing `stock_code`.
- For rate‑limit breaches, include a `Retry‑After` header.

---

*Keep this file up to date as new error handling patterns are introduced.*
