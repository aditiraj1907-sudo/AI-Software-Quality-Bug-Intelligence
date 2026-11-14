# Quality & Bug Intelligence

An AI-powered platform that analyzes source code, finds common errors and quality issues, classifies each bug by category, predicts how severe it is with machine learning, explains the problem with a suggested fix, and produces a quality report and a monitoring dashboard.

It supports **JavaScript** and **Python** code.

## Project structure

```
bug-intelligence/
├── frontend/                 Web pages (HTML, CSS, JavaScript). No build step.
│   ├── index.html            Home
│   ├── analyzer.html         Paste code, get findings
│   ├── dashboard.html        Issues across the project
│   ├── predictor.html        Severity and category from a bug description
│   ├── report.html           Quality report
│   ├── how-it-works.html     Stages, rules and model scores
│   ├── css/style.css
│   └── js/
│       ├── config.js         Backend address (empty = same server)
│       ├── api.js            Calls to the backend
│       ├── common.js         Shared helpers (charts, formatting, Markdown)
│       └── pages/            One script per page
│
├── backend/                  Python API (FastAPI)
│   ├── main.py               Routes
│   ├── service.py            Application logic
│   ├── schemas.py            Request validation
│   ├── report.py             Builds the Markdown report
│   ├── analyzer/             Code analysis engine
│   │   ├── parsing.py        Strips strings/comments, finds blocks, detects language
│   │   ├── rules.py          The 27 detection rules
│   │   └── engine.py         Runs rules, scores files
│   └── samples/              The five example files
│
├── ml/                       Machine learning (scikit-learn)
│   ├── data/bug_reports.csv  Labelled bug reports (text, category, severity)
│   ├── train.py              Trains and cross-validates the models
│   ├── model.py              Loads the models and makes predictions
│   └── models/               Saved models (created on first run)
│
├── database/                 SQLite
│   ├── schema.sql            Tables: files, findings, scans
│   └── db.py                 All SQL queries
│
└── tests/                    pytest tests for the analyzer, the ML and the API
```

## Run it

You need Python 3.10 or newer.

**Windows**

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

**macOS / Linux**

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Then open **http://127.0.0.1:8000**. The same server provides the API and the web pages.

The first start trains the ML models (about a second), creates the database, and fills it with a five-file sample project. After that, anything you add on the Analyzer page is saved in `database/bug_intelligence.db`.

Interactive API documentation is at http://127.0.0.1:8000/docs.

## How the parts fit together

```
 Browser (frontend)  ──HTTP/JSON──▶  FastAPI (backend)  ──▶  analyzer rules ──▶ findings
                                          │                         │
                                          │                         ▼
                                          │                  ml/model.py: predicts severity
                                          ▼
                                   database/db.py ──▶ SQLite (files, findings, scans)
```

1. **Parse.** `parsing.py` blanks out strings and comments and finds where functions and blocks end.
2. **Detect.** Each rule in `rules.py` looks for one pattern, such as `eval`, SQL built from strings, an off-by-one loop, or an empty `catch`.
3. **Classify.** Every rule belongs to a category: Security, Logic, Error handling, Performance, Resource management, Code quality or Maintainability.
4. **Predict.** The severity model reads the rule's description and returns a probability for critical, high, medium and low. That is blended 70/30 with the rule's default severity, and a 0 to 100 risk score is computed from the probabilities.
5. **Explain and report.** Every finding carries a reason and a suggested fix. Results are stored in SQLite, and the dashboard and report read from there.

## API

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/api/analyze` | Analyze code without saving it |
| GET | `/api/project` | Files, statistics and score history |
| POST | `/api/project/files` | Analyze code and add it to the project |
| DELETE | `/api/project/files/{id}` | Remove a file and its findings |
| POST | `/api/project/reset` | Restore the sample project |
| GET | `/api/findings` | List issues; filter with `severity`, `category`, `file` |
| GET | `/api/report` | The quality report as Markdown |
| POST | `/api/predict` | Severity and category of a bug description |
| GET | `/api/rules` | The detection rules with their predicted severity |
| GET | `/api/model` | Training set size and cross-validated scores |
| GET | `/api/samples` | The sample files |
| GET | `/api/health` | Status check |

## Machine learning

Two models, both TF-IDF (single words and word pairs) with logistic regression:

* **Severity:** bug report text → critical, high, medium or low
* **Category:** bug report text → one of the seven categories

They are trained on `ml/data/bug_reports.csv` (101 short, hand-written bug reports). Scores come from 5-fold cross-validation, where each report is predicted by a model that did not train on it:

| Model | Accuracy | Macro F1 | Random guessing |
| --- | --- | --- | --- |
| Severity (4 classes) | about 41% | 0.40 | 25% |
| Category (7 classes) | about 56% | 0.51 | 14% |

These are modest, and the page says so. 101 examples is a small set, and severity labels are partly a matter of opinion. The model is a triage hint, not a verdict. To improve it, add rows to the CSV and run:

```
python -m ml.train
```

This prints the new scores and saves the models. The backend also retrains by itself if the saved models are missing, are older than the CSV, or cannot be loaded.

## Database

SQLite file at `database/bug_intelligence.db` (created automatically). Set the environment variable `QBI_DB` to use a different path.

* `files` holds each analyzed file with its score.
* `findings` holds each issue, linked to its file. Deleting a file deletes its findings.
* `scans` holds a quality snapshot after every change to the project, which feeds the trend chart.

The project is shared by everyone who opens the server. There are no user accounts.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover the analyzer rules and scoring, the ML models, and every API route against a temporary database.

## Hosting

GitHub stores the code. **GitHub Pages can only host static files**, so it can serve the `frontend/` folder but cannot run the Python backend. To put the whole site online, deploy the backend on a host that runs Python (for example Render, Railway or PythonAnywhere), then:

1. Set `window.QBI_API_BASE` in `frontend/js/config.js` to the backend's address.
2. Start the backend with the environment variable `QBI_CORS` set to your Pages address, for example `https://your-name.github.io`.

For a demo or a viva, running it on your own computer as described above is enough.

## Limits

* Detection is pattern-based, not a full parser. It can miss bugs and can flag code that is fine.
* Only JavaScript and Python are supported, one file or snippet at a time, up to 200,000 characters.
* Explanations come from a built-in text for each rule. They are not generated by a language model.
* Uploaded code is only read and matched against patterns. It is never executed.

## Add a rule

Add a `Rule(...)` to the list in `backend/analyzer/rules.py` with an id, language, category, default severity, a short description for the ML model, a reason, a fix and a test function. Then add a case to `tests/test_analyzer.py`.
