# Spacefo video pipeline

Reference build scripts for the SpaceFI TikTok videos (1080×1920, 30 fps, -14 LUFS).

`zoom-out/` made "How small are we really?" (12 Oct 2026):

- `voice.py` – Kokoro TTS voiceover (am_michael, speed 1.08), one clip per scene
- `timeline.py` – shared timing for picture and sound, built from the voice clips
- `textures.py` – pre-renders the Sun, Milky Way, Laniakea and cosmic-web textures
- `render.py` – skia frame renderer piped into ffmpeg (camera zoom, text, YOU ARE HERE marker)
- `audio.py` – original soundtrack, sound effects, ducking and mix

Model files and textures are downloaded or generated at build time and are not stored here.
Finished videos live in `videos/`, named `YYYY-MM-DD-<slug>.mp4`.
