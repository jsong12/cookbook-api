import os, json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_conn():
    if DATABASE_URL:
        import psycopg2, psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        return conn, 'pg'
    else:
        import sqlite3
        conn = sqlite3.connect('/tmp/cookbook.db')
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

def init_db():
    conn, kind = get_conn()
    cur = conn.cursor()
    if kind == 'pg':
        cur.execute('''CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Other',
            cook_time TEXT,
            servings TEXT,
            difficulty TEXT DEFAULT 'Easy',
            ingredients TEXT,
            instructions TEXT,
            notes TEXT,
            photo_url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )''')
    else:
        cur.execute('''CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Other',
            cook_time TEXT,
            servings TEXT,
            difficulty TEXT DEFAULT 'Easy',
            ingredients TEXT,
            instructions TEXT,
            notes TEXT,
            photo_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    conn.commit()
    conn.close()

def row_to_dict(row, kind):
    if kind == 'pg':
        return dict(row)
    else:
        return dict(row)

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'db': 'postgres' if DATABASE_URL else 'sqlite'})

@app.route('/recipes', methods=['GET'])
def get_recipes():
    conn, kind = get_conn()
    cur = conn.cursor()
    if kind == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM recipes ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if 'created_at' in d and d['created_at']:
            d['created_at'] = str(d['created_at'])
        result.append(d)
    return jsonify(result)

@app.route('/recipes', methods=['POST'])
def add_recipe():
    d = request.json or {}
    conn, kind = get_conn()
    cur = conn.cursor()
    if kind == 'pg':
        import psycopg2.extras
        cur.execute('''INSERT INTO recipes (name,category,cook_time,servings,difficulty,ingredients,instructions,notes,photo_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
            (d.get('name'), d.get('category','Other'), d.get('cook_time',''),
             d.get('servings',''), d.get('difficulty','Easy'),
             d.get('ingredients',''), d.get('instructions',''),
             d.get('notes',''), d.get('photo_url','')))
        row = dict(cur.fetchone())
    else:
        cur.execute('''INSERT INTO recipes (name,category,cook_time,servings,difficulty,ingredients,instructions,notes,photo_url)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (d.get('name'), d.get('category','Other'), d.get('cook_time',''),
             d.get('servings',''), d.get('difficulty','Easy'),
             d.get('ingredients',''), d.get('instructions',''),
             d.get('notes',''), d.get('photo_url','')))
        cur.execute('SELECT * FROM recipes WHERE id=?', (cur.lastrowid,))
        row = dict(cur.fetchone())
    conn.commit()
    conn.close()
    if 'created_at' in row and row['created_at']:
        row['created_at'] = str(row['created_at'])
    return jsonify(row), 201

@app.route('/recipes/<int:rid>', methods=['PUT'])
def update_recipe(rid):
    d = request.json or {}
    conn, kind = get_conn()
    cur = conn.cursor()
    if kind == 'pg':
        import psycopg2.extras
        cur.execute('''UPDATE recipes SET name=%s,category=%s,cook_time=%s,servings=%s,
            difficulty=%s,ingredients=%s,instructions=%s,notes=%s,photo_url=%s WHERE id=%s RETURNING *''',
            (d.get('name'), d.get('category'), d.get('cook_time'), d.get('servings'),
             d.get('difficulty'), d.get('ingredients'), d.get('instructions'),
             d.get('notes'), d.get('photo_url'), rid))
        row = dict(cur.fetchone())
    else:
        cur.execute('''UPDATE recipes SET name=?,category=?,cook_time=?,servings=?,
            difficulty=?,ingredients=?,instructions=?,notes=?,photo_url=? WHERE id=?''',
            (d.get('name'), d.get('category'), d.get('cook_time'), d.get('servings'),
             d.get('difficulty'), d.get('ingredients'), d.get('instructions'),
             d.get('notes'), d.get('photo_url'), rid))
        cur.execute('SELECT * FROM recipes WHERE id=?', (rid,))
        row = dict(cur.fetchone())
    conn.commit()
    conn.close()
    if 'created_at' in row and row['created_at']:
        row['created_at'] = str(row['created_at'])
    return jsonify(row)

@app.route('/recipes/<int:rid>', methods=['DELETE'])
def delete_recipe(rid):
    conn, kind = get_conn()
    cur = conn.cursor()
    ph = '%s' if kind == 'pg' else '?'
    cur.execute(f'DELETE FROM recipes WHERE id={ph}', (rid,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': rid})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5055)), debug=False)
