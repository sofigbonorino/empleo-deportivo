"""Cosas que usan varias fuentes."""

import re
from datetime import datetime, timedelta

# Nos presentamos como un navegador común; algunos sitios rechazan pedidos "anónimos".
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def fecha(txt, ahora):
    """Pasa textos como 'Hace 5 horas', 'Ayer', 'Hace 1 mes', '3 de septiembre',
    'Posted 2 Days Ago' o 'Sep. 25, 2026' a una fecha AAAA-MM-DD."""
    t = txt.lower().strip()
    n = re.search(r"\d+", t)
    n = int(n.group()) if n else 1

    if not t or "minut" in t or "hoy" in t or "today" in t:
        d = ahora
    elif "hora" in t or "hour" in t:
        d = ahora - timedelta(hours=n)
    elif "ayer" in t or "yesterday" in t:
        d = ahora - timedelta(days=1)
    elif "día" in t or "dia" in t or "day" in t:
        d = ahora - timedelta(days=n)
    elif "semana" in t or "week" in t:
        d = ahora - timedelta(weeks=n)
    elif "mes" in t or "month" in t:
        d = ahora - timedelta(days=30 * n)
    elif m := re.search(r"(\d+) de (\w+)", t):  # "3 de septiembre"
        if m.group(2) not in MESES:
            return ahora.date().isoformat()
        try:
            d = ahora.replace(month=MESES[m.group(2)], day=int(m.group(1)))
        except ValueError:  # ej. "29 de febrero" en un año no bisiesto
            return ahora.date().isoformat()
        if d > ahora:  # "20 de diciembre" leído en enero es del año pasado
            d = d.replace(year=d.year - 1)
    else:  # "Sep. 25, 2026" (inglés)
        try:
            limpio = txt.replace(".", "").replace("Sept", "Sep").strip()
            return datetime.strptime(limpio, "%b %d, %Y").date().isoformat()
        except ValueError:
            return ahora.date().isoformat()
    return d.date().isoformat()


def modalidad(txt):
    t = txt.lower()
    if "híbrid" in t or "hibrid" in t or "hybrid" in t or "presencial y remoto" in t:
        return "Híbrido"
    if "remot" in t or "home office" in t:
        return "Remoto"
    if "presencial" in t or "on-site" in t or "onsite" in t:
        return "Presencial"
    return "Sin dato"
