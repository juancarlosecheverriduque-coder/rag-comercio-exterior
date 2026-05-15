"""
servidor.py — Backend Flask del RAG de Comercio Exterior
Expone endpoints para consultas y estado del sistema.
Lanza el monitor automático en un hilo separado.
"""

import os, sys, json, threading, logging
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR  = Path(__file__).parent.parent
DATOS_DIR = BASE_DIR / "datos"
DB_DIR    = DATOS_DIR / "vectordb"
UI_DIR    = BASE_DIR  / "ui"
LOG_FILE  = BASE_DIR  / "logs" / "servidor.log"
ENV_FILE  = BASE_DIR  / "config.env"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ── Cargar config.env ─────────────────────────────────────────────────────────

def cargar_env():
    if ENV_FILE.exists():
        for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if "=" in linea and not linea.startswith("#"):
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

cargar_env()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
N_RESULTADOS      = 6   # fragmentos a recuperar por consulta
# Opciones de modelo (cambia esta línea si quieres más calidad/menos costo):
#   "claude-haiku-4-5-20251001"  → ~$0.008/consulta  (RECOMENDADO: rápido y económico)
#   "claude-sonnet-4-6"          → ~$0.023/consulta  (calidad alta)
#   "claude-opus-4-7"            → ~$0.038/consulta  (máxima precisión, costoso)
MODELO_CLAUDE     = "claude-haiku-4-5-20251001"

# ── ChromaDB ──────────────────────────────────────────────────────────────────

