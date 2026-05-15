"""
monitor.py — Monitoreo automático de fuentes normativas colombianas
Revisa cada 6 horas: Diario Oficial, DIAN, MinCIT, VUCE, CAN
"""

import os, sys, json, time, logging, hashlib, argparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.insert(0, str(Path(__file__).parent))
from indexador import indexar_archivo

BASE_DIR   = Path(__file__).parent.parent
DATOS_DIR  = BASE_DIR / "datos"
DESC_DIR   = DATOS_DIR / "descargas"
LEG_DIR    = DATOS_DIR / "legislacion"
VISTO_FILE = DATOS_DIR / "vistos.json"
LOG_FILE   = BASE_DIR  / "logs" / "monitor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# ── Persistencia de URLs ya procesadas ───────────────────────────────────────

def cargar_vistos():
    if VISTO_FILE.exists():
        return set(json.loads(VISTO_FILE.read_text(encoding="utf-8")))
    return set()

def guardar_vistos(vistos):
    VISTO_FILE.write_text(json.dumps(list(vistos)), encoding="utf-8")

# ── Descargador genérico ──────────────────────────────────────────────────────

def descargar_pdf(url: str, nombre: str, vistos: set) -> Path | None:
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    if url_hash in vistos:
        return None

    try:
        r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            destino = DESC_DIR / f"{nombre}_{url_hash}.pdf"
        else:
            destino = DESC_DIR / f"{nombre}_{url_hash}.html"

        destino.write_bytes(r.content)
        vistos.add(url_hash)
        log.info(f"  ↓ Descargado: {destino.name}")
        return destino
    except Exception as e:
        log.warning(f"  ! No se pudo descargar {url}: {e}")
        return None

# ── Scrapers por fuente ───────────────────────────────────────────────────────

def scrape_diario_oficial(vistos: set) -> list[Path]:
    """Diario Oficial - imprenta.gov.co"""
    descargados = []
    urls = [
        "https://www.imprenta.gov.co/diariop/diario.nivel_3?p_optp=DO",
        "https://www.suin-juriscol.gov.co/legislacion/decretos.html",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower() and any(
                    k in href.lower() for k in ["decreto", "resolucion", "circular", "diario"]
                ):
                    full = href if href.startswith("http") else f"https://www.imprenta.gov.co{href}"
                    f = descargar_pdf(full, "diario_oficial", vistos)
                    if f:
                        descargados.append(f)
        except Exception as e:
            log.warning(f"Diario Oficial error: {e}")
    return descargados

def scrape_dian(vistos: set) -> list[Path]:
    """DIAN - resoluciones y conceptos de comercio exterior"""
    descargados = []
    urls = [
        "https://www.dian.gov.co/normatividad/Paginas/ResolucNetd.aspx",
        "https://www.dian.gov.co/normatividad/Paginas/Circular-Externa.aspx",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower():
                    full = href if href.startswith("http") else f"https://www.dian.gov.co{href}"
                    f = descargar_pdf(full, "dian", vistos)
                    if f:
                        descargados.append(f)
        except Exception as e:
            log.warning(f"DIAN error: {e}")
    return descargados

def scrape_mincit(vistos: set) -> list[Path]:
    """MinCIT - resoluciones de comercio exterior"""
    descargados = []
    urls = [
        "https://www.mincit.gov.co/normatividad/resoluciones.aspx",
        "https://www.mincit.gov.co/normatividad/decretos.aspx",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower():
                    full = href if href.startswith("http") else f"https://www.mincit.gov.co{href}"
                    f = descargar_pdf(full, "mincit", vistos)
                    if f:
                        descargados.append(f)
        except Exception as e:
            log.warning(f"MinCIT error: {e}")
    return descargados

def scrape_vuce(vistos: set) -> list[Path]:
    """VUCE - ventanilla única de comercio exterior"""
    descargados = []
    urls = [
        "https://vuce.gov.co/normatividad/",
        "https://www.mincit.gov.co/comercioexterior/tramites-de-comercio-exterior/vuce.aspx",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower():
                    full = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                    f = descargar_pdf(full, "vuce", vistos)
                    if f:
                        descargados.append(f)
        except Exception as e:
            log.warning(f"VUCE error: {e}")
    return descargados

def scrape_can(vistos: set) -> list[Path]:
    """CAN - Comunidad Andina y Arancel Externo Común"""
    descargados = []
    urls = [
        "https://www.comunidadandina.org/decisiones/",
        "https://www.comunidadandina.org/resoluciones/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower():
                    full = href if href.startswith("http") else f"https://www.comunidadandina.org{href}"
                    f = descargar_pdf(full, "can", vistos)
                    if f:
                        descargados.append(f)
        except Exception as e:
            log.warning(f"CAN error: {e}")
    return descargados

# ── Ciclo principal ───────────────────────────────────────────────────────────

SCRAPERS = {
    "Diario Oficial": scrape_diario_oficial,
    "DIAN":           scrape_dian,
    "MinCIT":         scrape_mincit,
    "VUCE":           scrape_vuce,
    "CAN / Arancel":  scrape_can,
}

def ciclo_completo():
    log.info("=" * 55)
    log.info(f"Iniciando ciclo de monitoreo — {datetime.now():%Y-%m-%d %H:%M}")
    log.info("=" * 55)

    DESC_DIR.mkdir(parents=True, exist_ok=True)
    LEG_DIR.mkdir(parents=True, exist_ok=True)

    vistos = cargar_vistos()
    total_nuevos = 0

    for nombre, scraper in SCRAPERS.items():
        log.info(f"\nRevisando {nombre}...")
        nuevos = scraper(vistos)
        if nuevos:
            log.info(f"  → {len(nuevos)} documento(s) nuevo(s)")
            for f in nuevos:
                try:
                    indexar_archivo(f)
                    total_nuevos += 1
                except Exception as e:
                    log.warning(f"  ! Error indexando {f.name}: {e}")
        else:
            log.info("  → Sin novedades")

    guardar_vistos(vistos)
    log.info(f"\nCiclo completo. {total_nuevos} documento(s) nuevos indexados.")
    log.info(f"Próxima revisión en 6 horas.\n")

    return total_nuevos

# ── Entrada ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ahora", action="store_true", help="Ejecutar ciclo inmediato sin scheduler")
    args = parser.parse_args()

    if args.ahora:
        ciclo_completo()
    else:
        # Primer ciclo al arrancar, luego cada 6 horas
        ciclo_completo()
        scheduler = BlockingScheduler()
        scheduler.add_job(ciclo_completo, "interval", hours=6)
        log.info("Scheduler activo. Revisando cada 6 horas.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            log.info("Monitor detenido.")
