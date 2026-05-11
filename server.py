"""
SQL Query Generator — Backend Server
Natural language → SQL using Claude API, executed on SQLite demo database
"""

import os
import io
import json
import sqlite3
import re
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

DB_PATH = 'demo.db'


# ── Demo database setup ───────────────────────────────────────────────────────

def init_db():
    """Create a realistic clinical/pharma demo database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS patients (
        id          INTEGER PRIMARY KEY,
        first_name  TEXT NOT NULL,
        last_name   TEXT NOT NULL,
        birth_date  TEXT NOT NULL,
        gender      TEXT CHECK(gender IN ('M','F','Other')),
        country     TEXT,
        enrolled_at TEXT,
        status      TEXT CHECK(status IN ('Active','Completed','Withdrawn','Screening'))
    );

    CREATE TABLE IF NOT EXISTS trials (
        id           INTEGER PRIMARY KEY,
        trial_code   TEXT UNIQUE NOT NULL,
        title        TEXT NOT NULL,
        phase        TEXT CHECK(phase IN ('I','II','III','IV')),
        status       TEXT CHECK(status IN ('Recruiting','Active','Completed','Terminated')),
        sponsor      TEXT,
        start_date   TEXT,
        end_date     TEXT,
        target_n     INTEGER
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        id           INTEGER PRIMARY KEY,
        patient_id   INTEGER REFERENCES patients(id),
        trial_id     INTEGER REFERENCES trials(id),
        enrolled_at  TEXT,
        arm          TEXT,
        completed    INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS adverse_events (
        id           INTEGER PRIMARY KEY,
        patient_id   INTEGER REFERENCES patients(id),
        trial_id     INTEGER REFERENCES trials(id),
        event_date   TEXT,
        description  TEXT,
        severity     TEXT CHECK(severity IN ('Mild','Moderate','Severe','Life-threatening')),
        resolved     INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS measurements (
        id           INTEGER PRIMARY KEY,
        patient_id   INTEGER REFERENCES patients(id),
        trial_id     INTEGER REFERENCES trials(id),
        visit_date   TEXT,
        visit_num    INTEGER,
        biomarker    TEXT,
        value        REAL,
        unit         TEXT
    );

    CREATE TABLE IF NOT EXISTS sites (
        id           INTEGER PRIMARY KEY,
        name         TEXT NOT NULL,
        city         TEXT,
        country      TEXT,
        principal_investigator TEXT
    );
    """)

    # Seed data only if empty
    if c.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
        patients = [
            (1,'Anna','Kowalska','1978-03-15','F','Poland','2023-01-10','Active'),
            (2,'Jan','Nowak','1965-07-22','M','Poland','2023-01-15','Active'),
            (3,'Maria','Schmidt','1982-11-03','F','Germany','2023-02-01','Completed'),
            (4,'Hans','Müller','1990-05-17','M','Germany','2023-02-14','Active'),
            (5,'Sophie','Dubois','1975-09-28','F','France','2023-03-05','Withdrawn'),
            (6,'Pierre','Martin','1988-12-01','M','France','2023-03-20','Active'),
            (7,'Emma','Johnson','1995-04-11','F','UK','2023-04-02','Screening'),
            (8,'Oliver','Smith','1970-08-30','M','UK','2023-04-18','Active'),
            (9,'Lena','Berg','1983-01-25','F','Netherlands','2023-05-07','Completed'),
            (10,'Lars','Andersen','1977-06-19','M','Denmark','2023-05-22','Active'),
            (11,'Isabel','Garcia','1992-02-14','F','Spain','2023-06-10','Active'),
            (12,'Carlos','Lopez','1969-10-08','M','Spain','2023-06-25','Active'),
            (13,'Giulia','Rossi','1986-07-31','F','Italy','2023-07-14','Completed'),
            (14,'Marco','Ferrari','1980-03-22','M','Italy','2023-07-28','Active'),
            (15,'Mia','Larsson','1998-11-05','F','Sweden','2023-08-15','Screening'),
        ]
        c.executemany("INSERT OR IGNORE INTO patients VALUES (?,?,?,?,?,?,?,?)", patients)

        trials = [
            (1,'TRL-2023-A1','Phase II Study of Drug X in Advanced Oncology','II','Active','Pharma Corp A','2023-01-01','2025-12-31',120),
            (2,'TRL-2023-B2','Phase III Cardiovascular Outcomes Trial','III','Recruiting','Pharma Corp B','2023-03-01','2026-06-30',500),
            (3,'TRL-2022-C3','Phase I Safety and Tolerability Study','I','Completed','BioTech C','2022-06-01','2023-06-30',30),
            (4,'TRL-2024-D4','Phase IV Post-Marketing Surveillance Study','IV','Active','Pharma Corp D','2024-01-01','2026-12-31',1000),
        ]
        c.executemany("INSERT OR IGNORE INTO trials VALUES (?,?,?,?,?,?,?,?,?)", trials)

        enrollments = [
            (1,1,1,'2023-01-10','Treatment A',0),
            (2,2,1,'2023-01-15','Treatment B',0),
            (3,3,1,'2023-02-01','Treatment A',1),
            (4,4,2,'2023-02-14','Placebo',0),
            (5,5,2,'2023-03-05','Treatment A',0),
            (6,6,2,'2023-03-20','Treatment A',0),
            (7,7,3,'2023-04-02','Treatment A',0),
            (8,8,1,'2023-04-18','Treatment B',0),
            (9,9,1,'2023-05-07','Treatment A',1),
            (10,10,2,'2023-05-22','Placebo',0),
            (11,11,4,'2023-06-10','Treatment A',0),
            (12,12,4,'2023-06-25','Treatment B',0),
            (13,13,3,'2023-07-14','Treatment A',1),
            (14,14,2,'2023-07-28','Treatment A',0),
            (15,15,4,'2023-08-15','Placebo',0),
        ]
        c.executemany("INSERT OR IGNORE INTO enrollments VALUES (?,?,?,?,?,?)", enrollments)

        adverse_events = [
            (1,1,1,'2023-02-15','Nausea and vomiting','Mild',1),
            (2,2,1,'2023-03-01','Fatigue','Moderate',1),
            (3,3,1,'2023-03-10','Headache','Mild',1),
            (4,4,2,'2023-04-05','Elevated blood pressure','Moderate',0),
            (5,5,2,'2023-04-20','Dizziness','Mild',1),
            (6,6,2,'2023-05-15','Chest pain','Severe',0),
            (7,8,1,'2023-06-01','Skin rash','Mild',1),
            (8,9,1,'2023-06-20','Anaemia','Moderate',1),
            (9,11,4,'2023-07-10','Injection site reaction','Mild',1),
            (10,14,2,'2023-09-05','Dyspnoea','Severe',0),
        ]
        c.executemany("INSERT OR IGNORE INTO adverse_events VALUES (?,?,?,?,?,?,?)", adverse_events)

        measurements = [
            (1,1,1,'2023-01-10',1,'Haemoglobin',13.2,'g/dL'),
            (2,1,1,'2023-03-10',2,'Haemoglobin',12.8,'g/dL'),
            (3,2,1,'2023-01-15',1,'Haemoglobin',14.5,'g/dL'),
            (4,2,1,'2023-03-15',2,'Haemoglobin',13.9,'g/dL'),
            (5,3,1,'2023-02-01',1,'Tumour size',45.0,'mm'),
            (6,3,1,'2023-04-01',2,'Tumour size',38.0,'mm'),
            (7,4,2,'2023-02-14',1,'Systolic BP',145.0,'mmHg'),
            (8,4,2,'2023-04-14',2,'Systolic BP',138.0,'mmHg'),
            (9,6,2,'2023-03-20',1,'Systolic BP',152.0,'mmHg'),
            (10,6,2,'2023-05-20',2,'Systolic BP',141.0,'mmHg'),
            (11,9,1,'2023-05-07',1,'Haemoglobin',11.9,'g/dL'),
            (12,9,1,'2023-07-07',2,'Haemoglobin',12.6,'g/dL'),
            (13,11,4,'2023-06-10',1,'Weight',72.5,'kg'),
            (14,11,4,'2023-09-10',2,'Weight',71.8,'kg'),
            (15,14,2,'2023-07-28',1,'Systolic BP',148.0,'mmHg'),
        ]
        c.executemany("INSERT OR IGNORE INTO measurements VALUES (?,?,?,?,?,?,?,?)", measurements)

        sites = [
            (1,'University Hospital Warsaw','Warsaw','Poland','Dr. Anna Wiśniewska'),
            (2,'Charité Berlin','Berlin','Germany','Prof. Klaus Weber'),
            (3,'Hôpital Saint-Louis','Paris','France','Dr. Isabelle Dupont'),
            (4,'University College London Hospital','London','UK','Prof. James Mitchell'),
            (5,'Amsterdam UMC','Amsterdam','Netherlands','Dr. Eva van den Berg'),
        ]
        c.executemany("INSERT OR IGNORE INTO sites VALUES (?,?,?,?,?)", sites)

    conn.commit()
    conn.close()
    print("✅ Database initialised")


