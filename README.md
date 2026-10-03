# Smart Study Notes Generator

A small Python web app that turns a paragraph into a concise summary and 3–5 study points using OpenAI's chat completions API. It also counts the original and summary words and calculates the percentage reduction.

## Run locally

1. Use Python 3.10 or newer.
2. Install the dependencies: `pip install -r requirements.txt`
3. Create a `.env` file in the project root (next to `app.py`) using `.env.example` as a template, then set your API key in it:

   ```env
   OPENAI_API_KEY=your-api-key
   OPENAI_MODEL=gpt-4o-mini
   ```

4. Start the app:

   ```powershell
   uvicorn app:app --reload
   ```

5. Open `http://127.0.0.1:8000`.

You can enter any paragraph of your own in the text box; the subject buttons only insert optional examples. The app reads `.env` for local development and environment variables on Vercel. Never put an API key in `index.html`, commit `.env`, or send the key in chat.

## Deploy to Vercel

1. Push this project to a GitHub repository and import it in Vercel, or deploy it with the Vercel CLI.
2. In **Vercel → Project → Settings → Environment Variables**, add `OPENAI_API_KEY` with your API key. Select the environments you want to use (at least **Production**; also **Preview** if needed).
3. Optionally add `OPENAI_MODEL` if you want to select a different model.
4. Save the variables and redeploy. Environment variable changes take effect on new deployments, not deployments already running.
5. Open the deployment URL, enter your own text in the paragraph box, and select **Generate study notes**.

The key must belong to an OpenAI project with API access and available usage/billing. A `401` means the key was rejected; a `429` usually means a usage or rate limit; a missing key returns a clear configuration error. The Vercel account, project permissions, and API key are user-provided; this source project does not contain deployment credentials.

## How the project files connect

1. `requirements.txt` installs FastAPI, Uvicorn, and dotenv.
2. Vercel detects the FastAPI app named `app` in `app.py`; locally, `uvicorn app:app` starts the same app.
3. `app.py` serves `index.html` at `/` and exposes `POST /api/generate`.
4. `index.html` sends the user's paragraph to `/api/generate` and displays the returned summary, key points, and counts.
5. For each request, `app.py` reads `OPENAI_API_KEY` and sends the paragraph to OpenAI; the key remains on the server.
6. `test_app.py` imports `app.py` and tests the user-input, OpenAI request, error handling, and word-count flow.
7. `.env.example` documents local settings; `.gitignore` and `.vercelignore` exclude the real `.env` file. `vercel.json` configures the Python function.

Keep these files in the same project root so the local server and Vercel can resolve the entrypoint, HTML page, dependencies, and deployment configuration.

## Test

Run the unit tests with:

```powershell
python -m unittest -v
```

The three metric cases below are recorded using deterministic sample summaries so that word counts and reduction calculations can be checked without an API key. The model-backed response parsing is also tested with a mocked API response. Actual AI wording varies by model and API response.

| Test paragraph | Summary and key points (deterministic test fixture) | Original words | Summary words | Reduction |
| --- | --- | ---: | ---: | ---: |
| Plants use sunlight to convert water and carbon dioxide into glucose, releasing oxygen. | **Summary:** Plants use sunlight to make glucose from water and carbon dioxide.<br>**Key points:** Plants use light energy to create glucose; water and carbon dioxide are raw materials; oxygen is released. | 13 | 11 | 15.4% |
| The printing press made books cheaper and faster to produce, spreading literacy and new ideas throughout Europe. | **Summary:** The printing press lowered book costs and helped ideas and literacy spread.<br>**Key points:** Movable type made book production faster; books became cheaper and more available; literacy and ideas spread more widely. | 17 | 12 | 29.4% |
| Burning fossil fuels increases greenhouse gases, trapping more heat and contributing to rising temperatures and changing weather. | **Summary:** Fossil fuel emissions trap heat, driving global warming and weather changes.<br>**Key points:** Fossil fuels add greenhouse gases; more heat is trapped in the atmosphere; temperatures and weather patterns are affected. | 17 | 11 | 35.3% |

### Observation

The sample summaries and key points keep the central idea of each paragraph and read coherently, while the reduction varies with how much detail is retained. These examples validate the word-count, percentage, and result-format calculations; they are deterministic test fixtures, not live model output. For a true relevance and coherence assessment of the AI-generated notes, run the three built-in Biology, History, and Climate paragraphs with `OPENAI_API_KEY` configured and compare each result with its source. AI-generated notes can omit nuance or contain mistakes, so verify important details against the original text.
