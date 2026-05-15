"""
indexador.py — Extrae texto de documentos y los indexa en ChromaDB
Soporta: PDF, DOCX, TXT, HTML
"""

import os, sys, re, argparse, logging
from pathlib import Path
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

# PDF
try:
    import PyPDF2
    PYPDF_OK = True
except ImportError:
    PYPDF_OK = False

# DOCX
try:
    from docx import Document as DocxDocument
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

# HTML
try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

BASE_DIR  = Path(__file__).parent.parent
DATOS_DIR = BASE_DIR / "datos"
DB_DIR    = DATOS_DIR / "vectordb"
LEG_DIR   = DATOS_DIR / "legislacion"
LOG_FILE  = BASE_DIR  / "logs" / "indexador.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

CHUNK_SIZE    = 800    # caracteres por fragmento
CHUNK_OVERLAP = 150    # solapamiento entre fragmentos

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

# ── Extractores de texto ──────────────────────────────────────────────────────

def extraer_pdf(ruta: Path) -> str:
    if not PYPDF_OK:
        return ""
    texto = []
    try:
        with open(ruta, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texto.append(t)
    except Exception as e:
        log.warning(f"Error leyendo PDF {ruta.name}: {e}")
    return "\n".join(texto)

def extraer_docx(ruta: Path) -> str:
    if not DOCX_OK:
        return ""
    try:
        doc = DocxDocument(str(ruta))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        log.warning(f"Error leyendo DOCX {ruta.name}: {e}")
        return ""

def extraer_html(ruta: Path) -> str:
    if not BS4_OK:
        return ruta.read_text(encoding="utf-8", errors="ignore")
    try:
        soup = BeautifulSoup(ruta.read_bytes(), "lxml")
        return soup.get_text(separator="\n")
    except Exception as e:
        log.warning(f"Error leyendo HTML {ruta.name}: {e}")
        return ""

def extraer_txt(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        log.warning(f"Error leyendo TXT {ruta.name}: {e}")
        return ""

EXTRACTORES = {
    ".pdf":  extraer_pdf,
    ".docx": extraer_docx,
    ".doc":  extraer_docx,
    ".html": extraer_html,
    ".htm":  extraer_html,
    ".txt":  extraer_txt,
    ".md":   extraer_txt,
}

# ── Chunking ──────────────────────────────────────────────────────────────────

def limpiar(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"\.{3,}", "...", texto)
    return texto.strip()

def chunk_texto(texto: str, nombre: str) -> list[str]:
    texto = limpiar(texto)
    if len(texto) == 0:
        return []
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + CHUNK_SIZE
        # Cortar en espacio o punto para no partir palabras
        if fin < len(texto):
            corte = texto.rfind(" ", inicio, fin)
            if corte == -1:
                corte = fin
            fin = corte
        chunks.append(texto[inicio:fin].strip())
        inicio = fin - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 80]

# ── Indexar un archivo ────────────────────────────────────────────────────────

def indexar_archivo(ruta: Path, coleccion=None):
    ext = ruta.suffix.lower()
    if ext not in EXTRACTORES:
        log.info(f"  Formato no soportado: {ruta.name}")
        return 0

    texto = EXTRACTORES[ext](ruta)
    if not texto or len(texto.strip()) < 100:
        log.warning(f"  Sin texto extraíble: {ruta.name}")
        return 0

    chunks = chunk_texto(texto, ruta.name)
    if not chunks:
        return 0

    if coleccion is None:
        coleccion = get_coleccion()

    # Detectar fuente por nombre de archivo
    nombre = ruta.name.lower()
    if "dian" in nombre:
        fuente = "DIAN"
    elif "mincit" in nombre:
        fuente = "MinCIT"
    elif "vuce" in nombre:
        fuente = "VUCE"
    elif "can" in nombre or "comunidad" in nombre:
        fuente = "CAN"
    elif "diario" in nombre:
        fuente = "Diario Oficial"
    else:
        fuente = "Legislación"

    ids        = [f"{ruta.stem}_{i}" for i in range(len(chunks))]
    metadatas  = [
        {
            "archivo": ruta.name,
            "fuente":  fuente,
            "chunk":   i,
            "fecha_indexacion": datetime.now().isoformat()
        }
        for i in range(len(chunks))
    ]

    # ChromaDB maneja duplicados por ID (upsert)
    coleccion.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas
    )
    log.info(f"  ✓ {ruta.name} — {len(chunks)} fragmentos indexados")
    return len(chunks)

# ── Indexar carpeta completa ──────────────────────────────────────────────────

def indexar_carpeta(ruta_carpeta: Path):
    archivos = [
        f for f in ruta_carpeta.rglob("*")
        if f.is_file() and f.suffix.lower() in EXTRACTORES
    ]

    if not archivos:
        log.info("No se encontraron archivos para indexar.")
        return

    log.info(f"\nIndexando {len(archivos)} archivos en {ruta_carpeta}...\n")
    coleccion  = get_coleccion()
    total_chunks = 0

    for archivo in tqdm(archivos, desc="Indexando", unit="archivo"):
        total_chunks += indexar_archivo(archivo, coleccion)

    log.info(f"\n✓ Indexación completa: {total_chunks} fragmentos totales en ChromaDB\n")

# ── Entrada ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicial", action="store_true",
                        help="Indexar carpeta datos/legislacion completa")
    parser.add_argument("--archivo", type=str,
                        help="Indexar un archivo específico")
    args = parser.parse_args()

    if args.inicial:
        indexar_carpeta(LEG_DIR)
    elif args.archivo:
        indexar_archivo(Path(args.archivo))
    else:
        indexar_carpeta(LEG_DIR)
