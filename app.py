#app.py
import os
import psutil
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from agent import process_command
from tools.excel_tools import analyze_file_structure, detect_patterns_and_relationships, save_uploaded_file, learn_from_file_content
from brain.ai_brain import AIBrain
import time
from threading import Lock
from dotenv import load_dotenv
from utils.logger import LIVE_LOGS

load_dotenv()

app = Flask(__name__)
app.config['DATA_FOLDER'] = os.getenv('DATA_FOLDER', 'data')
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['DATA_FOLDER'], 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Initialize Brain
brain = AIBrain()
START_TIME = time.time()
OBJECTIVE_STATE_LOCK = Lock()
OBJECTIVE_STATE = {
    "tag": "AWAITING_INPUT",
    "desc": "System ready. Standing by for user commands, excel processing, or data queries.",
    "updated_at": int(time.time())
}

# Ensure folders exist
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/favicon.ico')
def favicon():
    static_dir = os.path.join(app.root_path, 'static')
    # Prefer favicon.ico; fall back to jarvis_favicon.png served as PNG
    if os.path.exists(os.path.join(static_dir, 'favicon.ico')):
        return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    return send_from_directory(static_dir, 'jarvis_favicon.png', mimetype='image/png')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/neural-network")
def neural_network():
    return render_template("neural_network.html")

@app.route("/command", methods=["POST"])
def command():
    data = request.json
    user_command = data.get("command")
    if not user_command:
        return jsonify({"error": "No command provided"}), 400

    with OBJECTIVE_STATE_LOCK:
        OBJECTIVE_STATE["tag"] = "PROCESSING_QUERY"
        OBJECTIVE_STATE["desc"] = f'Analyzing command: "{user_command[:120]}"'
        OBJECTIVE_STATE["updated_at"] = int(time.time())

    try:
        result = process_command(user_command)
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(f"[COMMAND ERROR] {err_detail}")

        # Push the real error into the live log so frontend can see it
        from utils.logger import push_log as _push
        _push(f"[Error] {type(e).__name__}: {str(e)}", "error")

        with OBJECTIVE_STATE_LOCK:
            OBJECTIVE_STATE["tag"] = "CRITICAL_FAILURE"
            OBJECTIVE_STATE["desc"] = f"Neural link error: {str(e)}"
            OBJECTIVE_STATE["updated_at"] = int(time.time())

        # Return JSON instead of raising — frontend shows the real error message
        return jsonify({
            "status": "error",
            "message": f"เกิดข้อผิดพลาด: {type(e).__name__}: {str(e)}",
            "error": str(e)
        })

    status = result.get("status", "success")
    message = result.get("message") or result.get("response") or "Task complete."
    if status == "success":
        tag = "MISSION_COMPLETE"
    elif status == "error":
        tag = "LINK_ERROR"
    else:
        tag = "AWAITING_INPUT"

    with OBJECTIVE_STATE_LOCK:
        OBJECTIVE_STATE["tag"] = tag
        OBJECTIVE_STATE["desc"] = message
        OBJECTIVE_STATE["updated_at"] = int(time.time())

    return jsonify(result)

@app.route("/logs")
def get_logs():
    """
    Drain the LIVE_LOGS queue and return all pending messages as JSON.
    Frontend polls this every 300-400 ms to display realtime process steps.
    Returns at most 50 messages per call to keep payloads small.
    """
    logs = []
    max_drain = 50
    while not LIVE_LOGS.empty() and len(logs) < max_drain:
        try:
            logs.append(LIVE_LOGS.get_nowait())
        except Exception:
            break
    return jsonify(logs)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        # Save consistently to UPLOAD_FOLDER (data/uploads/)
        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Also copy to DATA_FOLDER root so Excel tools can find it by name
        data_filepath = os.path.join(app.config['DATA_FOLDER'], filename)
        import shutil
        shutil.copy2(filepath, data_filepath)

        # Analyze and learn from this file
        analysis = analyze_file_structure(data_filepath)
        learn_from_file_content(data_filepath, analysis, brain)

        return jsonify({
            "status": "success",
            "message": f"Successfully learned template from {filename}",
            "filename": filename,
            "preview": analysis.get("sheets", [{}])[0].get("sample_data", [])
        })

@app.route("/brain/status")
def get_brain_status():
    from brain.knowledge_graph import load_knowledge
    from brain.context_memory import load_context

    knowledge = load_knowledge()
    context = load_context()

    # Calculate some dynamic metrics
    uptime = int(time.time() - START_TIME)
    # Use a pseudo-random value seeded by current second so it changes every second
    neural_activity = 40 + int((time.time() * 7 + os.getpid()) % 40)

    # knowledge["entities"] is a dict {name: {...}}, knowledge["relations"] is a list
    entities_dict = knowledge.get("entities", {})
    if not isinstance(entities_dict, dict):
        entities_dict = {}
    contexts_list = context.get("contexts", [])
    synapse_load = len(entities_dict) + len(contexts_list)

    # Iterate over entity values (each value is a dict with a "type" key)
    entity_types = {}
    for entity_name, entity_data in entities_dict.items():
        if isinstance(entity_data, dict):
            t = entity_data.get("type", "unknown")
        else:
            t = "unknown"
        entity_types[t] = entity_types.get(t, 0) + 1

    # Correct knowledge file path: brain/knowledge.json (not knowledge_graph.json)
    knowledge_file = os.path.join("brain", "knowledge.json")
    knowledge_size_kb = os.path.getsize(knowledge_file) // 1024 if os.path.exists(knowledge_file) else 0

    return jsonify({
        "uptime": uptime,
        "neural_activity": neural_activity,
        "synapse_load": synapse_load,
        "cognitive_threads": 8,
        "knowledge_size_kb": knowledge_size_kb,
        "entity_types": entity_types,
        "recent_logs": contexts_list[-10:]
    })

