"""Busca avisos en todas las fuentes y guarda docs/jobs.json.

Pasos:
  1. Pide los avisos a cada fuente. Si una falla, anota el error y sigue.
  2. Filtro estricto: el aviso tiene que hablar de MEDIOS y de DEPORTE.
  3. Deduplica: mismo título + misma empresa = mismo aviso.
  4. Mezcla con el jobs.json anterior para recordar cuándo vimos cada aviso
     por primera vez (así la página sabe cuáles son "nuevos de hoy").
"""

import hashlib
import json
import re
import traceback
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fuentes import computrabajo, jobint, medios, workana

# Para sumar una fuente nueva: crear su función en fuentes/ y agregarla acá.
# Cada función recibe la hora actual y devuelve una lista de avisos.
FUENTES = [
    # Bolsas de trabajo generales
    ("Computrabajo", computrabajo.buscar),
    ("Bumeran", jobint.bumeran),
    ("ZonaJobs", jobint.zonajobs),
    ("Workana", workana.buscar),  # freelance remoto
    # Bolsas de trabajo propias de medios
    ("Clarín", medios.clarin),
    ("La Nación", medios.lanacion),
    ("Warner (TNT Sports)", medios.warner),
    ("Disney (ESPN)", medios.disney),
]

ARCHIVO = Path(__file__).parent / "docs" / "jobs.json"
ARGENTINA = timezone(timedelta(hours=-3))  # Argentina no tiene horario de verano
DIAS_SIN_VER_PARA_BORRAR = 7

# Palabras sin tildes y en minúscula (el texto se normaliza igual antes de comparar).
MEDIOS = re.compile(
    r"periodis|redact|\beditor|edicion|contenid|community|social media|redes sociales"
    r"|locut|cronista|comunicad|comunicacion|prensa|productor|produccion|conductor"
    r"|relator|comentarista|guionista|creador|streaming|\bmedios\b|audiovisual|columnista"
)
DEPORTE = re.compile(
    r"deport|(?<!tran)sport|futbol|\bclub\b|hockey|rugby|tenis|basquet|\bvoley|boxeo"
    r"|automovilismo|\bgolf\b|\bpadel\b|\bliga\b|\bole\b|\btyc\b|\bespn\b|fitness|running"
)

# Zona: su hermano vive en AMBA. Los presenciales/híbridos tienen que ser en
# CABA o provincia de Buenos Aires, menos las ciudades lejanas de esta lista.
AMBA = re.compile(r"capital federal|caba|ciudad autonoma|buenos aires|gba|amba")
LEJOS_DE_AMBA = re.compile(
    r"mar del plata|bahia blanca|tandil|pinamar|costa esmeralda|villa gesell|necochea"
    r"|olavarria|azul|junin|pergamino|san nicolas|tres arroyos|chivilcoy|mar de ajo"
    r"|san clemente|miramar|balcarce|bragado|9 de julio|nueve de julio|trenque lauquen"
)


def main():
    ahora = datetime.now(ARGENTINA)
    hoy = ahora.date().isoformat()

    # 1. Pedir avisos a cada fuente, sin que una caída frene al resto
    crudos = []
    estado = {}
    for nombre, buscar_en in FUENTES:
        try:
            avisos = buscar_en(ahora)
            crudos.extend(avisos)
            estado[nombre] = {"ok": True, "leidos": len(avisos)}
            print(f"OK    {nombre}: {len(avisos)} avisos leídos")
        except Exception as e:
            traceback.print_exc()
            estado[nombre] = {"ok": False, "error": str(e)[:200]}
            print(f"FALLÓ {nombre}: {e}")

    # 2 y 3. Filtrar (tema y zona) y deduplicar
    nuevos = {}
    for a in crudos:
        if not (es_relevante(a) and en_zona(a)):
            continue
        a["id"] = clave(a)
        nuevos.setdefault(a["id"], a)  # si ya estaba, se queda el primero
    print(f"Pasaron el filtro: {len(nuevos)}")

    # 4. Mezclar con lo que ya teníamos
    anteriores = {a["id"]: a for a in leer_anterior()}
    for id_, a in nuevos.items():
        viejo = anteriores.get(id_)
        a["primera_vez"] = viejo["primera_vez"] if viejo else hoy
        a["ultima_vez"] = hoy
        a["fecha"] = a["fecha"] or a["primera_vez"]  # fuentes que no traen fecha
        anteriores[id_] = a

    limite = (ahora - timedelta(days=DIAS_SIN_VER_PARA_BORRAR)).date().isoformat()
    # Los filtros se vuelven a pasar sobre todo lo guardado: si cambiamos una
    # regla, los avisos viejos que ya no la cumplen también se van.
    avisos = [a for a in anteriores.values()
              if a["ultima_vez"] >= limite and es_relevante(a) and en_zona(a)]
    avisos.sort(key=lambda a: (a["primera_vez"], a["fecha"]), reverse=True)

    ARCHIVO.parent.mkdir(exist_ok=True)
    ARCHIVO.write_text(json.dumps({
        "actualizado": ahora.isoformat(timespec="minutes"),
        "fuentes": estado,
        "avisos": avisos,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    hoy_nuevos = sum(a["primera_vez"] == hoy for a in avisos)
    print(f"Guardados {len(avisos)} avisos ({hoy_nuevos} nuevos hoy) en {ARCHIVO}")


def normalizar(texto):
    """Minúsculas y sin tildes: 'Fútbol' -> 'futbol'."""
    sin_tildes = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def es_relevante(aviso):
    if aviso.get("de_medio"):
        # Viene de la bolsa de trabajo de un medio: ya sabemos que es de medios,
        # alcanza con que el título hable de deporte (ej. "Pasantías Olé").
        return bool(DEPORTE.search(normalizar(aviso["titulo"])))
    texto = normalizar(aviso["titulo"] + " " + aviso["empresa"])
    return bool(MEDIOS.search(texto) and DEPORTE.search(texto))


def en_zona(aviso):
    """Remoto o sin ubicación: sirve. Presencial/híbrido: solo si es en AMBA."""
    if aviso["modalidad"] == "Remoto" or not aviso["ubicacion"]:
        return True
    lugar = normalizar(aviso["ubicacion"])
    return bool(AMBA.search(lugar)) and not LEJOS_DE_AMBA.search(lugar)


def clave(aviso):
    """Mismas palabras en título + empresa = mismo aviso, sin importar orden ni signos.
    Así 'community-manager-frigonorte' (Bumeran) y 'Community manager | Frigonorte'
    (Computrabajo) dan la misma clave."""
    palabras = re.findall(r"[a-z0-9]+", normalizar(aviso["titulo"] + " " + aviso["empresa"]))
    base = " ".join(sorted(set(palabras)))
    return hashlib.md5(base.encode()).hexdigest()[:12]


def leer_anterior():
    if not ARCHIVO.exists():
        return []
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))["avisos"]
    except (ValueError, KeyError):
        return []


if __name__ == "__main__":
    main()