def get_coleccion():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    return client.get_or_create_collection(
        name="legislacion_co",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

coleccion = None

def inicializar_db():
    global coleccion
    try:
        coleccion = get_coleccion()
        total = coleccion.count()
        log.info(f"ChromaDB lista: {total} fragmentos indexados")
    except Exception as e:
        log.error(f"Error iniciando ChromaDB: {e}")

# ── Consulta RAG ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un experto en comercio exterior colombiano. Tienes acceso a legislación actualizada de Colombia en materia de importaciones, exportaciones, aranceles, DIAN, MinCIT, VUCE y la Comunidad Andina (CAN).

INSTRUCCIONES:
1. Responde SIEMPRE en español.
2. Basa tus respuestas EXCLUSIVAMENTE en los fragmentos de legislación proporcionados.
3. Cita siempre la fuente exacta: nombre del documento, artículo o resolución.
4. Si la información no está en los fragmentos, dilo claramente.
5. Sé preciso con números de artículos, fechas y códigos arancelarios.
6. Organiza la respuesta de forma clara con la norma aplicable primero.

FORMATO DE RESPUESTA:
- Inicia con la norma/resolución aplicable
- Explica la regla o procedimiento
- Indica excepciones si las hay
- Cita la fuente al final entre corchetes"""

def consultar(pregunta: str) -> dict:
    if not ANTHROPIC_API_KEY:
        return {
            "respuesta": "⚠️ No hay API key configurada. Edita el archivo config.env y agrega tu ANTHROPIC_API_KEY.",
            "fuentes": [],
            "fragmentos": 0
        }

    if coleccion is None or coleccion.count() == 0:
        return {
            "respuesta": "⚠️ La base de legislación está vacía. Ejecuta 3_ACTUALIZAR_AHORA.bat para descargar normas, o agrega archivos a datos/legislacion/ y reinicia el sistema.",
            "fuentes": [],
            "fragmentos": 0
        }

    # Recuperar fragmentos relevantes
    try:
        resultados = coleccion.query(
            query_texts=[pregunta],
            n_results=min(N_RESULTADOS, coleccion.count()),
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        log.error(f"Error en búsqueda vectorial: {e}")
        return {"respuesta": f"Error en búsqueda: {e}", "fuentes": [], "fragmentos": 0}

    documentos = resultados["documents"][0]
    metadatas  = resultados["metadatas"][0]
    distancias = resultados["distances"][0]

    if not documentos:
        return {
            "respuesta": "No encontré legislación relevante para tu consulta en la base de datos.",
            "fuentes": [],
            "fragmentos": 0
        }

    # Construir contexto con fuentes
    contexto_partes = []
    fuentes_unicas  = {}
    for i, (doc, meta, dist) in enumerate(zip(documentos, metadatas, distancias)):
        relevancia = round((1 - dist) * 100, 1)
        fuente     = meta.get("fuente", "Desconocido")
        archivo    = meta.get("archivo", "")
        contexto_partes.append(
            f"[FRAGMENTO {i+1} — {fuente} | {archivo} | Relevancia: {relevancia}%]\n{doc}"
        )
        if archivo not in fuentes_unicas:
            fuentes_unicas[archivo] = {
                "fuente":     fuente,
                "archivo":    archivo,
                "relevancia": relevancia,
                "fecha":      meta.get("fecha_indexacion", "")[:10]
            }

    contexto = "\n\n---\n\n".join(contexto_partes)

    # Llamar a Claude
    try:
        cliente    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        mensaje    = f"LEGISLACIÓN DISPONIBLE:\n\n{contexto}\n\n---\n\nPREGUNTA DEL USUARIO:\n{pregunta}"
        respuesta  = cliente.messages.create(
            model=MODELO_CLAUDE,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": mensaje}]
        )
        texto_respuesta = respuesta.content[0].text
    except Exception as e:
        log.error(f"Error llamando a Claude: {e}")
        texto_respuesta = f"Error al consultar Claude: {e}"

    return {
        "respuesta":  texto_respuesta,
        "fuentes":    list(fuentes_unicas.values()),
        "fragmentos": len(documentos)
    }

# ── Flask App ─────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=str(UI_DIR))
CORS(app)

@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")

@app.route("/consultar", methods=["POST"])
def endpoint_consultar():
    data     = request.get_json()
    pregunta = (data or {}).get("pregunta", "").strip()
    if not pregunta:
        return jsonify({"error": "Pregunta vacía"}), 400
    log.info(f"Consulta: {pregunta[:80]}")
    resultado = consultar(pregunta)
    return jsonify(resultado)

@app.route("/estado")
def endpoint_estado():
    total = 0
    db_ok = False
    if coleccion:
        try:
            total = coleccion.count()
            db_ok = True
        except Exception:
            pass

    # Leer últimas líneas del log del monitor
    actividad = []
    monitor_log = BASE_DIR / "logs" / "monitor.log"
    if monitor_log.exists():
        lineas = monitor_log.read_text(encoding="utf-8", errors="ignore").splitlines()
        actividad = lineas[-8:] if len(lineas) >= 8 else lineas

    return jsonify({
        "db_ok":          db_ok,
        "fragmentos":     total,
        "api_key_ok":     bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "TU_API_KEY_AQUI"),
        "ultima_actividad": actividad,
        "hora":           datetime.now().strftime("%d/%m/%Y %H:%M")
    })

@app.route("/actualizar", methods=["POST"])
def endpoint_actualizar():
    """Dispara el monitor en un hilo separado sin bloquear."""
    def _run():
        try:
            from monitor import ciclo_completo
            nuevos = ciclo_completo()
            inicializar_db()   # refrescar conteo
            log.info(f"Actualización manual: {nuevos} nuevos documentos")
        except Exception as e:
            log.error(f"Error en actualización manual: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"mensaje": "Actualización iniciada. Puede tomar varios minutos."})

# ── Monitor en hilo separado ──────────────────────────────────────────────────

def iniciar_monitor():
    def _loop():
        import time
        from monitor import ciclo_completo
        while True:
            try:
                ciclo_completo()
            except Exception as e:
                log.error(f"Error en ciclo monitor: {e}")
            time.sleep(6 * 3600)   # 6 horas

    t = threading.Thread(target=_loop, daemon=True, name="monitor")
    t.start()
    log.info("Monitor automático iniciado (ciclo cada 6 horas)")

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    inicializar_db()
    iniciar_monitor()
    log.info("Servidor iniciado en http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
