"""Los cuatro modelos de Hugging Face, siempre en CPU. Cada uno se carga la primera vez que se usa."""

import numpy as np
import torch

# --- Ajustes (cambia aquí el modelo o la calidad) ----------------------------
MODELO_TEXTO = "Qwen/Qwen3-0.6B"            # alternativa más capaz: "Qwen/Qwen3-4B-Instruct-2507" (más lento)
MODELO_IMAGEN = "CompVis/stable-diffusion-v1-4"
VOZ_REPO = "rhasspy/piper-voices"
VOZ_ARCHIVO = "es/es_ES/davefx/medium/es_ES-davefx-medium"
MODELO_SONIDO = "facebook/musicgen-small"

PASOS_IMAGEN = 15        # menos pasos = más rápido, menos detalle
TAMANO_IMAGEN = 512
SEGUNDOS_SONIDO = 8

_cargados = {}


def _normalizar(audio):
    audio = np.asarray(audio, dtype=np.float32).squeeze()
    pico = float(np.max(np.abs(audio))) if audio.size else 0.0
    return audio / pico * 0.7 if pico > 0 else audio


# --- Texto: Qwen3 -------------------------------------------------------------
def escribir(mensajes, max_tokens=400):
    if "texto" not in _cargados:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(MODELO_TEXTO)
        _cargados["texto"] = (tok, AutoModelForCausalLM.from_pretrained(MODELO_TEXTO).eval())
    tok, modelo = _cargados["texto"]
    texto = tok.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    entrada = tok([texto], return_tensors="pt")
    with torch.inference_mode():
        salida = modelo.generate(**entrada, max_new_tokens=max_tokens, do_sample=True,
                                 temperature=0.7, top_p=0.8, top_k=20)
    return tok.decode(salida[0][entrada["input_ids"].shape[1]:], skip_special_tokens=True)


# --- Imagen: Stable Diffusion ---------------------------------------------------
def dibujar(prompt, negativo, semilla):
    if "imagen" not in _cargados:
        from diffusers import DPMSolverMultistepScheduler, StableDiffusionPipeline
        pipe = StableDiffusionPipeline.from_pretrained(MODELO_IMAGEN, safety_checker=None,
                                                       requires_safety_checker=False)
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.set_progress_bar_config(disable=True)
        _cargados["imagen"] = pipe
    generador = torch.Generator().manual_seed(semilla)
    return _cargados["imagen"](prompt, negative_prompt=negativo, num_inference_steps=PASOS_IMAGEN,
                               width=TAMANO_IMAGEN, height=TAMANO_IMAGEN, generator=generador).images[0]


# --- Voz: Piper (español) ----------------------------------------------------------
def narrar(texto):
    if "voz" not in _cargados:
        from huggingface_hub import hf_hub_download
        from piper import PiperVoice
        onnx = hf_hub_download(VOZ_REPO, VOZ_ARCHIVO + ".onnx")
        hf_hub_download(VOZ_REPO, VOZ_ARCHIVO + ".onnx.json")  # queda junto al .onnx
        _cargados["voz"] = PiperVoice.load(onnx)
    voz = _cargados["voz"]
    trozos = list(voz.synthesize(texto))
    return trozos[0].sample_rate, _normalizar(np.concatenate([t.audio_float_array for t in trozos]))


# --- Sonido ambiente: MusicGen --------------------------------------------------------
def ambiente(prompt):
    if "sonido" not in _cargados:
        from transformers import AutoProcessor, MusicgenForConditionalGeneration
        _cargados["sonido"] = (AutoProcessor.from_pretrained(MODELO_SONIDO),
                               MusicgenForConditionalGeneration.from_pretrained(MODELO_SONIDO).eval())
    procesador, modelo = _cargados["sonido"]
    entrada = procesador(text=[prompt], padding=True, return_tensors="pt")
    with torch.inference_mode():
        audio = modelo.generate(**entrada, do_sample=True, guidance_scale=3.0,
                                max_new_tokens=SEGUNDOS_SONIDO * 50)
    return modelo.config.audio_encoder.sampling_rate, _normalizar(audio[0, 0].numpy())
