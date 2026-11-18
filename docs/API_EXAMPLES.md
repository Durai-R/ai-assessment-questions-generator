# API examples

These examples follow the FastAPI routes and Pydantic schemas in `backend/app`. Responses are illustrative, not captured from a live service. Replace the password and saved-question ID placeholders before running the relevant commands.

## Setup and authentication

Start the backend from `backend\` so its `.env` file is loaded, then run these PowerShell examples in the same session. They use `curl.exe`, an HttpOnly-cookie-compatible cookie jar, and the local frontend origin allowed by `backend/.env.example`.

```powershell
$apiBase = 'http://localhost:8000'
$origin = 'http://localhost:5173'
$cookieJar = Join-Path $env:TEMP 'ai-assessment-cookies.txt'
```

All `POST`, `PATCH`, and `DELETE` requests under `/api/` require an `Origin` exactly matching `FRONTEND_ORIGIN` or one of `TRUSTED_ORIGINS`. The examples send that header. The API does not use a CSRF token. `GET` requests do not require `Origin`. The browser frontend sends cookies with Axios `withCredentials`; `curl.exe` uses `-b` and `-c` to send and store the HttpOnly cookie.

## Register

- **Purpose:** Create an account.
- **Method and path:** `POST /api/auth/register`
- **Authentication:** Public; requires a trusted `Origin`.
- **Success:** `201 Created`

Request:

```powershell
curl.exe -i -H "Origin: $origin" -H 'Content-Type: application/json' `
  --data-raw '{"email":"learner@example.com","password":"<PASSWORD-8-TO-128-CHARACTERS>"}' `
  "$apiBase/api/auth/register"
```

Illustrative response:

```json
{
  "id": "665f00000000000000000001",
  "email": "learner@example.com"
}
```

The email is normalized to lowercase. The response never includes the password or its hash.

## Login

- **Purpose:** Authenticate and set the HttpOnly access-token cookie.
- **Method and path:** `POST /api/auth/login`
- **Authentication:** Public; requires a trusted `Origin`.
- **Success:** `200 OK`

Request (the cookie jar is created/updated by `-c`):

```powershell
curl.exe -i -c $cookieJar -b $cookieJar -H "Origin: $origin" `
  -H 'Content-Type: application/json' `
  --data-raw '{"email":"learner@example.com","password":"<PASSWORD-8-TO-128-CHARACTERS>"}' `
  "$apiBase/api/auth/login"
```

Illustrative response body:

```json
{
  "id": "665f00000000000000000001",
  "email": "learner@example.com"
}
```

The response also sets the configured cookie (default name `assessment_access_token`) with `HttpOnly`, `Path=/`, and `SameSite=Lax`. The JWT is not returned in the JSON body.

## Current user

- **Purpose:** Return the profile associated with the authentication cookie.
- **Method and path:** `GET /api/auth/me`
- **Authentication:** Required; send the cookie from the login cookie jar.
- **Success:** `200 OK`

Request:

```powershell
curl.exe -i -b $cookieJar "$apiBase/api/auth/me"
```

Illustrative response:

```json
{
  "id": "665f00000000000000000001",
  "email": "learner@example.com"
}
```

## Logout

- **Purpose:** Expire the authentication cookie.
- **Method and path:** `POST /api/auth/logout`
- **Authentication:** No valid session is required by the route; requires a trusted `Origin`.
- **Success:** `204 No Content` (empty body)

Request:

```powershell
curl.exe -i -b $cookieJar -c $cookieJar -H "Origin: $origin" `
  -X POST "$apiBase/api/auth/logout"
```

The response expires the cookie using the same cookie attributes as login.

## Suggest topics

- **Purpose:** Ask Gemini for five distinct topic suggestions for a subject.
- **Method and path:** `POST /api/topics/suggest`
- **Authentication:** Required; requires a trusted `Origin`.
- **Success:** `200 OK`

Request:

```powershell
curl.exe -i -b $cookieJar -H "Origin: $origin" -H 'Content-Type: application/json' `
  --data-raw '{"subject":"React.js"}' "$apiBase/api/topics/suggest"
```

Illustrative response:

```json
{
  "topics": ["Hooks", "Components", "Props", "State Management", "Routing"]
}
```

## Generate a question draft

