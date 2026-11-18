# AI Assessment Generator

A React and FastAPI application for generating multiple-choice questions with Google Gemini. Users can review and edit generated drafts before saving them to a MongoDB question bank.

## Project overview

The application supports account registration and cookie-based sign-in, AI topic suggestions, and question generation for a selected subject, topic, and difficulty. Generated questions remain a draft in the browser until the user reviews them and selects **Save All**. Saved questions can then be searched, filtered, paginated, edited, and deleted.

## Features

- Register and sign in with an email and password.
- Suggest topics for a subject and generate 1–30 multiple-choice questions.
- Review a draft, edit question content, options, the correct answer, explanation, and difficulty, or remove a draft row. Subject and topic are not editable in the question edit dialog.
- Regenerate questions and save the reviewed batch together.
- Manage saved questions with server-side question-text search, subject/topic/difficulty filters, and pagination.
- Show loading, error, success, and empty states in the generation and question-bank workflows.
- Use an HttpOnly cookie to restore the signed-in user after a page refresh.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React, Vite, React Router, Redux Toolkit, React Redux, Axios |
| Backend | Python, FastAPI, Pydantic, Pydantic Settings |
| Database | MongoDB using PyMongo's asynchronous client |
| Authentication | Argon2 password hashing, PyJWT |
| AI generation | Google Gen AI Python SDK (`google-genai`) |
| AI default model | `gemini-3.5-flash-lite` |

The model can be overridden with the backend `GEMINI_MODEL` environment variable. The repository does not pin a Python runtime version or declare Node engines. Python 3.10+ is needed for the source syntax. The installed Vite 6 dependency supports Node `^18`, `^20`, or `>=22`.

## Architecture and technical decisions

1. React pages use the Axios client and endpoint service modules to call FastAPI. The shared client sends credentials, and Redux stores the current user profile and authentication status—not a JWT.
2. FastAPI validates request data with Pydantic and checks the HttpOnly JWT cookie on protected routes.
3. Topic and question generation call Gemini from the backend. Gemini output is requested as structured JSON, parsed, and validated before the API returns it.
4. Generated questions are returned as an in-memory draft. Generation does not create MongoDB question records.
5. **Save All** sends the reviewed batch to FastAPI. The backend validates it again and writes the batch in a MongoDB transaction.
6. Saved-question search, filters, ordering, and pagination are applied by the backend, so the browser receives only the requested page.

The frontend separates pages, reusable components, routes, API configuration, and endpoint services. The backend separates authentication, schemas, generation, database setup, and routers. This keeps the assessment project straightforward while centralizing shared concerns such as validation and authentication.

Question-text search is a case-insensitive literal substring match. Subject, topic, and difficulty filters are exact matches. Results are ordered newest first, with a stable ID tie-breaker.

## Prerequisites and local setup

- Python 3.10 or later. No exact version is pinned in the repository; the backend was previously exercised with Python 3.12.3.
- Node.js supported by the installed Vite version (`^18`, `^20`, or `>=22`) and npm. The frontend uses `package-lock.json`; use `npm ci`.
- MongoDB reachable by the backend. A replica set is required for transactional batch saves.
- A Gemini API key for topic suggestions and question generation. Login and saved-question management do not require a Gemini key.

### 1. Start MongoDB

For local development,  need to run mongo db server localy:

If you already have MongoDB, configure `MONGODB_URI` to point to it; its deployment must support transactions for batch saves.

### 2. Configure and run the backend

Run these commands from the repository root in PowerShell:

```powershell
Copy-Item backend\.env.example backend\.env
py -3 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Edit `backend\.env`. Set a long, unique `JWT_SECRET` and replace the `GEMINI_API_KEY` placeholder with your key. Do not put the Gemini key in frontend variables or commit a real key.

Start the backend from the `backend` directory:

```powershell
Set-Location backend
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

### 3. Configure and run the frontend

In a second terminal, from the repository root:

```powershell
Set-Location frontend
npm ci
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Open `http://localhost:5173`. `VITE_API_BASE_URL` is optional for local development because the frontend defaults to `http://localhost:8000`. There is currently no `frontend/.env.example`; do not copy the backend environment file into the frontend.

Use the same hostname (`localhost`) for the frontend and backend during local development. For deployment, configure the exact frontend origin in the backend and use HTTPS.

## Environment variables

### Frontend

| Variable | Required | Example/default | Purpose |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | No for local development | `http://localhost:8000` | FastAPI base URL. If omitted, the frontend uses this local default. Set it before starting Vite or building for a different backend. |

