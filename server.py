import json
import os
import re
import threading
import uuid
from datetime import datetime
from queue import Queue, Empty
from urllib.parse import quote

from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS

from app import scrape_google_maps, save_to_csv
from busca import main as busca_main

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# Store job state: { job_id: { "status", "stage", "current", "total", "message", "output_file", "queue" } }
jobs = {}


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


@app.route("/api/search", methods=["POST"])
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
