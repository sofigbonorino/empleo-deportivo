"""Lee proyectos freelance de workana.com (todos remotos, de toda Latinoamérica).

La página de búsqueda trae los proyectos como datos JSON dentro de un
atributo del HTML (<search :results-initials="...">), así que no hace
falta "raspar" la página: leemos ese JSON directo.
"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup

from .comun import HEADERS, fecha

BASE = "https://www.workana.com"
BUSQUEDAS = ["deportes", "deportivo", "futbol", "periodista deportivo", "redactor deportes"]
# Workana ordena por relevancia y no por fecha: hay avisos de hoy en páginas
# del fondo, así que se recorren todas (hasta 10). Lo viejo lo descarta buscar.py.
PAGINAS_POR_BUSQUEDA = 10

PAISES = {
    "AR": "Argentina", "MX": "México", "CO": "Colombia", "CL": "Chile", "PE": "Perú",
    "UY": "Uruguay", "PY": "Paraguay", "BO": "Bolivia", "EC": "Ecuador", "VE": "Venezuela",
    "ES": "España", "US": "Estados Unidos", "BR": "Brasil", "CR": "Costa Rica",
    "PA": "Panamá", "DO": "Rep. Dominicana", "GT": "Guatemala", "NL": "Países Bajos",
    "IT": "Italia", "DE": "Alemania", "FR": "Francia", "GB": "Reino Unido", "CA": "Canadá",
}


def buscar(ahora):
    avisos = []
    for termino in BUSQUEDAS:
        for pagina in range(1, PAGINAS_POR_BUSQUEDA + 1):
            resp = requests.get(f"{BASE}/jobs", headers=HEADERS, timeout=20, params={
                "query": termino, "language": "es", "page": pagina,
            })
            resp.raise_for_status()
            nodo = BeautifulSoup(resp.text, "html.parser").find("search")
            if nodo is None or not nodo.get(":results-initials"):
                raise ValueError("la página cambió de formato")
            datos = json.loads(nodo[":results-initials"])

            for p in datos["results"]:
                titulo = BeautifulSoup(p["title"], "html.parser").get_text()
                span = BeautifulSoup(p["title"], "html.parser").find("span", title=True)
                if span:  # el texto visible viene cortado con "..."; el completo está en title=
                    titulo = span["title"]
                pais = re.search(r"country=([A-Z]{2})", p.get("country") or "")
                avisos.append({
                    "titulo": titulo,
                    "empresa": "",
                    "ubicacion": "Freelance" + (
                        f" · cliente de {PAISES.get(pais.group(1), pais.group(1))}" if pais else ""),
                    "modalidad": "Remoto",
                    "fecha": fecha(p.get("postedDate") or "", ahora),
                    "fuente": "Workana",
                    "link": f"{BASE}/job/{p['slug']}",
                    # Cliente de otro país: la página lo muestra en una solapa aparte
                    "exterior": bool(pais) and pais.group(1) != "AR",
                })

            time.sleep(1)
            if pagina >= datos["pagination"].get("pages", 1):
                break
    return avisos