@app.route("/brain/suggestions")
def get_suggestions():
    partial = request.args.get("q", "")
    # If get_suggestions is not a method, use a fallback or safe access
    suggestions = getattr(brain, "get_suggestions", lambda q: [])(partial)
    return jsonify(suggestions)

@app.route("/brain/objective")
def get_objective_state():
    with OBJECTIVE_STATE_LOCK:
        return jsonify(dict(OBJECTIVE_STATE))

@app.route("/data/<path:filename>")
def get_data_file(filename):
    return send_from_directory(app.config['DATA_FOLDER'], filename)


@app.route("/api/students")
def api_students():
    """DataTables server-side endpoint for the student database cache."""
    import json as _json

    draw = request.args.get("draw", 1, type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search_val = request.args.get("search", "").strip().lower()

    # Optional column filters passed as JSON string
    try:
        filters = _json.loads(request.args.get("filters", "{}"))
    except Exception:
        filters = {}

    cache_path = os.path.join(app.config['DATA_FOLDER'], "db_cache.json")
    if not os.path.exists(cache_path):
        return jsonify({"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []})

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            records = _json.load(f)
    except Exception:
        return jsonify({"draw": draw, "recordsTotal": 0, "recordsFiltered": 0, "data": []})

    total = len(records)

    # Apply search filter
    if search_val:
        records = [
            r for r in records
            if any(search_val in str(v).lower() for v in r.values())
        ]

    # Apply column filters (e.g. {"ยศ": "ร.อ."})
    for col, val in filters.items():
        if val:
            records = [r for r in records if str(r.get(col, "")).lower() == val.lower()]

    filtered = len(records)

    # Paginate
    start = (page - 1) * per_page
    page_data = records[start: start + per_page]

    return jsonify({
        "draw": draw,
        "recordsTotal": total,
        "recordsFiltered": filtered,
        "data": page_data,
    })

# New API: append multiple rows (only the selected rows from UI)
@app.route('/api/append_rows', methods=['POST'])
def api_append_rows():
    payload = request.json or {}
    filename = payload.get('file', 'students.xlsx')
    rows = payload.get('rows', [])
    results = []
    try:
        from tools.excel_tools import append_row
        # Security: Only append rows that have been explicitly selected by the UI.
        # Each row should include a special key 'selected' or the client should only send selected rows.
        for r in rows:
            if isinstance(r, dict) and not r.get('__selected') and not r.get('selected'):
                # skip rows not explicitly marked as selected
                continue
            # Ensure we only keep columns A-J (first 10 keys) if dict; otherwise pass through
            if isinstance(r, dict):
                # Remove selection markers before writing
                r.pop('__selected', None)
                r.pop('selected', None)
                filtered = {}
                for i, k in enumerate(list(r.keys())):
                    if i >= 10: break
                    filtered[k] = r[k]
                r = filtered
            res = append_row({"file": filename, "data": r})
            results.append(res)
        if not results:
            return jsonify({"status": "error", "message": "No selected rows provided to append."}), 400
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def get_project_size():
    total_size = 0
    for dirpath, dirnames, filenames in os.walk("."):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return f"{total_size / (1024*1024):.2f} MB"

@app.route("/system_stats")
def system_stats():
    ram = psutil.virtual_memory()
    cpu_usage = psutil.cpu_percent()
    
    # Try to get real temperature
    cpu_temp = "N/A"
    try:
        # psutil.sensors_temperatures() is mostly for Linux
        temps = psutil.sensors_temperatures()
        if temps and 'coretemp' in temps:
            cpu_temp = f"{temps['coretemp'][0].current}°C"
    except Exception:
        pass
        
    # Fallback/Mock for Windows UI aesthetics if real temp fails
    if cpu_temp == "N/A":
        # Estimate temp based on load: base 40C + (load * 0.4)
        est_temp = 40 + (cpu_usage * 0.4) + (os.getpid() % 5)
        cpu_temp = f"{est_temp:.1f}°C"

    return jsonify({
        "ram_usage": f"{ram.percent}%",
        "project_size": get_project_size(),
        "cpu_usage": f"{cpu_usage}%",
        "cpu_temp": cpu_temp,
        "disk_free": f"{psutil.disk_usage('.').percent}%"
    })

if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode, port=5000, use_reloader=debug_mode)