The frontend environment table reflects the Axios configuration. No frontend `.env.example` is currently provided.

### Backend

The names and local examples below correspond to `backend/.env.example`.

| Variable | Required | Example/default | Purpose |
| --- | --- | --- | --- |
| `MONGODB_URI` | Yes for backend startup | `mongodb://localhost:27017/?replicaSet=rs0` | MongoDB connection URI. |
| `MONGODB_DB_NAME` | No | `ai_assessment` | Database name. |
| `JWT_SECRET` | Yes for a secure deployment | `replace-with-a-long-random-secret-at-least-32-characters` | Secret used to sign JWTs. Replace the sample value; never commit a real secret. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing and verification algorithm. |
| `JWT_EXPIRY_MINUTES` | No | `60` | JWT and cookie lifetime in minutes. |
| `FRONTEND_ORIGIN` | No for local development | `http://localhost:5173` | Frontend origin allowed by CORS and the Origin check. |
| `TRUSTED_ORIGINS` | No | Empty | Comma-separated additional trusted browser origins for state-changing requests. `FRONTEND_ORIGIN` is trusted as well. |
| `AUTH_COOKIE_NAME` | No | `assessment_access_token` | Name of the HttpOnly authentication cookie. |
| `AUTH_COOKIE_DOMAIN` | No | Empty (host-only cookie) | Cookie domain, if one is needed for the deployment. |
| `AUTH_COOKIE_SECURE` | No | `false` locally | Enables the cookie's `Secure` attribute. Production mode forces secure cookies. |
| `ENVIRONMENT` | No | `development` | Runtime environment; use `production` for deployment. |
| `GEMINI_API_KEY` | For generation only | `replace-with-your-google-ai-studio-api-key` | Backend-only Google Gemini credential. If missing, generation requests return a configuration error; other app features remain available. |
| `GEMINI_MODEL` | No | `gemini-3.5-flash-lite` | Gemini model identifier. |

The MongoDB integration test reads `MONGO_TEST_URI` directly from the process environment. It defaults to a local replica-set URI; point it at a disposable test database if you want to run that test.

## API reference

For endpoint-by-endpoint request/response examples, cookie-jar authentication, the required `Origin` header, and representative errors, see [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md).

Examples below are illustrative and were not captured from a live Gemini-backed run. All request bodies and response fields are based on the implemented Pydantic schemas and route handlers.

### Endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register` | Public | Create an account. |
| `POST` | `/api/auth/login` | Public | Sign in and set the HttpOnly cookie. |
| `GET` | `/api/auth/me` | Cookie | Return the current user profile. |
| `POST` | `/api/auth/logout` | Origin checked | Expire the authentication cookie. |
| `POST` | `/api/topics/suggest` | Cookie | Suggest topics for a subject. |
| `POST` | `/api/questions/generate` | Cookie | Generate a question draft. |
| `POST` | `/api/questions/bulk` | Cookie | Validate and persist a reviewed batch. |
| `GET` | `/api/questions` | Cookie | Search, filter, sort, and paginate saved questions. |
| `GET` | `/api/questions/filter-options` | Cookie | Return subjects and topics for filter controls. |
| `PATCH` | `/api/questions/{question_id}` | Cookie | Update a saved question. |
| `DELETE` | `/api/questions/{question_id}` | Cookie | Delete a saved question. |
| `GET` | `/api/health` | Public | Check backend health. |

All browser-facing state-changing requests (`POST`, `PATCH`, `PUT`, and `DELETE`) must include an `Origin` matching a configured trusted origin. Missing or untrusted origins are rejected. Authenticated endpoints use the cookie; the API does not require an `Authorization: Bearer` header.

### Request and response shapes

Registration and login accept:

```json
{
  "email": "learner@example.com",
  "password": "replace-with-a-password"
}
```

A successful login returns a public profile and sets the cookie; it does not return the JWT:

```json
{
  "id": "665f00000000000000000001",
  "email": "learner@example.com"
}
```

`POST /api/topics/suggest` accepts `{"subject":"React.js"}` and responds with:

```json
{
  "topics": ["Hooks", "Components", "Props", "State Management", "Routing"]
}
```

`POST /api/questions/generate` accepts:

```json
{
  "subject": "React.js",
  "topic": "Hooks",
  "difficulty": "Medium",
  "count": 1
}
```

It responds with a draft (no database IDs):

