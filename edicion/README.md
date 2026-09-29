# Edición del video final — Pitch institucional BeCode

Resultado: `../Video PITCH BeCode FINAL.mp4` (1920×1080, 30 fps, H.264 + AAC 256 kbps, ≈4:32, −15 LUFS).

## Estructura

| Tramo | Material | Duración aprox. |
|---|---|---|
| 1. Pitch inicial | `Video PITCH Inicial.mov` (4.35 s → 38.95 s; se quitan la toma falsa del inicio y los festejos del final) | 0:00 – 0:34 |
| Transición | Tarjeta KODU · "De una idea a una experiencia interactiva" | 0:34 – 0:36 |
| 2. Kodu | `Voz en off Kodu.mp4` + fragmentos de `Video Kodu DEMO.mp4` | 0:36 – 1:20 |
| Transición | KODU "Recursos didácticos interactivos" → TESTRA "Evaluaciones digitales con contexto" | 1:20 – 1:23 |
| 3. Testra | `Voz en off Testra.mp4` + `Video testra DEMO.mp4` | 1:23 – 2:03 |
| Transición | TESTRA → ECHO "Reuniones y seguimiento" | 2:03 – 2:05 |
| 4. Echo | `Voz en off ECHO` + `Video Echo DEMO.mp4` | 2:05 – 2:47 |
| Puente | "Menos carga administrativa. Más tiempo para escuchar, conversar y acompañar." → "Un ecosistema para la escuela" | 2:47 – 2:52 |
| 5. Pitch final | `Video PITCH Final.mp4` (7.95 s → 90.85 s; se quita la preparación de cámara) | 2:52 – 4:08 |
| Pausa con el mouse | El video se congela, se reproduce `Límites gratuitos de cada aplicación` con un panel animado | 4:08 – 4:22 |
| Cierre | Continúa el pitch final ("Creemos que…", "Muchas gracias"), freeze y logo BeCode | 4:22 – 4:32 |

Las voces no se aceleran ni se editan: cada frase de la voz en off está mapeada (en `edl.py`) al fragmento
de la demo que muestra exactamente eso. Donde la demo es más corta que la frase se usan cámara lenta suave,
freeze frames con zoom o reencuadres, nunca aceleración de la voz.

## Archivos

- `edl.py` — guion de edición: cortes, cámara virtual (zooms/punch-ins), textos, tarjetas, pausa, eventos de audio.
- `engine.py`, `lib.py` — motor de composición cuadro a cuadro (Pillow + ffmpeg).
- `render.py` — render en paralelo (4 procesos) → `video_only.mp4`.
- `prep_audio.sh` — limpieza de voces (high-pass, de-click, reducción de ruido, de-esser, compresión suave) y normalización a −16 LUFS.
- `mix.py` — mezcla: voces + pitch + camas de las demos atenuadas (−15 dB bajo la voz, ducking automático) + música + efectos.
- `music.py` — música de fondo original (chill/lo-fi, 84 BPM) sintetizada: sin derechos de terceros.
- `sfx.py` — efectos sutiles sintetizados (pop, click, notificación, confirmación, whoosh, lapicera).
- `stt.py` — transcripción (Whisper vía sherpa-onnx) usada para sincronizar cada frase.
- `fonts/` — Poppins (SIL OFL). `assets/` — logos recortados de las propias demos.

## Regenerar

```bash
# 1) extraer cuadros (ver comandos en el historial: fr/ini a 24 fps con corrección de color, fr/fin a 30 fps, demos a 60 fps)
# 2) audio
python3 sfx.py && python3 music.py && bash prep_audio.sh
python3 edl.py && python3 mix.py
ffmpeg -f f32le -ar 48000 -ac 2 -i aud/mix_raw.f32 -af "volume=1.3dB,alimiter=limit=0.84" aud/mix_final.wav
# 3) video + mux
python3 render.py
ffmpeg -i video_only.mp4 -i aud/mix_final.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -movflags +faststart final.mp4
```
