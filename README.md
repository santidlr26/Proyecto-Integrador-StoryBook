# Storybook
## Integrantes:
Jairo Andres Niño Santos /
/ David Santiago Del Rio Mosquera
/ Frank Erick Joel Diaz Albarracin


Aplicación local que, a partir de una **idea** y un **tipo de cuento**, genera un cuento de **cinco escenas**.
Cada escena tiene texto, ilustración, narración con voz y sonido ambiente. La escena 1 se muestra en cuanto
está lista, mientras se genera la siguiente; se navega con **Anterior / Siguiente**.
Todo corre en **CPU**, sin APIs de pago y sin conexión a Internet después de la primera descarga de modelos.

## Modelos (Hugging Face)

| Función | Modelo | Licencia |
|---|---|---|
| Texto | `Qwen/Qwen3-0.6B` | Apache 2.0 |
| Imagen | `CompVis/stable-diffusion-v1-4` | CreativeML OpenRAIL-M |
| Voz | Piper, voz `es_ES-davefx-medium` (`rhasspy/piper-voices`) | Ver la tarjeta de la voz |
| Sonido ambiente | `facebook/musicgen-small` | CC BY-NC 4.0 (solo uso no comercial) |

Verifica las licencias vigentes en cada repositorio. Los modelos se cambian en las primeras líneas de `modelos.py`.

## Instalación

1. Instala [uv](https://docs.astral.sh/uv/getting-started/installation/) (descarga Python 3.12 por su cuenta si hace falta).
2. En la carpeta del proyecto:

```bash
uv sync
uv run python app.py
```

3. Abre la dirección que aparece en la terminal (normalmente http://127.0.0.1:7860).

La primera vez se descargan los modelos (unos 10 GB) a la caché de Hugging Face (`~/.cache/huggingface`,
o la carpeta de `HF_HOME`). Después se puede trabajar sin conexión:
`export HF_HUB_OFFLINE=1` (PowerShell: `$env:HF_HUB_OFFLINE=1`).

Si `CompVis/stable-diffusion-v1-4` pide aceptar los términos, inicia sesión con `huggingface-cli login`.

## Uso

1. Escribe la idea, por ejemplo: *Un faro abandonado donde cada noche se enciende una luz sola*.
2. Elige o escribe el tipo de cuento (Terror, Fantasía, Misterio, Aventura, Ciencia ficción, Infantil).
3. Pulsa **Generar cuento**. Cada escena se completa (texto, imagen, voz, sonido) antes de pasar a la siguiente.
4. Usa **Anterior / Siguiente** para recorrer las escenas y los reproductores para oír la narración y el ambiente.

Los archivos quedan en `salida/<fecha>/` (`escenaN.png`, `escenaN_voz.wav`, `escenaN_sonido.wav`). En la terminal se
imprimen los tiempos de cada paso y el prompt exacto de cada imagen (útil como evidencia para el informe).

## Requisitos

- CPU de 4 núcleos o más y **16 GB de RAM** recomendados (los cuatro modelos permanecen cargados), ~12 GB de disco.
- Sin GPU. Cada escena tarda varios minutos en CPU; los tiempos reales dependen del equipo (anótalos de la terminal).
- Para acelerar: baja `PASOS_IMAGEN` o `TAMANO_IMAGEN` en `modelos.py`. Para un relato más coherente prueba
  `Qwen/Qwen3-4B-Instruct-2507` (necesita más RAM y es más lento).

## Consistencia entre escenas

- **Texto:** primero se crea un plan (título, protagonista, lugar, estilo y las cinco ideas); cada escena se escribe
  viendo el plan y las escenas anteriores. Se reintenta si no nombra al protagonista.
- **Imagen:** la descripción fija del protagonista, el lugar y el estilo se repiten en el prompt de las cinco imágenes,
  con la misma semilla.
- **Comparar configuraciones:** en `historia.py`, `CONSISTENCIA = False` genera cada imagen solo con el prompt de la
  escena y semilla distinta (línea base). Genera el mismo cuento con `True` y `False` y compara las capturas.

## Estructura

```
app.py        interfaz y flujo escena por escena
historia.py   plan y escenas con el modelo de texto, prompts de imagen y sonido
modelos.py    los cuatro modelos (texto, imagen, voz, sonido)
```

## Licencia

Código bajo licencia MIT (`LICENSE`). Los modelos mantienen sus propias licencias.