```json
{
  "questions": [
    {
      "question_text": "Which Hook is used to store state in a function component?",
      "options": ["useState", "useMemo", "useRef", "useEffect"],
      "correct_option_index": 0,
      "explanation": "useState adds state to a function component and returns the current value and an update function."
    }
  ]
}
```

`POST /api/questions/bulk` accepts a reviewed batch:

```json
{
  "questions": [
    {
      "subject": "React.js",
      "topic": "Hooks",
      "difficulty": "Medium",
      "question_text": "Which Hook is used to store state in a function component?",
      "options": ["useState", "useMemo", "useRef", "useEffect"],
      "correct_option_index": 0,
      "explanation": "useState adds state to a function component."
    }
  ]
}
```

The response contains the saved question objects, including `id`, `created_at`, and `updated_at`:

```json
{
  "items": [
    {
      "id": "665f00000000000000000002",
      "subject": "React.js",
      "topic": "Hooks",
      "difficulty": "Medium",
      "question_text": "Which Hook is used to store state in a function component?",
      "options": ["useState", "useMemo", "useRef", "useEffect"],
      "correct_option_index": 0,
      "explanation": "useState adds state to a function component.",
      "created_at": "2025-01-15T12:00:00Z",
      "updated_at": "2025-01-15T12:00:00Z"
    }
  ]
}
```

`GET /api/questions` returns `items`, `total`, `page`, and `page_size`. The list endpoint supports `search`, `subject`, `topic`, `difficulty`, `page`, and `page_size`. For example:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 10
}
```

`GET /api/questions/filter-options` returns `{"subjects":["React.js"],"topics":["Hooks"]}`. `PATCH /api/questions/{question_id}` accepts one or more question fields, including subject and topic at the API level; the current edit dialog does not expose subject or topic for editing. For example, the API accepts `{"difficulty":"Hard","explanation":"Updated explanation."}`. `DELETE` returns no response body on success.

### PowerShell `curl.exe` examples

These examples assume the backend is at `http://localhost:8000`. Use an account you have registered. The cookie jar is stored in the Windows temporary directory. Include the trusted `Origin` on every state-changing request.

```powershell
$cookieJar = Join-Path $env:TEMP 'ai-assessment-cookies.txt'

# Register once; omit if the account already exists.
curl.exe -i -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' --data-raw '{"email":"learner@example.com","password":"replace-with-a-password"}' http://localhost:8000/api/auth/register

# Login and save the HttpOnly cookie.
curl.exe -i -c $cookieJar -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' --data-raw '{"email":"learner@example.com","password":"replace-with-a-password"}' http://localhost:8000/api/auth/login

# Read the current user using the cookie.
curl.exe -i -b $cookieJar http://localhost:8000/api/auth/me

# Suggest topics.
curl.exe -i -b $cookieJar -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' --data-raw '{"subject":"React.js"}' http://localhost:8000/api/topics/suggest

# Generate one draft question; generation does not save it.
curl.exe -i -b $cookieJar -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' --data-raw '{"subject":"React.js","topic":"Hooks","difficulty":"Medium","count":1}' http://localhost:8000/api/questions/generate

# Save a reviewed batch.
curl.exe -i -b $cookieJar -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' --data-raw '{"questions":[{"subject":"React.js","topic":"Hooks","difficulty":"Medium","question_text":"Which Hook stores state in a function component?","options":["useState","useMemo","useRef","useEffect"],"correct_option_index":0,"explanation":"useState adds state to a function component."}]}' http://localhost:8000/api/questions/bulk

# List saved questions with all server-side filters and pagination.
curl.exe -i -b $cookieJar "http://localhost:8000/api/questions?search=state&subject=React.js&topic=Hooks&difficulty=Medium&page=1&page_size=10"

# Retrieve filter values for a subject.
curl.exe -i -b $cookieJar "http://localhost:8000/api/questions/filter-options?subject=React.js"

# Edit, then delete a saved question (replace the ID with one returned by bulk save).
curl.exe -i -b $cookieJar -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' -X PATCH --data-raw '{"difficulty":"Hard"}' http://localhost:8000/api/questions/665f00000000000000000002
curl.exe -i -b $cookieJar -H 'Origin: http://localhost:5173' -X DELETE http://localhost:8000/api/questions/665f00000000000000000002

# Logout and update the cookie jar with the expired cookie.
curl.exe -i -b $cookieJar -c $cookieJar -H 'Origin: http://localhost:5173' -X POST http://localhost:8000/api/auth/logout
```

## AI integration