def get_schema() -> str:
    """Return the full database schema as a string for Claude."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in c.fetchall()]

    schema_parts = []
    for table in tables:
        c.execute(f"PRAGMA table_info({table})")
        cols = c.fetchall()
        col_defs = ", ".join(f"{col[1]} {col[2]}" for col in cols)
        c.execute(f"SELECT * FROM {table} LIMIT 2")
        sample = c.fetchall()
        schema_parts.append(f"TABLE {table} ({col_defs})\n  Sample: {sample}")

    conn.close()
    return "\n\n".join(schema_parts)


def execute_sql(query: str) -> dict:
    """Execute a SQL query safely and return results."""
    query = query.strip().rstrip(';')

    # Safety: only SELECT allowed
    if not re.match(r'^\s*SELECT\b', query, re.IGNORECASE):
        return {'error': 'Only SELECT queries are allowed for safety.'}

    # Block dangerous keywords
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
    if any(kw in query.upper() for kw in dangerous):
        return {'error': 'Destructive SQL statements are not allowed.'}

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        start = time.time()
        c.execute(query)
        rows = c.fetchmany(200)  # max 200 rows
        elapsed = round((time.time() - start) * 1000, 1)

        columns = [desc[0] for desc in c.description] if c.description else []
        data    = [dict(row) for row in rows]

        conn.close()
        return {
            'columns': columns,
            'rows':    data,
            'count':   len(data),
            'elapsed': elapsed,
        }
    except sqlite3.Error as e:
        return {'error': f'SQL Error: {str(e)}'}
    except Exception as e:
        return {'error': str(e)}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/api/schema', methods=['GET'])
def schema():
    """Return table names and column info for the frontend."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {}
    for (table,) in c.fetchall():
        c.execute(f"PRAGMA table_info({table})")
        cols = [{'name': r[1], 'type': r[2]} for r in c.fetchall()]
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        tables[table] = {'columns': cols, 'row_count': count}
    conn.close()
    return jsonify({'tables': tables})


