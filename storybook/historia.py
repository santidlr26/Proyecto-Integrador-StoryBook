"""Escribe el cuento con el LLM: primero la 'biblia' (personaje, lugar, estilo, plan) y luego cada escena."""

import re
import unicodedata

import modelos

# True: la descripción fija del personaje, el lugar y el estilo van en TODAS las imágenes y se usa la
# misma semilla (configuración final). False: línea base para comparar (solo el prompt de la escena).
CONSISTENCIA = True
SEMILLA = 1234
PALABRAS = 90  # longitud pedida para el texto de cada escena (sube o baja este número)
ESPANOL = {"el", "la", "los", "las", "de", "que", "y", "en", "un", "una", "con", "por", "se", "su", "a", "del", "al"}
NEGATIVO = "text, letters, watermark, blurry, lowres, deformed, bad anatomy, extra limbs, cropped"


def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _campos(texto, claves):
    """Lee líneas 'CLAVE: valor'. Más fiable con modelos pequeños que pedir JSON (tolera tildes y negritas)."""
    texto = unicodedata.normalize("NFC", re.sub(r"<think>.*?</think>", "", texto, flags=re.S))
    plano = _sin_tildes(texto)
    marcas = list(re.finditer(r"(?im)^[\s*#-]*(" + "|".join(claves) + r")[\s*]*:[ \t]*", plano))
    campos = {}
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        campos[m.group(1).upper()] = texto[m.end():fin].strip().strip("*").strip()
    return campos


def _pedir(mensajes, claves, validar=None, max_tokens=500, intentos=3):
    """Llama al modelo hasta obtener todas las claves y que `validar` no encuentre problemas.
    Si falla, se le devuelve su respuesta junto con el problema concreto para que la corrija."""
    ultimo = None
    for _ in range(intentos):
        respuesta = modelos.escribir(mensajes, max_tokens)
        campos = _campos(respuesta, claves)
        if all(campos.get(k) for k in claves):
            ultimo = campos
            problema = validar(campos) if validar else ""
            if not problema:
                return campos
        else:
            problema = "No usaste el formato pedido: una línea por cada clave, con 'CLAVE: valor'."
        mensajes = mensajes + [{"role": "assistant", "content": respuesta},
                               {"role": "user", "content": f"{problema} Escríbelo de nuevo completo."}]
    if ultimo is None:
        raise RuntimeError("El modelo de texto no devolvió el formato esperado. Intenta de nuevo.")
    return ultimo  # formato correcto pero con detalles por mejorar: se acepta


def crear_biblia(idea, genero):
    claves = ["TITULO", "PROTAGONISTA", "APARIENCIA", "LUGAR", "ESTILO"] + [f"ESCENA{i}" for i in range(1, 6)]
    pedido = f"""Eres un escritor de cuentos. Idea: "{idea}". Tipo de cuento: {genero}.
Aunque la idea esté en otro idioma, el cuento se escribe en español.
Responde SOLO con estas 10 líneas, una por línea, sin nada más:
TITULO: título corto en español
PROTAGONISTA: nombre propio del protagonista
APARIENCIA: aspecto físico fijo del protagonista, en inglés, máximo 20 palabras (edad, pelo, ropa con colores)
LUGAR: lugar principal de la historia, en inglés, máximo 10 palabras
ESTILO: estilo de ilustración acorde al tipo de cuento, en inglés, máximo 10 palabras
ESCENA1: qué ocurre al inicio (una frase en español)
ESCENA2: primer obstáculo o descubrimiento
ESCENA3: la situación se complica
ESCENA4: momento decisivo
ESCENA5: desenlace"""
    return _pedir([{"role": "user", "content": pedido}], claves)


def crear_escena(biblia, genero, numero, anteriores):
    nombre = biblia["PROTAGONISTA"]
    plan = "\n".join(f"{i}. {biblia[f'ESCENA{i}']}" for i in range(1, 6))
    previo = "\n".join(f"Escena {i}: {t}" for i, t in enumerate(anteriores, 1)) or "(todavía no hay)"
    pedido = f"""Cuento "{biblia['TITULO']}" ({genero}). Protagonista: {nombre}.
Plan del cuento:
{plan}

Escenas ya escritas (continúa desde ellas, sin repetirlas):
{previo}

Escribe SOLO la escena {numero}: {biblia[f'ESCENA{numero}']}
Responde SOLO con estas 3 líneas:
NARRACION: un párrafo de unas {PALABRAS} palabras (5 o 6 frases) EN ESPAÑOL que cuente la escena como un cuento, no como un resumen: qué hace {nombre}, qué ve, qué oye y qué siente
IMAGEN: en inglés, máximo 20 palabras: qué ocurre y dónde (no describas el aspecto del protagonista)
SONIDO: en inglés, máximo 8 palabras: sonidos ambientales de la escena"""

    def valida(c):
        texto = _sin_tildes(c["NARRACION"]).lower()
        palabras = texto.split()
        if len(palabras) < PALABRAS * 0.6:
            return f"La narración tiene {len(palabras)} palabras y debe tener unas {PALABRAS}: añade más detalles y frases."
        if _sin_tildes(nombre.split()[0]).lower() not in texto:
            return f"La narración debe nombrar al protagonista, {nombre}."
        if sum(p in ESPANOL for p in palabras) < len(palabras) * 0.15:
            return "La narración debe estar escrita en español."
        return ""

    return _pedir([{"role": "user", "content": pedido}], ["NARRACION", "IMAGEN", "SONIDO"], valida)


def prompt_imagen(biblia, escena, numero):
    """Devuelve (prompt, semilla). Con CONSISTENCIA, el personaje, lugar y estilo se repiten siempre."""
    if CONSISTENCIA:
        texto = f"{biblia['APARIENCIA']}, {escena['IMAGEN']}, {biblia['LUGAR']}, {biblia['ESTILO']}"
        return texto, SEMILLA
    return escena["IMAGEN"], SEMILLA + 101 * numero


def prompt_sonido(escena):
    return f"{escena['SONIDO']}, ambient soundscape, no vocals, no drums"