Gemini drafts and their request flow, prompt templates, structured-output schemas, validation, error handling, environment variables, and verification limits are covered in [docs/AI_INTEGRATION.md](docs/AI_INTEGRATION.md). Structural validity does not establish factual correctness; review questions and answer keys before saving.

## Validation and error handling

| Input | Constraint |
| --- | --- |
| Subject and topic | Non-empty, up to 160 characters. |
| Difficulty | `Easy`, `Medium`, or `Hard`. |
| Generation count | Whole number from 1 to 30. |
| Saved batch size | 1 through 30 questions. |
| Question text | Non-empty, up to 2,000 characters. |
| Options | Exactly four distinct, non-empty strings, each up to 500 characters. |
| Correct answer | Integer index from 0 through 3. |
| Explanation | Non-empty, up to 4,000 characters. |
| Search and pagination | Search text up to 120 characters; page is at least 1 and page size is 1 through 100. |
| Account credentials | Valid email address; password from 8 through 128 characters. |

FastAPI returns request validation errors in the API's error format. Known Gemini failures are mapped to safe client-facing messages: missing configuration is reported as a service/configuration error, quota or rate limits as a usage-limit error, timeouts as a timeout, and provider or malformed/incomplete responses as generation failures. A 429 quota response is not retried. After the two retries for a 503 are exhausted, the API returns “The AI service is temporarily busy. Please wait a moment and try again.” Provider status codes are logged without logging provider response bodies or credentials. An unexpected non-provider SDK exception may still result in a generic server error.

The React UI shows action-specific feedback and pending states. A failed generation or Save All does not intentionally discard the current draft. A failed edit leaves the form values available for retry. An initial `/api/auth/me` 401 restores signed-out state; a protected request's 401 expires an existing session. Network errors are distinct from session expiry.

## Security

- Passwords are hashed with Argon2; plaintext passwords are not stored.
- Login sets a short-lived JWT in an HttpOnly cookie and returns only the public user profile. The cookie uses `Path=/` and `SameSite=Lax`; its lifetime follows the JWT expiry. `Secure` is enabled in production and can be explicitly configured for HTTPS deployments.
- JWTs are signed and verified with the configured algorithm (`HS256` by default). Protected requests validate the token and load the user record from MongoDB.
- CORS allows configured exact frontend origins with credentials. Browser-facing state-changing API routes—including login and logout—check the request `Origin` against trusted origins.
- Topic and question routes require authentication. Saved-question reads, edits, and deletes are scoped to the current user's ID.
- The Gemini API key is read by the backend only. Do not prefix it with `VITE_`, place it in frontend files, or expose it in logs.

For production, use HTTPS, a strong unique JWT secret, the correct trusted frontend origin(s), and secure cookie settings. Keep frontend and backend hostnames aligned when relying on `SameSite=Lax`.

## Checks and tests

Run backend checks from `backend/` with the virtual environment activated:

```powershell
python -m compileall -q app tests
python -m pytest -q
```

The test suite mocks Gemini for automated checks. The MongoDB integration test needs a reachable replica set and a disposable test database configured with `MONGO_TEST_URI`; it skips when MongoDB is unavailable.

Run the frontend production build from `frontend/`:

```powershell
npm ci
npm run build
```

Available frontend scripts are `dev`, `build`, and `preview`. No frontend lint, type-check, or test script is configured in `package.json`. There is no separate backend lint or type-check command configured.

During the latest retry-handling update, the backend syntax check passed and tests reported **30 passed, 1 skipped** (the MongoDB integration test); the frontend production build passed. A browser smoke test with intercepted API responses confirmed duplicate-submit guards, pending feedback, and draft preservation. No live Gemini request was verified after the timeout/schema changes. Live MongoDB persistence and full authenticated browser workflows require the configured services and should be tested in the target environment.

## AI-assisted development documentation

The detailed seven-question AI usage report is in [docs/AI Assisted Development Report.pdf](<docs/AI Assisted Development Report.pdf>). It distinguishes implemented protections and checks from live Gemini or manual accuracy checks that were not verified.

## Known limitations and items to confirm

- Python and Node versions are not pinned by project-level runtime declarations. The versions above describe source/dependency compatibility, not a formal support matrix.
- The frontend has no `.env.example`; the current local API URL works through the Axios default.
- Automated checks do not prove Gemini's factual accuracy. Manual review remains necessary.
- No live Gemini request was verified after the schema and 10-second timeout changes; the MongoDB replica-set integration test was skipped because a test database was unavailable.
- No frontend lint, type-check, or automated test script is configured.
- No manual factual accuracy review of generated questions is documented in the available development history.
