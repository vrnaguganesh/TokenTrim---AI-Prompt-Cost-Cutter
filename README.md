# ✂ TokenTrim - AI Prompt Cost Cutter

An AI-based middleware and plugin suite designed to reduce LLM API costs by removing unnecessary, redundant, and filler information from prompts before sending them to models like Gemini, GPT, and Claude. It leverages lightweight NLP algorithms to shrink token payloads while protecting technical structures (such as code blocks, variables, URLs, and custom entities).

## ML training pipeline

The ML service combines `zai-org/BPO` with
`Sudhendra/semantic-compression-sft`. Records are normalized to prompt pairs,
measured with `cl100k_base`, validated with sentence-transformer cosine
similarity, and split deterministically into 80% training, 10% validation, and
10% test data. Compression is accepted only when semantic and safety checks
pass; similarity is a validation signal, not a substitute for human review.

From `ml-service` in a clean Python environment:

```bash
pip install -r requirements.txt
python training/download_dataset.py
python training/preprocess.py
python training/train.py
python training/evaluate.py
```

The processed dataset is written to
`ml-service/data/processed/tokentrim_semantic_compression.csv`, the split CSVs
to `ml-service/data/splits/`, model artifacts to `ml-service/models/`, and
evaluation reports to `ml-service/reports/`. Estimated costs are calculated
only at serving time from the configurable prices in `config/models.json`.

## Production request flow

The extension talks only to the Node API (`/api/v1/optimize`). The Node API
forwards requests to the private FastAPI `POST /internal/optimize` endpoint and
returns the validated result. The Python service also exposes `/health`,
`/ready`, and `/model-info`. If the API, model, tokenizer, or validation fails,
the extension keeps the original prompt and displays an unavailable/rejected
status instead of blocking the underlying AI site.

For local development, copy `.env.example` to the appropriate service
environment and start the ML service before the backend:

```bash
docker compose up --build
```

The ML service is not published as a host port by Compose; only the Node API is
publicly exposed. Set `ML_INTERNAL_TOKEN` to the same non-secret development or
deployment value in both services when enabling internal authentication.

---

## 📂 Project Structure

```bash
📂 TokenTrim/
├── 📄 index.html             # Premium interactive playground dashboard
├── 📄 styles.css             # Cyberpunk glassmorphic design theme stylesheet
├── 📄 app.js                 # Local browser NLP engine and playground logic
├── 📄 README.md              # Project documentation
│
├── 📂 middleware/            # Developer SDK integrations
│   ├── 📂 node/
│   │   ├── 📄 tokentrim.js  # Node.js prompt-compression engine
│   │   └── 📄 example.js     # Express.js middleware integration example
│   └── 📂 python/
│       ├── 📄 tokentrim.py  # Python prompt-compression engine
│       └── 📄 example.py     # FastAPI middleware integration example
│
└── 📂 extension/             # Browser Plugins
    ├── 📄 manifest.json      # Chrome Manifest V3 configuration
    ├── 📄 popup.html         # Extension popup UI
    ├── 📄 popup.js           # Extension transmission trigger
    └── 📄 content.js         # Chat portal script injection (ChatGPT/Claude/Gemini)
```

---

## ⚡ Key Features

1. **Local NLP Prompt Compression**:
   - **Filler & Politeness Pruning**: Automatically scrubs conversational padding like *"please note that"*, *"in order to"*, or *"can you please"* which inflate token counts.
   - **Redundancy Filter**: Computes Jaccard Similarity of sentence tokens in a sliding window to prune duplicate information clauses (common in web scrapes or RAG database context dumps).
   - **Aggressive Stopwords Strip**: An optional high-compression mode that eliminates structural noise without breaking readability.
2. **Context Safeguards**:
   - Auto-detects and isolates Markdown code blocks (```` ``` ````), inline code (`` ` ``), URLs, email addresses, and capitalized proper nouns/entities using a placeholder translation layer, ensuring technical strings are never corrupted.
3. **Pluggable Integration**:
   - Ready-to-go Express (Node.js) middleware and FastAPI (Python) SDK scripts.
   - Self-contained Google Chrome extension to optimize prompts directly in ChatGPT, Gemini, and Claude web chat interface inputs.

---

## 🚀 Getting Started

### 1. Launching the Playground Dashboard
Simply double-click the **`index.html`** file in Chrome, Edge, or Firefox browser to open the TokenTrim Interactive Dashboard.
- Paste any prompt (or load one of the presets) into the original text box.
- Customize aggression parameters and select your target LLM (e.g. GPT-4o, Gemini 1.5 Pro).
- Click **Compress Context** to inspect the live token savings, calculated cost reductions, speedup indices, and word-by-word differences.

### 2. Running the Node.js Express Middleware
Ensure Node.js is installed, navigate to `middleware/node` and run:
```bash
# Install Express
npm install express

# Start the mock gateway server
node example.js
```
Make a `POST` request to `http://localhost:3000/v1/chat/completions` with a payload of `{ "prompt": "..." }` to view compressed responses.

### 3. Running the Python FastAPI Middleware
Ensure Python is installed along with FastAPI and Uvicorn, navigate to `middleware/python` and run:
```bash
# Install dependencies
pip install fastapi uvicorn

# Start the mock gateway API
python example.py
```
View the interactive docs at `http://127.0.0.1:8000/docs`.

### 4. Loading the Chrome Extension
1. Open Google Chrome and go to `chrome://extensions/`.
2. Toggle **Developer mode** in the top-right corner to **ON**.
3. Click the **Load unpacked** button in the top-left corner.
4. Navigate and select the **`extension`** folder inside this project.
5. Refresh your chat page (ChatGPT, Gemini, or Claude). Write a prompt, click the TokenTrim extension icon in the toolbar, select settings, and click **Compress Input**!
