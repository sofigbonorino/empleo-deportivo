"""Lee avisos de ar.computrabajo.com.

Computrabajo arma una página por búsqueda: /trabajo-de-<palabras>.
Cada aviso es un <article class="box_offer"> con título, empresa,
lugar, fecha y (a veces) un ícono que dice si es remoto.
"""

import re
import time

import requests
from bs4 import BeautifulSoup

from .comun import HEADERS, fecha

NOMBRE = "Computrabajo"
BASE = "https://ar.computrabajo.com"

# Buscamos amplio; el filtro estricto de buscar.py después limpia el ruido.
BUSQUEDAS = [
    "periodista deportivo", "redactor deportes", "editor deportivo",
    "productor contenido deportivo", "community manager deportes",
    "locutor deportivo", "cronista deportivo", "coordinador de contenido deportivo",
    "periodista", "redactor", "editor de contenido", "community manager",
    "locutor", "comunicador", "prensa", "creador de contenido",
    "deportes", "deportivo", "futbol",
]
PAGINAS_POR_BUSQUEDA = 2


def buscar(ahora):
    """Devuelve la lista de avisos (sin filtrar) de todas las búsquedas."""
    avisos = []
    sesion = requests.Session()
    sesion.headers.update(HEADERS)

    for termino in BUSQUEDAS:
        slug = termino.replace(" ", "-")
        for pagina in range(1, PAGINAS_POR_BUSQUEDA + 1):
            url = f"{BASE}/trabajo-de-{slug}"
            if pagina > 1:
                url += f"?p={pagina}"
            resp = sesion.get(url, timeout=20)
            resp.raise_for_status()
            encontrados = _leer_pagina(resp.text, ahora)
            avisos.extend(encontrados)
            time.sleep(1)  # pausa cortita para no saturar al sitio
            if not encontrados:
                break  # no hay más páginas para esta búsqueda

    return avisos


def _leer_pagina(html, ahora):
    soup = BeautifulSoup(html, "html.parser")
    avisos = []
    for art in soup.select("article.box_offer"):
        link = art.select_one("h2 a.js-o-link")
        if not link:
            continue
        renglones = art.select("p.fs16")
        empresa = _texto(renglones[0]) if len(renglones) > 0 else ""
        empresa = re.sub(r"^\d,\d\s+", "", empresa)  # saca el puntaje: "4,1 NewSport"
        ubicacion = _texto(renglones[1]) if len(renglones) > 1 else ""

        if art.select_one(".i_home"):
            modalidad = "Remoto"
        elif art.select_one(".i_home_office"):
            modalidad = "Híbrido"
        else:
            modalidad = "Presencial"

        avisos.append({
            "titulo": _texto(link),
            "empresa": empresa,
            "ubicacion": ubicacion,
            "modalidad": modalidad,
            "fecha": fecha(_texto(art.select_one("p.fc_aux")), ahora),
            "fuente": NOMBRE,
            "link": BASE + link["href"].split("#")[0],
        })
    return avisos


def _texto(nodo):
    if nodo is None:
        return ""
    return " ".join(nodo.get_text(" ").split())