@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate SQL from natural language using Claude."""
    data    = request.get_json()
    api_key = data.get('apiKey', '').strip()
    prompt  = data.get('prompt', '').strip()

    if not api_key:  return jsonify({'error': 'API key required'}), 400
    if not prompt:   return jsonify({'error': 'Question required'}), 400

    schema = get_schema()

    system = """You are an expert SQL engineer. Convert natural language questions to SQLite SELECT queries.

Rules:
- Output ONLY the raw SQL query — no explanation, no markdown, no backticks
- Only generate SELECT statements (never INSERT, UPDATE, DELETE, DROP)
- Use proper JOINs when data spans multiple tables
- Use aliases for readability
- Add ORDER BY where it makes sense
- Use LIMIT if the query could return very many rows (e.g. LIMIT 50)
- Column names and table names are case-sensitive — use exactly as in the schema
- Date columns are stored as TEXT in YYYY-MM-DD format"""

    user_msg = f"""DATABASE SCHEMA:
{schema}

USER QUESTION: {prompt}

Generate the SQL query:"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=400,
            system=system,
            messages=[{'role': 'user', 'content': user_msg}]
        )
        sql = msg.content[0].text.strip()
        # Strip markdown if Claude adds it anyway
        sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'^```\s*', '', sql)
        sql = re.sub(r'\s*```$', '', sql).strip()

        return jsonify({'sql': sql})

    except anthropic.AuthenticationError:
        return jsonify({'error': 'Invalid API key'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/execute', methods=['POST'])
def execute():
    """Execute a SQL query and return results."""
    data  = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    result = execute_sql(query)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok'})


# ── Boot ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("🗄️  SQL Query Generator running on http://localhost:5000")
    app.run(debug=False, port=5000)
