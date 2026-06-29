"""
api.py — Serveur Flask pour le dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import json
from datetime import datetime
from pathlib import Path
import threading

from scraper import (
    lancer_collecte, charger_base, calculer_stats,
    exporter_csv, charger_logs, SECTEURS_BENIN,
    VILLES_BENIN, DEPARTEMENTS_BENIN, SOURCES, EXPORT_DIR
)

app = Flask(__name__)
CORS(app)

# État de la collecte en cours
collecte_state = {
    "en_cours": False,
    "progression": 0,
    "message": "",
    "derniere_stats": None
}


def run_collecte(sources, secteurs, villes, nb):
    collecte_state["en_cours"] = True
    collecte_state["progression"] = 10
    collecte_state["message"] = "Initialisation des scrapers..."

    try:
        import time
        collecte_state["progression"] = 30
        collecte_state["message"] = f"Collecte sur {', '.join(sources)}..."
        
        stats, data = lancer_collecte(sources, secteurs, villes, nb)
        
        collecte_state["progression"] = 80
        collecte_state["message"] = "Dédoublonnage et classification..."
        time.sleep(0.5)
        
        collecte_state["progression"] = 95
        collecte_state["message"] = "Sauvegarde en base..."
        time.sleep(0.3)
        
        collecte_state["derniere_stats"] = stats
        collecte_state["progression"] = 100
        collecte_state["message"] = f"Terminé ! {stats['total']} entreprises en base."
    except Exception as e:
        collecte_state["message"] = f"Erreur: {str(e)}"
    finally:
        collecte_state["en_cours"] = False


@app.route("/api/stats")
def get_stats():
    data = charger_base()
    stats = calculer_stats(data)
    return jsonify(stats)


@app.route("/api/entreprises")
def get_entreprises():
    data = charger_base()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    secteur = request.args.get("secteur", "")
    ville = request.args.get("ville", "")
    source = request.args.get("source", "")
    qualite = request.args.get("qualite", "")
    search = request.args.get("search", "").lower()

    # Filtres
    filtered = data
    if secteur:
        filtered = [e for e in filtered if e.get("secteur") == secteur]
    if ville:
        filtered = [e for e in filtered if e.get("ville") == ville]
    if source:
        filtered = [e for e in filtered if e.get("source") == source]
    if qualite:
        filtered = [e for e in filtered if e.get("qualite") == qualite]
    if search:
        filtered = [e for e in filtered if search in e.get("nom", "").lower()
                    or search in e.get("ville", "").lower()
                    or search in e.get("secteur", "").lower()]

    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    page_data = filtered[start:end]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "data": page_data
    })


@app.route("/api/lancer-collecte", methods=["POST"])
def lancer():
    if collecte_state["en_cours"]:
        return jsonify({"error": "Collecte déjà en cours"}), 400

    body = request.json or {}
    sources = body.get("sources", ["Google Maps"])
    secteurs = body.get("secteurs", SECTEURS_BENIN[:3])
    villes = body.get("villes", ["Cotonou"])
    nb = int(body.get("nb_par_source", 100))

    t = threading.Thread(target=run_collecte, args=(sources, secteurs, villes, nb))
    t.daemon = True
    t.start()

    return jsonify({"message": "Collecte lancée", "ok": True})


@app.route("/api/progression")
def progression():
    return jsonify(collecte_state)


@app.route("/api/exporter")
def exporter():
    data = charger_base()
    secteur = request.args.get("secteur", "")
    ville = request.args.get("ville", "")
    if secteur:
        data = [e for e in data if e.get("secteur") == secteur]
    if ville:
        data = [e for e in data if e.get("ville") == ville]

    path = exporter_csv(data)
    return send_file(path, as_attachment=True, download_name=Path(path).name)


@app.route("/api/logs")
def get_logs():
    logs = charger_logs()
    return jsonify(logs[-50:])


@app.route("/api/config")
def get_config():
    return jsonify({
        "secteurs": SECTEURS_BENIN,
        "villes": VILLES_BENIN,
        "departements": DEPARTEMENTS_BENIN,
        "sources": SOURCES
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    from scraper import DB_FILE
    if DB_FILE.exists():
        DB_FILE.unlink()
    return jsonify({"ok": True, "message": "Base réinitialisée"})


if __name__ == "__main__":
    print("API démarrée sur http://localhost:5050")
    app.run(port=5050, debug=False)