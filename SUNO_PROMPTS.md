# Suno Prompts Library

Pool de prompts por canal con SEO alignment: snowfall + rain + insomnia relief + deep sleep keywords.

## Reglas

- Custom Mode + Instrumental ON
- 4 min duration cap
- WAV download (no MP3)
- 2-3 retries por prompt, keep best
- Naming: `track_NNN_<short>.wav` en `data/raw_tracks/`

## Filtros de calidad (descarta)

- Vocals reconocibles
- Distorsión / artifacts metálicos
- BPM > 75
- Loop obvio
- Genre drift (rock, pop, drum-and-bass)
- Sounds-like-existing-song

---

## CANAL 1 (ejemplo: tema rain / post-breakup — ajusta a tu CHANNEL_NAME)

**Tono**: melancólico, post-breakup. Piano, strings, soft pads. 55-70 BPM.
**Weather variety**: rain + snowfall + winter atmosphere (matches branding + amplía SEO).

```
1.  dark ambient piano, slow, melancholic, 60bpm, no drums, deep reverb, female vocal hums in the distance, rain texture subtle
2.  sad solo piano, minor key, slow rubato, intimate close mic, snowfall ambience, lonely atmosphere
3.  cinematic strings, sad, lonely, 65bpm, cello and viola, no percussion, snowstorm distant atmosphere
4.  romantic ambient piano, slow, melancholic, sustain pedal heavy, rain on window background
5.  lofi ambient piano, vinyl crackle, slow, sad chord progression Am-F-C-G, snowfall sounds subtle
6.  warm ambient pads, sad, slow attack, no drums, distant choir, winter sunset feeling
7.  emotional piano with strings, slow build, melancholic, no percussion, intimate, snow falling outside
8.  hauntology ambient, vinyl crackle, distant piano, foggy texture, post-breakup, winter night
9.  sad acoustic guitar, fingerpicked, slow, reverb-heavy, lonely, snow drift outside window
10. cinematic emotional piano, minor key, slow, female humming far away, blizzard wind subtle
11. ambient string ensemble, sad, sustained chords, very slow, no rhythm, snowfall ambience
12. melancholic music box, slow, minor, reverb, childhood winter memory feel
13. ambient pads with piano accents, slow, sad, dream-like, slight tape saturation, snowfall texture
14. solo cello, sad, slow, intimate recording, reverb tail, missing someone in winter
15. soft electric piano, rhodes, melancholic chord progression, no drums, late autumn rain
16. ambient guitar with reverb, slow phaser, sad melody, no vocals, rainy winter night
17. minimal piano with field recording snowfall, sad, slow, intimate
18. warm tape ambient, sad chord progression, slow, lo-fi texture, post-breakup, snow texture
19. emotional violin, slow, sad, no percussion, hall reverb, winter atmosphere
20. ambient piano with subtle synthesizer, slow, melancholic, dreamy, snowstorm outside window
```

---

## CANAL 2 (ejemplo: tema insomnio / sleep aid — solo si operas 2 canales)

**Tono**: contemplativo, insomnio/ansiedad, surrender soft. Drones, synth pads.
**Sleep aid emphasis**: insomnia relief + deep sleep music vocabulary explícito en prompts.

```
1.  deep ambient drone, very slow evolution, dark texture, no rhythm, for deep sleep, insomnia relief
2.  ethereal synth pads, slow, no drums, dream-like, night atmosphere, sleep aid
3.  minimal ambient, low drone, distant high tones, very calming, insomnia relief music
4.  warm analog synth pads, slow attack, no rhythm, peaceful, deep sleep music
5.  dark ambient with binaural texture, very slow, no melody, for deep sleep and relaxation
6.  ambient cinematic pads, slow drift, no percussion, anxiety calming, sleep music
7.  spacious ambient, reverb-heavy synths, very slow, peaceful, deep sleep aid
8.  drone with subtle chord movement, dark ambient, no rhythm, meditative, deep sleep music
9.  ambient soundscape with distant wind, slow synth chords, no drums, deep sleep music
10. soft electronic ambient, very slow, no percussion, dreamy, insomnia relief
11. lo-fi ambient pads, vinyl crackle, no rhythm, dreamy, sleep aid music
12. dark ambient with low rumble, very slow, deep texture, for insomnia relief
13. minimal ambient piano with synth pads, very slow, no drums, peaceful, sleep music
14. ambient with subtle snowfall field recording, soft pads, slow, deep sleep music
15. ethereal vocals humming, slow, no rhythm, distant, dream-like, sleep aid
16. ambient drone with chime accents, very slow, peaceful, deep meditation sleep
17. warm bass drone with high pad shimmer, very slow, no rhythm, sleep music
18. ambient cinematic, slow strings and synth, no percussion, late night insomnia relief
19. binaural ambient pads, slow phase, very calming, for deep sleep insomnia relief
20. soft synth ambient with subtle distortion, very slow, dreamy, deep sleep music
```

---

## Variación (después de 40 base)

- **Llave**: Am, Dm, Em, F#m, Cm
- **BPM**: 55, 60, 65, 70 (ch1) / sin BPM o 40-50 (ch2)
- **Texturas**: añade/quita rain, snowfall, vinyl crackle, distant choir, tape saturation, wind
- **Instrumento líder**: piano → strings → guitar → synth → cello → music box

---

## Descripción YouTube (ya está en `titles_pool.py`)

Cada video se publica con esta descripción auto-generada:

```
{título del video}

#ambient #music #sad #playlist #snowfall #rain #sleepmusic #darkambient

ambient sleep music
insomnia relief
deep sleep music

music to calm your soul, to fall asleep to or to overthink.
it would mean so much to me if you'd subscribe ❤️

tags: ambient sleep music, insomnia relief, deep sleep music,
snowfall ambient, rain music, dark ambient, sleep music, ...
```

## Tags YouTube (max 500 chars total — usamos 323)

```python
[
    "ambient", "sleep music", "dark ambient", "sad music",
    "ambient music", "music for sleep", "insomnia relief",
    "deep sleep music", "music for overthinking", "lonely music",
    "late night music", "3am music", "sad ambient", "calm music",
    "music for soul", "ambient mix", "healing music", "snowfall",
    "snowfall ambient", "winter ambient", "rain music",
    "music for missing someone", "post breakup",
]
```