- **Purpose:** Generate an unsaved MCQ draft for the selected subject, topic, and difficulty.
- **Method and path:** `POST /api/questions/generate`
- **Authentication:** Required; requires a trusted `Origin`.
- **Success:** `200 OK`

Request:

```powershell
curl.exe -i -b $cookieJar -H "Origin: $origin" -H 'Content-Type: application/json' `
  --data-raw '{"subject":"React.js","topic":"Hooks","difficulty":"Medium","count":1}' `
  "$apiBase/api/questions/generate"
```

Illustrative response:

```json
{
  "questions": [
    {
      "question_text": "Which Hook is used to add state to a function component?",
      "options": ["useState", "useMemo", "useRef", "useEffect"],
      "correct_option_index": 0,
      "explanation": "useState returns the current state and a function to update it."
    }
  ]
}
```

The draft has no saved-question ID. Generation does not write to MongoDB.

## Save a reviewed batch

- **Purpose:** Validate and persist a reviewed batch for the signed-in user.
- **Method and path:** `POST /api/questions/bulk`
- **Authentication:** Required; requires a trusted `Origin`.
- **Success:** `201 Created`

The request uses batch-level `subject`, `topic`, and `difficulty`; each question contains its own text, four options, correct option index, and explanation. The example uses reviewed content, which may differ from the generated draft.

Request:

```powershell
curl.exe -i -b $cookieJar -H "Origin: $origin" -H 'Content-Type: application/json' `
  --data-raw '{"subject":"React.js","topic":"Hooks","difficulty":"Medium","questions":[{"question_text":"Which Hook is used to add state to a function component?","options":["useState","useMemo","useRef","useEffect"],"correct_option_index":0,"explanation":"useState returns the current state and a function to update it."}]}' `
  "$apiBase/api/questions/bulk"
```

Illustrative response:

```json
{
  "items": [
    {
      "id": "<QUESTION_ID>",
      "subject": "React.js",
      "topic": "Hooks",
      "difficulty": "Medium",
      "question_text": "Which Hook is used to add state to a function component?",
      "options": ["useState", "useMemo", "useRef", "useEffect"],
      "correct_option_index": 0,
      "explanation": "useState returns the current state and a function to update it.",
      "created_at": "2026-01-15T12:00:00Z",
      "updated_at": "2026-01-15T12:00:00Z"
    }
  ]
}
```

The response's ID and timestamps are generated by the backend. A replica set is required for the transactional save.

## List questions with combined filters and pagination

- **Purpose:** Search and filter the signed-in user's saved questions, then return one page.
- **Method and path:** `GET /api/questions`
- **Authentication:** Required.
- **Success:** `200 OK`

`search` is a case-insensitive literal substring of question text. `subject`, `topic`, and `difficulty` are exact-match filters. Filters are combined. `page` starts at 1; `page_size` is 1–100 (default 10).

Request:

```powershell
curl.exe -i -b $cookieJar --get `
  --data-urlencode 'search=state' `
  --data-urlencode 'subject=React.js' `
  --data-urlencode 'topic=Hooks' `
  --data-urlencode 'difficulty=Medium' `
  --data-urlencode 'page=1' `
  --data-urlencode 'page_size=10' `
  "$apiBase/api/questions"
