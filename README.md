# 🗄️ SQL Query Generator — AI

A web app that converts natural language questions into SQL queries using **Claude AI**, then executes them on a live SQLite database.

## Features

- Ask questions in plain English (Polish or English) — get instant SQL
- Editable SQL before execution — tweak if needed
- Live results table with row count and execution time
- Interactive database schema explorer
- 12 built-in example queries to get started
- Query history — click to re-run previous queries
- Only SELECT queries allowed — safe by design

## Demo Database

Includes a realistic **clinical trials** SQLite database with:

| Table | Description |
|---|---|
| `patients` | 15 patients across 6 European countries |
| `trials` | 4 clinical trials (Phase I–IV) |
| `enrollments` | Patient-trial assignments with arms |
| `adverse_events` | 10 adverse events with severity levels |
| `measurements` | Biomarker readings per visit |
| `sites` | 5 investigational sites |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask |
| Database | SQLite (built-in, zero config) |
| AI | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Frontend | Vanilla HTML · CSS · JavaScript |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/szmsk/sql-query-gen.git
cd sql-query-gen

# 2. Install
pip install -r requirements.txt

# 3. Run
python server.py

# 4. Open browser
# http://localhost:5000
```

Get an API key at [console.anthropic.com](https://console.anthropic.com) — first $5 free.

## Example Questions

- *"How many patients are enrolled in each trial?"*
- *"Show all patients who had severe adverse events"*
- *"What is the average haemoglobin level per trial?"*
- *"List trials by phase and current status"*
- *"Which patients have completed their trial?"*

## How It Works

```
User question (natural language)
        ↓
Database schema sent to Claude as context
        ↓
Claude generates SQLite SELECT query
        ↓
Query displayed in editable editor
        ↓
User runs query → Flask executes on SQLite
        ↓
Results displayed as formatted table
```

## Project Structure

```
sql-query-gen/
├── server.py           # Flask backend + SQLite + Claude API
├── requirements.txt    # Python dependencies
├── public/
│   ├── index.html      # App UI
│   ├── style.css       # Styles
│   └── app.js          # Frontend logic
└── README.md
```

## Author

Built by **Szymon Kloskowski**

**Contact:** kloskowskiszymon@wp.pl
**GitHub:** [github.com/szmsk](https://github.com/szmsk)
**LinkedIn:** [linkedin.com/in/szymon-kloskowski](https://linkedin.com/in/szymon-kloskowski)

## License

MIT
