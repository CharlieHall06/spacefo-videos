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
- Analytics: Supermetrics TikTok (TIKBA), account id "the.vanished.files" (connected 12 Oct 2026; free trial expired 22 Oct 2026, so queries fail until the user subscribes or reconnects). Fallback: Metricool TikTok post fields TKPO02, TKPO03, TKPO05, TKPO06, TKPO07, TKPO08, TKPO09, TKPO10, TKPO13 (full-watch rate), TKPO15 (average watch time), TKPO16 (For You share) if it is ever connected there. With no stats yet, formats rotate evenly.
- Files: vanished-files/videos/YYYY-MM-DD-<slug>.mp4 in this repo; build scripts in pipeline/vanished-<slug>/.

## Variety rule
- Every video changes format and case type (sea, air, land/expedition, colony/civilisation, person, place) from the one before. About 2 in 3 use the best-scoring formats on the scoreboard; about 1 in 3 tests a less-tested format. Judge only videos at least 48 hours old.

## Format scoreboard
| Format | Videos | Avg views | Avg watch (% of length) | Avg full-watch | Likes+comments+shares per 100 views | Notes |
|---|---|---|---|---|---|---|
| Case file | 2 (+1 new) | 680 | 17% (Mary Celeste 23%, Flannan 12%) | 4.2% | 1.4 | Mary Celeste 74s: 640 views, 16.8s, 6.5%, 2.2. Flannan Isles 44.5s: 720 views, 5.3s, 1.8%, 0.7 (Supermetrics 20 Oct 2026 11:52 UTC). Percy Fawcett (44.6s) made 24 Oct; judge from 26 Oct |
| Last known moments | 1 (+1 unscored) | 605 | 15% (6.9s) | 4.2% | 0.7 | Flight 19 (45s). Carroll A. Deering (44s) made 22 Oct; could not be scored on 24 Oct (no stats) |
| One detail | 1 | 681 | 11% (4.0s) | 2.2% | 0.4 | Roanoke (35s), now scored (~90h old) |
| Theories ranked | 1 (unscored) | – | – | – | – | Amelia Earhart (45.5s), posted 21 Oct 11:00 UTC: 217 views, 7.3s (16%), 4.0% full-watch, 0.5 per 100 views at 22 Oct ~12:00 UTC (under 48h, not scored yet) |
| Countdown, Myth vs truth | 0 | – | – | – | – | untested |
- Takeaway so far: views are flat at ~600–720 whatever the format, so the For You page is testing each video on a similar small audience; watch % decides whether it gets pushed further. Watch % has fallen with each video (23% → 15% → 11% → 12%). Flannan Isles got the most views but kept people only 5.3s, so the first 5 seconds are where viewers leave. On 20 Oct tried Theories ranked (a "wait for #1" structure plus a #4–#1 tracker on screen) with a very famous name in the hook to see if that holds people longer. Early sign (under 48h): Earhart's 7.3s average watch is the best of the 45s videos so far. On 22 Oct went back to Last known moments (best average watch in seconds among the 45s videos) with a sea case, and a stronger visual hook (ship on the shoals + CREW VANISHED stamp on frame 0). On 24 Oct no new stats: the Supermetrics trial expired on 22 Oct (TRIAL_EXPIRED) and Metricool has only spacefi6, so the choice used this scoreboard: Case file (best watch % and engagement), land/expedition case, with three walking silhouettes + NEVER FOUND stamp on frame 0. Earhart and Deering stay unscored until stats come back.

## Videos made
1. Mary Celeste (1872, sea / ghost ship) – Case file style, 74s. Posted by the user on 12 Oct 2026 at 01:18, made in another chat before this schedule existed. Caption: "In 1872 a ship was found drifting with 6 months of food on board… and not one person 🚢 What do you think happened to them? 👇 #maryceleste #ghostship #unsolvedmysteries #historytok #mystery"

2. Flight 19 (5 Dec 1945, air) – Last known moments, 45.4s. Made 13 Oct 2026 for the user to post at 6pm. File: vanished-files/videos/2026-10-13-flight-19.mp4; scripts: pipeline/vanished-flight-19/. Voice: bm_george, run at ~1.0 speed (1.03 × ±3%) to fit 45s. Sources: NHHC H-Gram 057-4, National Archives "Prologue" blog (2017), History.com.
   - Voiceover: "December fifth, nineteen forty-five. Five Navy bombers leave Florida on a training flight, fourteen men on board. Three forty. The leader radios: both my compasses are out. He's sure they're over the Florida Keys. They're not. Sunset. The sea turns rough, and fuel is running low. Seven oh four. The last words heard: we'll have to ditch. A flying boat with thirteen men goes to find them. Twenty minutes later, a tanker sees a burst of flames. Twenty-seven men. Six aircraft. No wreckage ever found. The cause is still unknown. What do you think happened?"
   - Caption: "5 Navy planes. 14 men. One radio message… then nothing, ever again ✈️🌊 What do you think happened to Flight 19? 👇 #flight19 #unsolvedmysteries #mystery #history #creepy #fyp"

3. Roanoke Colony (Aug 1590, colony) – One detail, 35.0s. Made 15 Oct 2026 for the user to post at 6pm. File: vanished-files/videos/2026-10-15-roanoke.mp4; scripts: pipeline/vanished-roanoke/ (build.sh runs voice → audio → render → loudnorm). Voice: bm_george at 1.05 × ±3% (0.88 on the reveal word); TTS spells Roanoke "Rowanoke" so it says "ROH-uh-noke". Why: only scored video (74s) held ~23% of its length, so tested the shortest, untested format; colony case type after sea and air. Sources: NPS Fort Raleigh "1590 Rescue Voyage" and "John White" pages, NC DNCR "Origins of the Lost Colony Mystery", Britannica "Lost Colony".
   - Voiceover: "In fifteen ninety, John White sails back to his colony on Roanoke Island. More than a hundred settlers were waiting for him. Every one of them is gone. No sign of a fight. Just one word, carved into a post of the fort. Croatoan. They'd agreed a signal: if they were ever forced out, carve a cross. There's no cross. Croatoan was a friendly island to the south. A storm stops White ever getting there. It's still unsolved. Where do you think they went?"
   - Caption: "Over 100 settlers vanished… and left just one word carved into a post 🪓🌫️ Where do you think they went? 👇 #roanoke #lostcolony #unsolvedmysteries #mystery #history #fyp"

4. Flannan Isles lighthouse keepers (Dec 1900, place / lighthouse) – Case file, 44.5s. Made 17 Oct 2026 for the user to post at 6pm. File: vanished-files/videos/2026-10-17-flannan-isles.mp4; scripts: pipeline/vanished-flannan-isles/ (build.sh: voice → audio → render → loudnorm). Voice: bm_george at 1.08 × ±3% (theory lines 3% slower). Why: Case file is the best-scoring format (23% watch, 2.2 interactions per 100 views vs 15%/0.7 for Last known moments), cut to 45s with the hook spoken first; place case type after sea, air and colony. Left out the popular myths (uneaten meal, stopped clock, fake logbook entries) and the murder rumours. Sources: Wikipedia "Flannan Isles Lighthouse" (quotes Muirhead's 1901 report), Sky HISTORY UK, History Hit.
   - Voiceover: "Three lighthouse keepers vanished, and one of them left his coat behind. December, nineteen hundred. A ship passes the Flannan Isles lighthouse, off Scotland. Its light is out. Eleven days later, the relief boat arrives. Nobody is there. The gate and the door are shut. But one set of oilskins is still there. One man went out without his coat. At the west landing, a box of ropes, over a hundred feet above the sea, is smashed open. Theory: a giant wave swept them away. The official verdict. Theory: one man ran out to warn the others. They were never found. No one knows for sure. What do you think happened?"
   - Caption: "3 lighthouse keepers vanished… and one of them left his coat behind 🌊🕯️ What do you think happened? 👇 #flannanisles #lighthouse #unsolvedmysteries #mystery #history #fyp"

5. Amelia Earhart (2 Jul 1937, air / person) – Theories ranked, 45.5s. Made 20 Oct 2026 for the user to post at 6pm. File: vanished-files/videos/2026-10-20-amelia-earhart.mp4; scripts: pipeline/vanished-earhart/ (build.sh: voice → audio → render → loudnorm). Voice: bm_george at 1.12 × ±3% ("Number…" lines 3% slower); TTS says Nikumaroro as "Neekoomaroro". Why: no format clearly working and watch % falling, so the ~1-in-3 test of an untested format; most famous case so far and topical (the Purdue-backed Nikumaroro search reported on 20 Oct 2026 that it found no plane); air/person case after place. Ranking: #4 lived on under a new name (debunked – no name given), #3 captured by Japan (the 2017 "proof" photo was printed in 1935), #2 castaway on Nikumaroro (bones found in 1940, later lost), #1 out of fuel and sank (the official conclusion). Visuals have no faces; the photo is a stylised empty dock. Sources: National Archives/DocsTeach Itasca radio log, National Geographic (2017 photo discredited), NPR/MPR (2018 Jantz bones study), Wikipedia "Irene Craigmile Bolam", ABC News/NBC (Oct 2026 search).
   - Voiceover: "Amelia Earhart vanished in nineteen thirty-seven. Four theories, ranked. She and navigator Fred Noonan were hunting for a tiny Pacific island. Her radio call: we must be on you, but cannot see you. Gas is running low. Then, silence. Number four: she lived on, under a new name. Debunked. Number three: captured by Japan. But the photo said to prove it was printed two years earlier. Number two: a castaway on Nikumaroro. Bones found there were lost. A search this month found no plane. Number one: she ran out of fuel and sank. The official conclusion. Her plane has never been found. Which theory do you believe?"
   - Caption: "Amelia Earhart vanished in 1937… here are 4 theories, ranked ✈️🌊 Which one do you believe? 👇 #ameliaearhart #unsolvedmysteries #mystery #history #creepy #fyp"

6. Carroll A. Deering (Jan 1921, sea / ghost ship) – Last known moments, 44.0s. Made 22 Oct 2026 for the user to post at 6pm. File: vanished-files/videos/2026-10-22-carroll-deering.mp4; scripts: pipeline/vanished-carroll-deering/ (build.sh: voice → audio → render → loudnorm + re-encode to stay under 15 MB). Voice: bm_george at 1.12 × ±3% (theory lines and "No crew." 5% slower). Why: previous video was Theories ranked (air/person), so a best-scoring format (Last known moments) and the sea case type. Timeline from NPS: lightship 29 Jan, SS Lake Elon sighting 30 Jan 5:45pm, found aground 31 Jan 6:30am, boarded 4 Feb. Theories (mutiny, pirates) labelled as unproven; the forged message in a bottle was left out. Sources: NPS Cape Hatteras "The Ghost Ship of the Outer Banks", Library of Congress "Headlines & Heroes" (2023), Wikipedia "Carroll A. Deering".
   - Voiceover: "This ship ran aground with every sail set, and nobody on board. January twenty-ninth, nineteen twenty-one. The schooner Carroll A. Deering passes a lightship. A crewman shouts across: we've lost both anchors. He doesn't look like an officer. Next evening, another ship sees her steering a strange course. January thirty-first. She's found stuck on Diamond Shoals. Sails set. Lifeboats gone. When they finally get on board: food laid out for a meal. The log, gone. No crew. Theory: mutiny. Theory: pirates. Nothing was ever proven. Still unsolved. What do you think happened?"
   - Caption: "This ship ran aground with every sail set… and nobody on board 🚢🌫️ What do you think happened to the crew? 👇 #carrolladeering #ghostship #unsolvedmysteries #mystery #history #fyp"

7. Percy Fawcett (May 1925, land / expedition) – Case file, 44.6s. Made 24 Oct 2026 for the user to post at 6pm. File: vanished-files/videos/2026-10-24-percy-fawcett.mp4; scripts: pipeline/vanished-fawcett/ (build.sh: voice → audio → render → loudnorm). Voice: bm_george at 1.12 × ±3% (theory lines, "His report…" and "A typo?" 5% slower); TTS says Rimell as "Rimmel". Why: previous video was Last known moments (sea); Case file is the best-scoring format; land/expedition case type not used yet. Strangest clue: his last letter to his wife gives the camp as 11°43′S, his report to the North American Newspaper Alliance as 13°43′S (same longitude). 1951 remains: the Royal Anthropological Institute concluded they were not his. Left out the disputed "100 searchers died" claim and named the tribal oral accounts only as "killed in the jungle", labelled THEORY. Sources: Wikipedia "Percy Fawcett", History.com "Explorer Percy Fawcett disappears in the Amazon", RAI Fawcett Papers (A69), National Geographic.
   - Voiceover: "He went into the Amazon to find a lost city, and never came back. May twenty-ninth, nineteen twenty-five. Percy Fawcett sends his guides home from Dead Horse Camp. With him: his son Jack, and Jack's friend Raleigh Rimell. His last letter to his wife: you need have no fear of any failure. But that letter puts the camp at eleven degrees south. His report to the papers says thirteen. A typo? Or a false trail? In nineteen fifty-one, bones said to be his turn up. Tests say they're not him. Theory: hunger or fever. Theory: killed in the jungle. None of them was ever found. Still unsolved. What do you think happened?"
   - Caption: "He went into the Amazon to find a lost city… and never came back 🌿🧭 What do you think happened to him? 👇 #percyfawcett #lostcityofz #unsolvedmysteries #mystery #history #fyp"

## Case ideas (check each against the case rules first)
- ~~Roanoke Colony (found abandoned 1590) – "CROATOAN"~~ – done 15 Oct 2026
- ~~Flight 19 (1945)~~ – done 13 Oct 2026
- ~~Amelia Earhart (1937)~~ – done 20 Oct 2026 (Theories ranked)
- The Franklin Expedition (1845) – two ships lost in the Arctic; wrecks found 2014 and 2016
- ~~Flannan Isles lighthouse keepers (1900)~~ – done 17 Oct 2026
- SS Waratah (1909) – liner vanished off South Africa
- USS Cyclops (1918) – no wreck ever found
- Star Dust airliner (1947) – the "STENDEC" message
- ~~Carroll A. Deering (1921) – ghost ship off Cape Hatteras~~ – done 22 Oct 2026 (Last known moments)
- ~~Percy Fawcett (1925) – the search for the "Lost City of Z"~~ – done 24 Oct 2026 (Case file)
- The Norse settlers of Greenland (15th century)
- The Ninth Legion (2nd century)
- D.B. Cooper (1971) – the hijacker who jumped and vanished (never name suspects)
- Lake Anjikuni village (1930) – widely considered a hoax; good for "Myth vs truth"
