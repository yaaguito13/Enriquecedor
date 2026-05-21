"""app.py — Backend Flask: scraping + enriquecimiento de ficheros"""

import os, json, threading, uuid
from queue import Queue, Empty
from dataclasses import asdict

from flask import Flask, render_template, request, jsonify, Response, send_file
from scraper import ScraperAgent, export_results, get_demo_companies, SECTOR_QUERIES

app = Flask(__name__)
app.secret_key = os.urandom(24)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXT = {".csv", ".xlsx", ".xls", ".xlsm", ".tsv"}

sessions: dict[str, dict] = {}

# ───────────────────────────────
# Utilidades
# ───────────────────────────────
def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXT


def _make_session(q: Queue) -> tuple[str, dict]:
    sid = str(uuid.uuid4())
    sessions[sid] = {
        "queue": q,
        "companies": [],
        "done": False,
        "agent": None
    }
    return sid, sessions[sid]


# ───────────────────────────────
# Ruta principal
# ───────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", sectors=list(SECTOR_QUERIES.keys()))


# ───────────────────────────────
# CHECK IA (🔴 ESTA ES LA QUE TE FALTABA)
# ───────────────────────────────
@app.route("/api/check-ai")
def check_ai():
    """
    Endpoint usado por el frontend para saber si el modo IA está activo.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        return jsonify({
            "ok": True,
            "message": "Claude activo y listo"
        })

    return jsonify({
        "ok": False,
        "message": "Sin API key configurada"
    })


# ───────────────────────────────
# SCRAPING
# ───────────────────────────────
@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    data = request.get_json(force=True)
    sector = data.get("sector", "Tecnología")
    keywords = data.get("keywords", "")
    demo = data.get("demo", False)

    q = Queue()
    sid, session = _make_session(q)

    def run():
        try:
            if demo:
                import time
                companies = get_demo_companies(sector)

                for i, c in enumerate(companies):
                    if session.get("stopped"):
                        q.put({"type": "stopped", "message": "⏹ Demo detenida."})
                        break
                    time.sleep(0.4)
                    session["companies"].append(asdict(c))

                    q.put({
                        "type": "company",
                        "company": asdict(c),
                        "message": f"✓ {c.empresa}",
                        "stats": {
                            "fuentes": i + 1,
                            "empresas": i + 1,
                            "emails": sum(1 for x in companies[:i+1] if x.email),
                            "telefonos": sum(1 for x in companies[:i+1] if x.telefono)
                        }
                    })

                if not session.get("stopped"):
                    q.put({
                        "type": "done",
                        "message": "✅ Demo completada.",
                        "stats": {
                            "fuentes": len(companies),
                            "empresas": len(companies),
                            "emails": sum(1 for c in companies if c.email),
                            "telefonos": sum(1 for c in companies if c.telefono)
                        }
                    })

            else:
                def cb(msg, **kw):
                    session["companies"] = [
                        asdict(c) for c in agent.companies.values()
                    ]
                    q.put({"message": msg, **kw})

                agent = ScraperAgent(sector, keywords, status_cb=cb)
                session["agent"] = agent
                if session.get("stopped"):
                    agent.stop()
                agent.run()

                session["companies"] = [
                    asdict(c) for c in agent.companies.values()
                ]

        except Exception as e:
            q.put({"type": "error", "message": f"Error: {e}"})
        finally:
            session["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"session_id": sid})


# ───────────────────────────────
# ENRIQUECIMIENTO
# ───────────────────────────────
@app.route("/api/enrich", methods=["POST"])
def start_enrich():
    if "file" not in request.files:
        return jsonify({"error": "No se recibió ningún fichero"}), 400

    f = request.files["file"]

    if not f.filename or not _allowed_file(f.filename):
        return jsonify({"error": "Formato no permitido"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_name = f"{uuid.uuid4()}{os.path.splitext(f.filename)[1].lower()}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    f.save(file_path)

    q = Queue()
    sid, session = _make_session(q)
    session["mode"] = "enrich"

    def run():
        from enricher import EnricherAgent, export_enriched

        try:
            def cb(msg, **kw):
                q.put({"message": msg, **kw})
                if kw.get("type") == "row":
                    session["companies"].append(kw["row"])

            agent = EnricherAgent(status_cb=cb)
            session["agent"] = agent
            if session.get("stopped"):
                agent.stop()
            results = agent.run(file_path)

            session["companies"] = [
                asdict(r) for r in results
            ]

        except Exception as e:
            q.put({"type": "error", "message": f"Error: {e}"})
        finally:
            session["done"] = True
            try:
                os.remove(file_path)
            except Exception:
                pass

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"session_id": sid})


# ───────────────────────────────
# PREVIEW CSV/EXCEL
# ───────────────────────────────
@app.route("/api/preview", methods=["POST"])
def preview_columns():
    if "file" not in request.files:
        return jsonify({"error": "No se recibió fichero"}), 400

    f = request.files["file"]

    if not f.filename or not _allowed_file(f.filename):
        return jsonify({"error": "Formato no permitido"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_name = f"{uuid.uuid4()}{os.path.splitext(f.filename)[1].lower()}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    f.save(file_path)

    try:
        from enricher import read_file, detect_columns

        headers, rows = read_file(file_path)
        col = detect_columns(headers)

        detected = {k: headers[v] for k, v in col.items() if v is not None}
        undetected = [k for k, v in col.items() if v is None]

        return jsonify({
            "headers": headers,
            "detected": detected,
            "undetected": undetected,
            "total_rows": len(rows),
            "ok": True
        })

    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 400

    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass


# ───────────────────────────────
# STOP
# ───────────────────────────────
@app.route("/api/stop/<sid>", methods=["POST"])
def stop_scrape(sid: str):
    session = sessions.get(sid)

    if not session:
        return jsonify({"error": "Sesión no encontrada"}), 404

    session["stopped"] = True
    agent = session.get("agent")

    if agent:
        agent.stop()
        
    return jsonify({"ok": True})


# ───────────────────────────────
# SSE STREAM
# ───────────────────────────────
@app.route("/api/stream/<sid>")
def stream(sid: str):
    if sid not in sessions:
        return jsonify({"error": "Not found"}), 404

    def generate():
        session = sessions[sid]
        q = session["queue"]

        while True:
            try:
                event = q.get(timeout=1.0)

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if event.get("type") in ("done", "error", "stopped"):
                    break

            except Empty:
                if session["done"]:
                    break
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ───────────────────────────────
# EXPORT
# ───────────────────────────────
@app.route("/api/export/<sid>/<fmt>")
def export(sid: str, fmt: str):
    if sid not in sessions:
        return jsonify({"error": "Not found"}), 404

    raw = sessions[sid].get("companies", [])

    if not raw:
        return jsonify({"error": "Sin datos"}), 400

    mode = sessions[sid].get("mode", "scrape")

    if mode == "enrich":
        from enricher import EnrichedRow, export_enriched

        rows = [
            EnrichedRow(**{k: v for k, v in r.items()
                           if k in EnrichedRow.__dataclass_fields__})
            for r in raw
        ]

        csv_path, xlsx_path = export_enriched(rows, OUTPUT_DIR)
        fname_base = "enriquecido"

    else:
        from scraper import Company

        companies = [
            Company(**{k: v for k, v in c.items()
                       if k in Company.__dataclass_fields__})
            for c in raw
        ]

        csv_path, xlsx_path = export_results(companies, OUTPUT_DIR)
        fname_base = "resultados"

    if fmt == "xlsx":
        return send_file(xlsx_path, as_attachment=True,
                         download_name=f"{fname_base}.xlsx")

    if fmt == "csv":
        return send_file(csv_path, as_attachment=True,
                         download_name=f"{fname_base}.csv")

    return jsonify({"error": "Formato no soportado"}), 400


# ───────────────────────────────
# MAIN
# ───────────────────────────────
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    print("\n🚀  EmpresaScout  →  http://localhost:5001\n")

    app.run(debug=True, threaded=True, port=5001)