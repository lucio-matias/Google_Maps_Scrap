import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from queue import Queue, Empty
from urllib.parse import quote

import jwt
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from app import scrape_google_maps, save_to_csv
from busca import main as busca_main

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-secret-in-production")
JWT_EXPIRY_HOURS = 24
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Store job state: { job_id: { "status", "stage", "current", "total", "message", "output_file", "queue" } }
jobs = {}


# ---------- User storage helpers ----------

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# ---------- JWT helpers ----------

def create_token(username):
    payload = {
        "sub": username,
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Accept token from Authorization header or query param (for EventSource / window.open)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
        else:
            token = request.args.get("token", "")

        if not token:
            return jsonify({"error": "Token ausente ou inválido."}), 401
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido."}), 401
        return f(*args, **kwargs)
    return decorated


# ---------- Auth endpoints ----------

def _validate_password_strength(password):
    """Returns an error message if password doesn't meet requirements, else None."""
    if len(password) < 8:
        return "A senha deve ter pelo menos 8 caracteres."
    if not re.search(r'[A-Z]', password):
        return "A senha deve conter pelo menos uma letra maiúscula."
    if not re.search(r'[a-z]', password):
        return "A senha deve conter pelo menos uma letra minúscula."
    if not re.search(r'[0-9]', password):
        return "A senha deve conter pelo menos um número."
    if not re.search(r'[^A-Za-z0-9]', password):
        return "A senha deve conter pelo menos um símbolo (!@#$%...)."
    return None


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "Nome, e-mail e senha são obrigatórios."}), 400

    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({"error": "E-mail inválido."}), 400

    pwd_error = _validate_password_strength(password)
    if pwd_error:
        return jsonify({"error": pwd_error}), 400

    users = load_users()
    if email in users:
        return jsonify({"error": "E-mail já cadastrado."}), 409

    users[email] = {"name": name, "hash": generate_password_hash(password)}
    save_users(users)

    token = create_token(email)
    return jsonify({"token": token, "username": name}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    # Accept 'email' or legacy 'username' field
    email = (data.get("email") or data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "E-mail e senha são obrigatórios."}), 400

    users = load_users()
    user_data = users.get(email)

    if not user_data:
        return jsonify({"error": "Credenciais inválidas."}), 401

    # Support legacy flat format {key: hash_string} and new format {key: {name, hash}}
    if isinstance(user_data, str):
        hashed = user_data
        display_name = email
    else:
        hashed = user_data.get("hash", "")
        display_name = user_data.get("name", email)

    if not hashed or not check_password_hash(hashed, password):
        return jsonify({"error": "Credenciais inválidas."}), 401

    token = create_token(email)
    return jsonify({"token": token, "username": display_name})


# ---------- Utilities ----------

def sanitize_filename(name):
    """Remove characters that are invalid in filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


def run_job(job_id, termo, cidade):
    job = jobs[job_id]
    queue = job["queue"]

    date_suffix = datetime.now().strftime("%m-%Y")
    safe_termo = sanitize_filename(termo)
    temp_dir = os.path.join(os.path.dirname(__file__), "TEMP")
    os.makedirs(temp_dir, exist_ok=True)
    stage1_file = os.path.join(temp_dir, f"{safe_termo}_{date_suffix}.csv")
    stage2_file = os.path.join(temp_dir, f"busca_{safe_termo}_{date_suffix}.xlsx")

    job["output_file"] = stage2_file

    def send_progress(stage, current, total, status="running", message=""):
        job.update({"stage": stage, "current": current, "total": total, "status": status, "message": message})
        queue.put({"stage": stage, "current": current, "total": total, "status": status, "message": message})

    try:
        # --- Stage 1: Google Maps scraping ---
        send_progress(1, 0, 0, "running", "Iniciando busca no Google Maps...")

        query = f"{termo} em {cidade}"
        search_url = f"https://www.google.com/maps/search/{quote(query)}"

        def stage1_callback(current, total):
            send_progress(1, current, total, "running", f"Extraindo empresa {current}/{total}")

        scraped_data = scrape_google_maps(search_url, progress_callback=stage1_callback)

        if not scraped_data:
            send_progress(1, 0, 0, "error", "Nenhum dado encontrado no Google Maps.")
            return

        save_to_csv(scraped_data, filename=stage1_file)
        send_progress(1, len(scraped_data), len(scraped_data), "running", "Etapa 1 concluída.")

        # --- Stage 2: Contact extraction ---
        send_progress(2, 0, len(scraped_data), "running", "Iniciando extração de contatos...")

        def stage2_callback(current, total):
            send_progress(2, current, total, "running", f"Processando contatos {current}/{total}")

        busca_main(input_file=stage1_file, output_file=stage2_file, progress_callback=stage2_callback)

        send_progress(2, len(scraped_data), len(scraped_data), "completed", "Busca finalizada com sucesso!")

    except Exception as e:
        send_progress(job.get("stage", 1), 0, 0, "error", f"Erro: {str(e)}")


# ---------- Protected API routes ----------

@app.route("/api/search", methods=["POST"])
@require_auth
def start_search():
    data = request.get_json()
    termo = data.get("termo", "").strip()
    cidade = data.get("cidade", "").strip()

    if not termo or not cidade:
        return jsonify({"error": "Termo e cidade são obrigatórios."}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "stage": 1,
        "current": 0,
        "total": 0,
        "message": "Iniciando...",
        "output_file": None,
        "queue": Queue(),
    }

    thread = threading.Thread(target=run_job, args=(job_id, termo, cidade), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
@require_auth
def progress(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job não encontrado."}), 404

    def generate():
        queue = jobs[job_id]["queue"]
        while True:
            try:
                msg = queue.get(timeout=30)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("status") in ("completed", "error"):
                    break
            except Empty:
                # Send keepalive
                yield f"data: {json.dumps({'keepalive': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/api/download/<job_id>")
@require_auth
def download(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job não encontrado."}), 404

    job = jobs[job_id]
    if job["status"] != "completed":
        return jsonify({"error": "Job ainda não concluído."}), 400

    output_file = job["output_file"]
    if not output_file or not os.path.exists(output_file):
        return jsonify({"error": "Arquivo não encontrado."}), 404

    return send_file(output_file, as_attachment=True, download_name=os.path.basename(output_file))


if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
