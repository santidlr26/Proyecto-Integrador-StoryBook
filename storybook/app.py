"""Interfaz: se genera una escena completa (texto, imagen, voz y sonido), se muestra y se pasa a la siguiente."""

import time
from pathlib import Path

import gradio as gr
import soundfile as sf

import historia
import modelos

SALIDA = Path("salida").resolve()
TIPOS = ["Terror", "Fantasía", "Misterio", "Aventura", "Ciencia ficción", "Infantil"]
N = 5

CSS = """
.gradio-container {max-width: 980px !important; margin: auto}
footer {display: none !important}
"""

with gr.Blocks(title="Storybook") as demo:
    gr.Markdown("# Storybook\nGenera un cuento de cinco escenas con imagen, narración y sonido ambiente. "
                "Todo se ejecuta en este equipo.")
    idea = gr.Textbox(label="Idea de la historia", lines=3, max_length=500)
    tipo = gr.Dropdown(TIPOS, value="Fantasía", allow_custom_value=True, label="Tipo de cuento")
    boton = gr.Button("Generar cuento", variant="primary")
    estado = gr.Markdown()

    escenas = gr.State([])   # escenas ya listas: [{texto, imagen, voz, sonido}, ...]
    actual = gr.State(0)     # escena que se está viendo

    titulo = gr.Markdown()
    contador = gr.Markdown()
    with gr.Row():
        imagen = gr.Image(label="Ilustración", interactive=False, height=420)
        with gr.Column():
            texto = gr.Textbox(label="Texto", lines=8, interactive=False)
            voz = gr.Audio(label="Narración", interactive=False)
            sonido = gr.Audio(label="Sonido ambiente", interactive=False, loop=True)
    with gr.Row():
        anterior = gr.Button("Anterior")
        siguiente = gr.Button("Siguiente")

    visor = [contador, imagen, texto, voz, sonido]


def mostrar(lista, i):
    """Valores del visor para la escena i (índice desde 0)."""
    e = lista[i]
    return [f"Escena {i + 1} de {N}", e["imagen"], e["texto"], e["voz"], e["sonido"]]


def mover(lista, i, paso):
    nuevo = i + paso
    if not 0 <= nuevo < len(lista):
        if paso > 0 and i < N - 1:
            gr.Info("Esa escena todavía se está generando.")
        return [i] + [gr.update()] * len(visor)
    return [nuevo] + mostrar(lista, nuevo)


def generar(idea_txt, tipo_txt):
    idea_txt, tipo_txt = (idea_txt or "").strip(), (tipo_txt or "").strip()
    if not idea_txt or not tipo_txt:
        raise gr.Error("Escribe la idea de la historia y el tipo de cuento.")

    # Orden de las salidas: boton, estado, titulo, escenas, actual, *visor
    def salida(msg, activo=False, nombre=None, lista=None, i=None, vista=None):
        return [gr.update(interactive=activo), msg,
                gr.update() if nombre is None else nombre,
                gr.update() if lista is None else lista,
                gr.update() if i is None else i,
                *(vista or [gr.update()] * len(visor))]

    yield salida("Escribiendo el plan del cuento...", nombre="", lista=[], i=0,
                 vista=["", None, "", None, None])

    carpeta = SALIDA / time.strftime("%Y%m%d-%H%M%S")
    carpeta.mkdir(parents=True, exist_ok=True)
    listas, anteriores = [], []
    try:
        biblia = historia.crear_biblia(idea_txt, tipo_txt)
        nombre = f"## {biblia['TITULO']}"
        for n in range(1, N + 1):
            t = [time.time()]
            yield salida(f"Escena {n} de {N}: escribiendo el texto...", nombre=nombre)
            escena = historia.crear_escena(biblia, tipo_txt, n, anteriores)
            anteriores.append(escena["NARRACION"])
            t.append(time.time())

            yield salida(f"Escena {n} de {N}: dibujando la ilustración...")
            prompt, semilla = historia.prompt_imagen(biblia, escena, n)
            ruta_img = carpeta / f"escena{n}.png"
            modelos.dibujar(prompt, historia.NEGATIVO, semilla).save(ruta_img)
            t.append(time.time())

            yield salida(f"Escena {n} de {N}: grabando la narración...")
            sr, audio = modelos.narrar(escena["NARRACION"])
            ruta_voz = carpeta / f"escena{n}_voz.wav"
            sf.write(ruta_voz, audio, sr)
            t.append(time.time())

            yield salida(f"Escena {n} de {N}: creando el sonido ambiente...")
            sr, audio = modelos.ambiente(historia.prompt_sonido(escena))
            ruta_sonido = carpeta / f"escena{n}_sonido.wav"
            sf.write(ruta_sonido, audio, sr)
            t.append(time.time())

            print(f"escena {n}: texto {t[1] - t[0]:.0f} s, imagen {t[2] - t[1]:.0f} s, voz {t[3] - t[2]:.0f} s, "
                  f"sonido {t[4] - t[3]:.0f} s | prompt de imagen: {prompt}")
            listas.append({"texto": escena["NARRACION"], "imagen": str(ruta_img),
                           "voz": str(ruta_voz), "sonido": str(ruta_sonido)})
            fin = "Cuento terminado." if n == N else f"Escena {n} lista. Generando la siguiente..."
            # La primera escena se muestra sola; las demás se consultan con Anterior / Siguiente.
            yield salida(fin, activo=n == N, lista=list(listas),
                         vista=mostrar(listas, 0) if n == 1 else None)
    except Exception as error:  # se informa el problema sin cerrar la aplicación
        yield salida(f"No se pudo completar el cuento: {error}", activo=True)


with demo:
    boton.click(generar, [idea, tipo], [boton, estado, titulo, escenas, actual, *visor])
    anterior.click(lambda l, i: mover(l, i, -1), [escenas, actual], [actual, *visor])
    siguiente.click(lambda l, i: mover(l, i, +1), [escenas, actual], [actual, *visor])

if __name__ == "__main__":
    demo.queue().launch(css=CSS, theme=gr.themes.Base(primary_hue="slate", neutral_hue="slate"),
                        allowed_paths=[str(SALIDA)])
