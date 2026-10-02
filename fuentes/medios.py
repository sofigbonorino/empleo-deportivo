"""Bolsas de trabajo propias de empresas de medios.

Cada empresa usa una plataforma distinta para publicar búsquedas:
  - Clarín (Olé) y La Nación -> HiringRoom (página HTML)
  - Warner Bros. Discovery (TNT Sports) -> Workday (API pública en JSON)
  - Disney (ESPN) -> página de búsqueda de disneycareers.com

Todos los avisos salen con "de_medio": True. Como la empresa ya es un medio,
buscar.py solo les pide que el TÍTULO hable de deporte.
"""

import requests
from bs4 import BeautifulSoup

from .comun import HEADERS, fecha, modalidad


# ---------- HiringRoom ----------

def clarin(ahora):
    return _hiringroom("Clarín", "clarin", ahora)


def lanacion(ahora):
    return _hiringroom("La Nación", "lanacion", ahora)


def _hiringroom(empresa, subdominio, ahora):
    base = f"https://{subdominio}.hiringroom.com"
    resp = requests.get(base + "/jobs", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    avisos = []
    for a in soup.select('a[href^="/jobs/get_vacancy/"]'):
        titulo = a.select_one("h4")
        if not titulo:
            continue
        # Los renglones de la tarjeta: título, lugar, área, Full-time, Híbrido, ..., "Hace 2 días"
        partes = [p.strip() for p in a.get_text("|").split("|") if p.strip()]
        cuando = next((p for p in partes if p.lower().startswith("hace")), "")
        avisos.append({
            "titulo": " ".join(titulo.get_text(" ").split()),
            "empresa": empresa,
            "ubicacion": partes[1] if len(partes) > 1 else "",
            "modalidad": modalidad(" ".join(partes)),
            "fecha": fecha(cuando, ahora),
            "fuente": empresa,
            "link": base + a["href"],
            "de_medio": True,
        })
    if not avisos and "get_vacancy" not in resp.text:
        raise ValueError("la página cambió de formato")
    return avisos


# ---------- Workday (Warner Bros. Discovery) ----------

def warner(ahora):
    base = "https://warnerbros.wd5.myworkdayjobs.com"
    api = base + "/wday/cxs/warnerbros/global/jobs"
    vistos = {}
    for texto in ("Argentina", "Buenos Aires"):
        offset = 0
        while True:
            resp = requests.post(api, headers=HEADERS, timeout=20, json={
                "appliedFacets": {}, "limit": 20, "offset": offset, "searchText": texto,
            })
            resp.raise_for_status()
            datos = resp.json()
            for j in datos.get("jobPostings", []):
                lugar = j.get("locationsText", "")
                if "argentina" in lugar.lower() or "buenos aires" in lugar.lower():
                    vistos[j["externalPath"]] = j
            offset += 20
            if offset >= datos.get("total", 0) or offset >= 200:
                break

    return [{
        "titulo": j["title"],
        "empresa": "Warner Bros. Discovery",
        "ubicacion": j.get("locationsText", ""),
        "modalidad": modalidad(j.get("remoteType", "")),
        "fecha": fecha(j.get("postedOn", ""), ahora),
        "fuente": "Warner (TNT Sports)",
        "link": base + "/global" + ruta,
        "de_medio": True,
    } for ruta, j in vistos.items()]


# ---------- Disney (ESPN) ----------

def disney(ahora):
    base = "https://www.disneycareers.com"
    resp = requests.get(base + "/en/search-jobs/Argentina", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    avisos = []
    for a in soup.select("a[data-job-id]"):
        # Renglones: título | empresa del grupo | lugar | fecha
        partes = [p.strip() for p in a.get_text("|").split("|") if p.strip()]
        if len(partes) < 3:
            continue
        avisos.append({
            "titulo": partes[0],
            "empresa": partes[1],
            "ubicacion": " ".join(partes[2].split()),
            "modalidad": "Sin dato",
            "fecha": fecha(partes[-1], ahora),
            "fuente": "Disney (ESPN)",
            "link": base + a["href"],
            "de_medio": True,
        })
    return avisos
