#!/bin/sh
# Build 'Roanoke – one word left behind' in the current (build) directory.
# Needs Kokoro model files in /home/claude/build/models and fonts in /home/claude/build/fonts.
set -e
D=$(dirname "$0")
python3 "$D/voice.py"
python3 "$D/audio.py"
python3 "$D/render.py" silent.mp4
ffmpeg -hide_banner -i mix_raw.wav -af loudnorm=I=-14:TP=-2:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p' > ln.json
python3 - <<'PY'
import json, subprocess
m = json.load(open('ln.json'))
af = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "silent.mp4", "-i", "mix_raw.wav", "-af", af,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "35.0", "-movflags", "+faststart",
                "final.mp4"], check=True)
PY
