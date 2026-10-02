"""Lee avisos de Bumeran y ZonaJobs (las dos son de la misma empresa, Jobint).

Sus páginas de búsqueda están detrás de Cloudflare y cargan los avisos con
JavaScript, así que no se pueden leer directo. Lo que sí publican es un
"sitemap": la lista oficial de todos sus avisos que arman para Google.
De cada link sacamos el título (y a veces la empresa, que viene pegada).
No trae ubicación ni fecha; la fecha la pone buscar.py (el día que lo vimos).
"""

import re

import requests

from .comun import HEADERS, modalidad


def bumeran(ahora):
    return _leer_sitemap("Bumeran", "https://www.bumeran.com.ar/sitemap_avisos_bum.xml")


def zonajobs(ahora):
    return _leer_sitemap("ZonaJobs", "https://www.zonajobs.com.ar/sitemap_avisos_zj.xml")


def _leer_sitemap(nombre, url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    links = re.findall(r"<loc>([^<]+/empleos/[^<]+)</loc>", resp.text)
    if not links:
        raise ValueError("el sitemap vino vacío o cambió de formato")
    return [_aviso(nombre, link) for link in links]


def _aviso(nombre, link):
    # ".../empleos/community-manager-frigonorte-1118464237.html" -> "Community manager frigonorte"
    slug = link.rsplit("/", 1)[-1]
    slug = re.sub(r"-?\d+\.html$", "", slug)
    titulo = " ".join(slug.replace("|", " | ").replace("-", " ").split())
    titulo = titulo[:1].upper() + titulo[1:]

    return {
        "titulo": titulo,
        "empresa": "",
        "ubicacion": "",
        "modalidad": modalidad(titulo),
        "fecha": None,  # buscar.py usa el día en que lo vimos por primera vez
        "fuente": nombre,
        "link": link,
    }