```

Illustrative response:

```json
{
  "items": [
    {
      "id": "<QUESTION_ID>",
      "subject": "React.js",
      "topic": "Hooks",
      "difficulty": "Medium",
      "question_text": "Which Hook is used to add state to a function component?",
      "options": ["useState", "useMemo", "useRef", "useEffect"],
      "correct_option_index": 0,
      "explanation": "useState returns the current state and a function to update it.",
      "created_at": "2026-01-15T12:00:00Z",
      "updated_at": "2026-01-15T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

An empty result uses the same shape with `"items": []` and `"total": 0`. Results are ordered newest first, with an ID tie-breaker.

## Load filter options

- **Purpose:** Load distinct subjects and topics belonging to the signed-in user. Supplying a subject narrows only the topic options.
- **Method and path:** `GET /api/questions/filter-options`
- **Authentication:** Required.
- **Success:** `200 OK`

Request (optional subject filter):

```powershell
curl.exe -i -b $cookieJar --get --data-urlencode 'subject=React.js' `
  "$apiBase/api/questions/filter-options"
```

Illustrative response:

```json
{
  "subjects": ["React.js"],
  "topics": ["Hooks"]
}
```

## Edit a saved question

- **Purpose:** Update one or more fields on a saved question owned by the signed-in user.
- **Method and path:** `PATCH /api/questions/{question_id}`
- **Authentication:** Required; requires a trusted `Origin`.
- **Success:** `200 OK`

The API permits updates to `subject`, `topic`, `difficulty`, `question_text`, `options`, `correct_option_index`, and `explanation`. The current frontend edit dialog does not expose subject or topic.

Request:

```powershell
$questionId = '<24-CHARACTER-SAVED-QUESTION-ID>'
curl.exe -i -b $cookieJar -H "Origin: $origin" -H 'Content-Type: application/json' `
  -X PATCH --data-raw '{"difficulty":"Medium","explanation":"Reviewed explanation: useState returns the current state and an update function."}' `
  "$apiBase/api/questions/$questionId"
```

Illustrative response:

```json
{
  "id": "<QUESTION_ID>",
  "subject": "React.js",
  "topic": "Hooks",
  "difficulty": "Medium",
  "question_text": "Which Hook is used to add state to a function component?",
  "options": ["useState", "useMemo", "useRef", "useEffect"],
  "correct_option_index": 0,
  "explanation": "Reviewed explanation: useState returns the current state and an update function.",
  "created_at": "2026-01-15T12:00:00Z",
  "updated_at": "2026-01-16T12:00:00Z"
}
```

The ID in the command is a placeholder; substitute the actual ID returned by bulk save or listing.

## Delete a saved question

- **Purpose:** Delete one saved question owned by the signed-in user.
- **Method and path:** `DELETE /api/questions/{question_id}`
- **Authentication:** Required; requires a trusted `Origin`.
- **Success:** `204 No Content` (empty body)

Request:

```powershell
$questionId = '<24-CHARACTER-SAVED-QUESTION-ID>'
curl.exe -i -b $cookieJar -H "Origin: $origin" -X DELETE `
  "$apiBase/api/questions/$questionId"
```

Replace the placeholder with a valid saved-question ID.

## Representative errors

The following response bodies are illustrative and reflect the implemented status codes and public messages.

### Request validation — `422 Unprocessable Entity`

For example, `count: 0` on question generation:

```json
{
  "detail": [
    {
      "loc": ["body", "count"],
      "msg": "Input should be greater than or equal to 1",
      "type": "greater_than_equal"
    }
  ]
}
```

Question inputs also reject invalid difficulty values, unknown fields, missing/extra question fields, fewer/more than four options, duplicate or blank options, and a non-integer or out-of-range answer index. The frontend returns validation issues in the same `detail` array shape.

### Unauthenticated request — `401 Unauthorized`

```json
{"detail":"Authentication required."}
```

This applies to protected routes when the cookie is missing, invalid, expired, or its user no longer exists.

### Untrusted or missing Origin — `403 Forbidden`

For a state-changing `/api/` request:

```json
{"detail":"Request origin is not allowed."}
```

### Invalid or incomplete Gemini response — `502 Bad Gateway`

An unparseable response, schema-invalid response (including duplicate options), or a result with the wrong number of questions is not returned as a draft. Representative public messages:

```json
{"detail":"Gemini returned an invalid response. Try generating again."}
```

If the generated question count differs from the requested count:

```json
{"detail":"Gemini returned fewer questions than requested. Try generating again."}
```

For topic suggestions with fewer than five distinct topics:

```json
{"detail":"Gemini returned fewer than five distinct topics. Try generating again."}
```

### Gemini timeout — `504 Gateway Timeout`

```json
{"detail":"Gemini generation timed out. Try again."}
```

### Gemini quota/rate limit — `429 Too Many Requests`

```json
{"detail":"AI generation reached its usage limit. Try again later."}
```

### Gemini temporary unavailability — `503 Service Unavailable`

After retries for provider status 503 are exhausted:

```json
{"detail":"The AI service is temporarily busy. Please wait a moment and try again."}
```

If the backend has no configured key, generation also returns `503`:

```json
{"detail":"AI generation is not configured. Set GEMINI_API_KEY on the backend."}
```

Other recognized provider failures return `502` with `"Gemini could not complete generation. Try again."`; an HTTP transport error returns `502` with `"Gemini is temporarily unavailable. Try again."`. A save on MongoDB without transaction support returns `503` with `"Bulk save requires a MongoDB replica set with transaction support."`
