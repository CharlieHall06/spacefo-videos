# The Vanished Files – video style & rules

Account: TikTok @the.vanished.files. Short, eerie, true mystery stories – mostly famous disappearances (ships, planes, expeditions, lost colonies, people from history) plus other unexplained cases. Videos are made by Claude on a schedule (Tue/Thu/Sat, ready by mid-afternoon for the user to post at 6pm UK). Set up 12 Oct 2026.

## Case rules (always)
- Real, well-documented cases only, checked against reputable sources (official reports, major newspapers and broadcasters, museums, historians). Check every date, name and number.
- Prefer historical cases (roughly 30+ years old) or very famous public cases. Never cover recent missing-person cases involving private individuals, any case involving children, or active investigations.
- Never name or hint that a living person is responsible. Never present suspects, rumours or theories as facts: label theories as THEORY and say when something is unconfirmed, disputed or debunked.
- Treat the people involved with respect: no gore, no mockery, no sensational death details.
- No real people's faces or photos – use silhouettes, maps, objects, places and weather. No made-up quotes, documents, photos or "evidence" presented as real; case-file graphics are clearly stylised title cards.
- End honestly: if it is still unsolved, say so.

## Formats (rotate; track them on the scoreboard)
1. Case file – hook fact → 3–4 eerie details → the strangest clue → 2–3 theories → "What do you think happened?" (35–45s)
2. Countdown – "3 ships that vanished without a trace – wait for #1" (35–45s)
3. Last known moments – the final hours as a timeline with a ticking clock and timestamps (35–45s)
4. Theories ranked – least to most likely, ending on the best-supported one (35–45s)
5. One detail – a single strange clue that makes the case so hard to explain (25–35s)
6. Myth vs truth – a famous "vanishing" story that turns out to be a hoax or has a real answer (30–40s)

## Look
- Dark case-file aesthetic: near-black and cold blue-grey with an evidence-red accent; film grain, slight flicker, vignette, slow drift/zoom on every scene, quick flash or glitch on cuts.
- Procedural visuals: fog, sea, waves, forest, snow, night skies, vintage-style maps with routes and pins, silhouettes, objects (ship, lantern, compass, aircraft outline, lighthouse), paper-textured cards.
- Type: kicker in a typewriter face (Courier Prime), e.g. "CASE FILE #003 · 1872 · NORTH ATLANTIC"; headline in a condensed bold (Oswald or Bebas Neue), white; red rubber-stamp words ("MISSING", "UNSOLVED", "NEVER FOUND"); redaction bars that reveal text. Fonts come from Google Fonts' GitHub repo (github.com/google/fonts, OFL licence).
- Text mid-to-lower screen (y ≈ 1220–1610), clear of TikTok's right-side buttons and the bottom caption area. Frame 0 must already show the scene, a bold hook line and a red stamp or pill teasing the twist.
- 1080×1920, 30 fps, H.264 + AAC, under about 15 MB.

## Voice (the user wants it to sound human, not too perfect – a soft "Yeti mic" sound)
- Narrator: bm_george (British male), speed 0.96, lang en-gb. Alternative: am_onyx (deep American), speed 0.97, lang en-us. The user was sent both samples on 12 Oct 2026; use whichever this line says is chosen. Chosen: bm_george (default until the user picks)
- Generate one sentence at a time, vary speed ±3% per sentence, natural pauses of 0.3–0.6s and a longer beat before reveals.
- Processing (ffmpeg): highpass 70 Hz; +2.5 dB at 170 Hz; +1.2 dB at 3.4 kHz; −2.5 dB at 8 kHz; acompressor threshold −22 dB, ratio 2.4, attack 8, release 140, makeup 2; small-room reflection aecho=0.85:0.55:17|29:0.14|0.09; faint pink-noise room tone (amplitude 0.0022, low-passed 6 kHz, high-passed 120 Hz). Reference: pipeline/vanished-voice/vanished_voice_sample.py

## Sound
- Original synthesized music only: low drones, dark pads, sub pulses, sparse piano-like plucks. Texture effects: radio static, sonar pings, wind, waves, ticking clock, typewriter clacks, heartbeat, distant thunder. A hit on the twist.
- Duck music about 10 dB under the voice. Final mix −14 LUFS, true peak ≤ −1.5 dBTP.

## Captions
- Hook line + question + an emoji or two, e.g. "A ship found drifting with nobody on board… where did they go? 🚢🌫️", plus 4–6 relevant tags such as #mystery #unsolvedmysteries #history #creepy #fyp.

## Posting & analytics
- The user posts these videos themselves (chosen 12 Oct 2026; their free Metricool plan only covers the space account). Each run has the video ready by mid-afternoon with the caption and a checklist: save to Photos → switch to @the.vanished.files in TikTok → post at 6pm with the "AI-generated content" label on.
- Never book anything to Metricool brand 7369991 (spacefi6). Only if a Metricool brand with TikTok exactly "the.vanished.files" appears later (e.g. after a plan upgrade): book it there for 6pm (tiktokData.title = the caption, isAigc true) and tell the user so they don't post it twice.
- Analytics: Supermetrics TikTok (TIKBA) if the.vanished.files gets added there; otherwise Metricool TikTok post fields TKPO02, TKPO03, TKPO05, TKPO06, TKPO07, TKPO08, TKPO09, TKPO10, TKPO13 (full-watch rate), TKPO15 (average watch time), TKPO16 (For You share) if it is ever connected there. With no stats yet, formats rotate evenly.
- Files: vanished-files/videos/YYYY-MM-DD-<slug>.mp4 in this repo; build scripts in pipeline/vanished-<slug>/.

## Variety rule
- Every video changes format and case type (sea, air, land/expedition, colony/civilisation, person, place) from the one before. About 2 in 3 use the best-scoring formats on the scoreboard; about 1 in 3 tests a less-tested format. Judge only videos at least 48 hours old.

## Format scoreboard
No videos posted yet.

## Videos made
None yet.

## Case ideas (check each against the case rules first)
- Mary Celeste (1872) – ship found drifting, crew gone
- Roanoke Colony (found abandoned 1590) – "CROATOAN"
- Flight 19 (1945) – five Navy bombers lost off Florida, and a rescue plane with them
- Amelia Earhart (1937)
- The Franklin Expedition (1845) – two ships lost in the Arctic; wrecks found 2014 and 2016
- Flannan Isles lighthouse keepers (1900)
- SS Waratah (1909) – liner vanished off South Africa
- USS Cyclops (1918) – no wreck ever found
- Star Dust airliner (1947) – the "STENDEC" message
- Carroll A. Deering (1921) – ghost ship off Cape Hatteras
- Percy Fawcett (1925) – the search for the "Lost City of Z"
- The Norse settlers of Greenland (15th century)
- The Ninth Legion (2nd century)
- D.B. Cooper (1971) – the hijacker who jumped and vanished (never name suspects)
- Lake Anjikuni village (1930) – widely considered a hoax; good for "Myth vs truth"
