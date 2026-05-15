# RAG Comercio Exterior Colombia
## Guía de uso — Paso a paso

---

## ¿Qué hace este sistema?

Revisa automáticamente las páginas oficiales (Diario Oficial, DIAN, MinCIT,
VUCE y CAN) cada 6 horas, descarga las normas nuevas y las indexa. Cuando
tú haces una pregunta, el sistema busca los fragmentos más relevantes y los
envía a Claude para que te responda citando la fuente exacta.

---

## INSTALACIÓN (solo la primera vez)

### Requisito previo: Python

1. Ve a https://www.python.org/downloads/
2. Descarga la última versión (botón amarillo grande)
3. Ejecuta el instalador
4. ⚠️ **IMPORTANTE**: Marca la casilla "Add Python to PATH" antes de instalar

### Instalar el sistema

1. Descomprime la carpeta `rag_comercio_exterior`
2. Abre la carpeta
3. Doble clic en **`1_INSTALAR.bat`**
4. Sigue las instrucciones en pantalla
5. Cuando te pida la API key, ve a https://console.anthropic.com/ y cópiala

La instalación toma entre 3 y 8 minutos dependiendo de tu conexión.

---

## USO DIARIO

### Iniciar el sistema

Doble clic en **`2_INICIAR.bat`**

El navegador se abre automáticamente con la interfaz. Mantén la ventana negra
abierta mientras usas el sistema.

### Hacer una consulta

Escribe tu pregunta en el cuadro de texto y presiona Enter. Ejemplos:

- "¿Qué documentos necesito para importar maquinaria industrial?"
- "¿Cuál es el arancel para el código arancelario 8471.30?"
- "¿Qué dice la última resolución DIAN sobre vistos buenos?"
- "Requisitos VUCE para exportar café"
- "¿Cómo aplica el Arancel Externo Común de la CAN a productos textiles?"

### Actualizar normas manualmente

Si salió una norma importante y no quieres esperar 6 horas:
- Clic en **"↻ Buscar normas nuevas ahora"** en el panel izquierdo, o
- Doble clic en **`3_ACTUALIZAR_AHORA.bat`**

### Agregar tus documentos existentes

Copia tus archivos PDF/Word a la carpeta:

    rag_comercio_exterior\datos\legislacion\

Luego ejecuta `3_ACTUALIZAR_AHORA.bat` para indexarlos.

---

## SOLUCIÓN DE PROBLEMAS

### "No hay API key configurada"
Abre el archivo `config.env` con el Bloc de notas y reemplaza
`TU_API_KEY_AQUI` con tu clave real de https://console.anthropic.com/

### "La base de legislación está vacía"
Ejecuta `3_ACTUALIZAR_AHORA.bat` para descargar las normas por primera vez.
También puedes copiar tus archivos a `datos\legislacion\` y ejecutar el bat.

### El navegador no abre
Abre el navegador manualmente y ve a: http://localhost:5000

### Error al instalar
Verifica que Python esté instalado con `python --version` en el Símbolo del
sistema (cmd). Si no aparece, reinstala Python marcando "Add Python to PATH".

---

## ESTRUCTURA DE ARCHIVOS

```
rag_comercio_exterior\
├── 1_INSTALAR.bat          ← Ejecutar solo una vez
├── 2_INICIAR.bat           ← Ejecutar cada vez que quieras usar el sistema
├── 3_ACTUALIZAR_AHORA.bat  ← Forzar búsqueda de normas nuevas
├── config.env              ← API key de Anthropic (no compartir)
├── README.md               ← Esta guía
├── core\
│   ├── servidor.py         ← Backend principal
│   ├── monitor.py          ← Scraper automático de fuentes
│   └── indexador.py        ← Procesador de documentos
├── ui\
│   └── index.html          ← Interfaz web
├── datos\
│   ├── legislacion\        ← Pon aquí tus documentos propios
│   ├── descargas\          ← Normas descargadas automáticamente
│   └── vectordb\           ← Base de datos vectorial (no tocar)
└── logs\
    ├── monitor.log         ← Registro de monitoreo
    ├── indexador.log       ← Registro de indexación
    └── servidor.log        ← Registro del servidor
```

---

## COSTOS APROXIMADOS

- **Python, ChromaDB, modelo de embeddings**: GRATIS
- **API de Anthropic (Claude)**: ~$0.003 USD por consulta (menos de 1 centavo)
  Con uso normal (20 consultas/día) serían menos de $2 USD al mes.

---

## FUENTES MONITOREADAS

| Fuente | URL |
|--------|-----|
| Diario Oficial | imprenta.gov.co |
| DIAN | dian.gov.co |
| MinCIT | mincit.gov.co |
| VUCE | vuce.gov.co |
| CAN / Arancel Externo Común | comunidadandina.org |

---

*Sistema construido con Python · ChromaDB · Sentence Transformers · Claude API*
