# AI-Assisted Development Report

**Project:** AI Assessment Generator  
**Developer:** Durai Raja  
**Default Gemini model:** `gemini-3.5-flash-lite`

## 1. Which AI tools did I use?

- **GitHub Copilot:** The available development record is a Copilot SDK session in VS Code. I used the assistant for implementation support, debugging, code cleanup, and documentation work.
- **ChatGPT:** I used ChatGPT for planning, explanations, prompt refinement, and code review.
- **Google Gemini:** The application uses the official `google-genai` SDK on the FastAPI backend to suggest topics and generate question drafts. The configured default model is `gemini-3.5-flash-lite`; this is the application's runtime provider, separate from development assistance.

## 2. What tasks did I use AI for?

I used AI assistance across the React frontend and FastAPI backend: refining the interface and form feedback, debugging the question-edit dialog's focus behavior, organizing frontend pages and services, adding cookie-based authentication, and implementing Gemini topic and question generation.

I also used it to review server-side question search, filters, pagination, and batch saving; investigate a Gemini schema error; simplify backend code; remove unused frontend code; and prepare project documentation. These tasks are reflected in the conversation and the current application structure. Requests for live Gemini generation and broader browser checks were not themselves evidence that those checks were completed.

## 3. Representative prompts

The excerpts below are taken or paraphrased from my development requests. Longer prompts are labeled as paraphrases.

1. **Frontend bug fix — representative excerpt:** “In the question edit modal, typing one character makes the input lose focus. Find the cause, keep the dialog and inputs mounted, and verify editing from both the draft table and All Questions.”  
   **Purpose:** Diagnose and fix the edit workflow while preserving its behavior.

2. **Gemini integration — representative paraphrase:** Integrate the official `google-genai` SDK into the existing FastAPI generation flow, request structured JSON for topics and MCQs, validate responses with Pydantic, and keep generation as a draft until Save All.  
   **Purpose:** Replace mock generation without changing the existing frontend API contract or persistence workflow.

3. **Authentication — representative paraphrase:** Move the JWT from browser storage into an HttpOnly cookie, restore the session through `/api/auth/me`, and protect state-changing routes with trusted-origin checks.  
   **Purpose:** Update React and FastAPI authentication together while retaining existing protected routes.

4. **Backend cleanup — representative paraphrase:** Remove unused code and simplify redundant backend implementation, but preserve authentication, Gemini validation, user-scoped question operations, and transactional batch saving.  
   **Purpose:** Increase the backend code quality without changing its required behavior.

## 4. What did I modify after receiving AI-generated output?

I asked for a simpler implementation when earlier approaches seemed more complex than needed. The resulting code keeps the existing project structure and API flow rather than adding unnecessary layers.

Implemented decisions visible in the current project include:

- Generated questions stay in a React draft until I review them and select **Save All**. The backend validates the submitted batch before persisting it.
- Search, metadata filters, and pagination run in FastAPI/MongoDB rather than only filtering the currently loaded browser rows.
- Generation prompts separate user-provided subject and topic values from instructions. The backend requests structured JSON and validates it before returning a draft.
- React authentication stores the user profile/status in Redux and sends the JWT as an HttpOnly cookie; it no longer sends a bearer token from browser storage.
- The frontend uses separate pages, reusable components, routes, API configuration, and endpoint service modules.
- Backend validation and question operations were simplified while preserving the authenticated user's data scope.

The implementation does not prove that every requested live or manual check was performed. Live Gemini compatibility and manual factual review remain unverified; see Sections 5 and 6.

## 5. Incorrect or unsuitable AI responses

An earlier proposed implementation was more elaborate than I wanted, so I asked for simpler code that would be easier to explain in an interview.

During Gemini integration, a topic-generation request returned `400 INVALID_ARGUMENT`: the provider rejected an `additional_properties` field in the response schema. The current generator builds its response schema from Pydantic and removes `minLength` and `maxLength`. No successful live Gemini request after that schema change was verified, so resolution of this specific provider error remains unverified.

After the retry change, Gemini also rejected the configured 7-second deadline with `INVALID_ARGUMENT`, stating that the minimum allowed deadline is 10 seconds. I raised the per-attempt timeout to 10 seconds, set the backend overall deadline to 35 seconds, and aligned the frontend Axios timeout to 40 seconds. Automated checks cover the timeout configuration, but no live request verified the provider accepts the updated deadline. No manual factual review of generated questions is documented in the available development history.

I kept retries in one layer by setting the SDK to one attempt and handling 503 retries in the application: two retries after the initial call, with 250 ms then 500 ms delays and up to 200 ms jitter per delay. Exhaustion returns the specified temporary-busy 503 message. Quota errors are not retried, timeouts remain distinct, and the backend logs provider status codes without printing provider responses.

## 6. How did I validate generated questions?

The FastAPI generation module configures Gemini with `response_mime_type="application/json"` and a response schema derived from the Pydantic response models. It asks for five distinct topics or the exact requested question count, with four plausible options, one correct answer, and a supporting explanation.

Before a generated draft is returned, Pydantic checks the response shape and required text. Options are trimmed and must be four distinct, non-empty values. `correct_option_index` must be a strict integer from 0 to 3. The generation code also compares the returned number of questions with the requested count and rejects a mismatch.

The **Save All** endpoint independently validates the reviewed batch before inserting records. The saved-question update endpoint validates the merged question as well, so an edit cannot leave the stored question with invalid options or answer index.

These are structural checks, not a guarantee that an answer is factually correct. No manual accuracy review is documented in the available development history.

## 7. Security considerations

- The Gemini API key is loaded by the backend from environment configuration and represented as a secret value. It is not needed in React or exposed in the frontend.
- Passwords are hashed with Argon2 before they are stored.
- The backend signs JWTs with the configured algorithm and verifies the signature, `sub`, and `exp` before loading the user from MongoDB.
- Login sets the JWT in an HttpOnly cookie with `Path=/` and `SameSite=Lax`; the cookie lifetime follows JWT expiry. `Secure` is enabled for production or when explicitly configured.
- FastAPI checks the request `Origin` against configured trusted origins on state-changing API routes, including login and logout. CORS is configured for exact allowed origins with credentials.
- Saved-question list, edit, and delete queries include the authenticated user's ID.
- Known Gemini quota, timeout, provider, and invalid-response failures are mapped to safe API messages rather than returning raw provider response content. Provider status codes are logged without logging credentials or response bodies; an unexpected SDK exception may still produce a generic server error.

These statements describe protections present in the inspected code; they do not replace deployment review or testing with production configuration.
