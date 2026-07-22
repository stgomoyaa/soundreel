# Avatar Generation Guide

Basado en el estilo visual del nicho ambient/lofi para dormir.

## Estética target

| Atributo | Spec |
|---|---|
| Color palette | Violetas profundos, azules nocturnos, magentas oscuros. **NUNCA** warm/orange/yellow. |
| Iluminación | Side-lit dramático, low-key, una fuente fuerte + ambient muy bajo |
| Mood | Melancólico, contemplativo, dreamy, slight nostalgia. Mujer 20-28 años |
| Crops | Mix: portrait close-up, mid-shot en setting, full-body distante |
| Film look | Vintage 35mm grain, slight chromatic aberration, soft focus |
| Resolución | 4K mínimo (3840×2160), ratio 16:9 horizontal preferido |
| Expresión | Pensativa, mirada lejana, half-smile, ojos hacia ventana/cielo. NO sonriendo abiertamente. |

## Character consistency

CRÍTICO: Mismo avatar para todo el canal. Diferenciado entre ch1 y ch2.

**Recomendación de tooling**:
- Midjourney v6+ con `--cref <image_url>` (consistencia rostro)
- Flux 1.1 Pro con character LoRA
- Leonardo AI con character reference
- Sora si tienes acceso (mejor video → static frame)

**Genera primero "character bible"**:
1. 1 imagen "hero" del avatar (portrait neutral, lighting plain) → URL para `--cref`
2. Esa URL se usa de seed en todas las generaciones siguientes

---

## Canal 1 (ejemplo: tema rain / post-breakup — ajusta a tu CHANNEL_NAME)

### Character bible prompt (genera primero, guarda URL)

```
portrait of a 24 year old woman, soft features, dark long hair, melancholic 
expression, looking slightly off camera, neutral background, soft natural 
lighting, cinematic, 35mm film, shallow depth of field, ultra realistic, 
photographic
```

### Scene prompts (usa con --cref)

```
1. same woman, sitting by rainy window at night, soft purple neon light from 
   outside, looking pensive, cinematic 35mm, vintage film grain, melancholic, 
   shallow dof, blue-violet color grading

2. same woman in dark bedroom, soft side lighting from window, sitting on edge 
   of bed, looking down, sad expression, 35mm vintage film, low key lighting

3. same woman walking in empty wet street at night, neon signs reflecting on 
   pavement, looking back over shoulder, melancholic, cinematic, anamorphic, 
   purple-blue tones, light rain

4. same woman in passenger seat of car at night, city lights blurred outside 
   window, headphones on, looking out window pensively, cinematic, soft 
   purple light on face

5. same woman in dimly lit cafe at night, half-empty coffee cup, looking at 
   empty seat across from her, dark moody atmosphere, vintage film, 35mm

6. same woman on apartment balcony at night, city skyline behind, fairy lights, 
   wearing oversized sweater, looking distant, cinematic, magenta and blue tones

7. close-up of same woman crying softly, single tear, dramatic side lighting, 
   blue-purple shadows, 35mm film grain, intimate, melancholic

8. same woman in childhood bedroom, looking at old photos on bed, soft warm 
   purple lamp, nostalgic, cinematic, shallow dof
```

---

## Canal 2 (ejemplo: tema insomnio / sleep aid — solo si operas 2 canales)

Mismo aesthetic pero diferente avatar. Diferenciar para evitar "duplicate operator" detection.

### Character bible prompt

```
portrait of a 26 year old woman, sharper features than typical, mid-length 
dark hair with subtle waves, tired but serene expression, looking down, neutral 
background, soft natural lighting, cinematic, 35mm film, shallow depth of field, 
ultra realistic, photographic
```

### Scene prompts

```
1. same woman lying in bed at 3am unable to sleep, eyes open staring at ceiling, 
   only blue moonlight on her face, dark room, intimate, 35mm film grain

2. same woman reading book in armchair at night, single warm lamp, dark room 
   around her, peaceful but exhausted expression, cinematic, vintage

3. same woman in bathroom mirror at night, harsh single overhead light, looking 
   at her own reflection, tired, slight purple wash, cinematic

4. same woman at desk at 2am, laptop screen lighting her face, headphones, 
   looking at screen pensively, dark room, blue-purple tones

5. same woman on apartment balcony at night, holding mug of tea, watching city 
   below, peaceful exhaustion, magenta gradient sky, cinematic

6. same woman in empty hallway at night, single warm wall light, looking down 
   hallway, lonely composition, low key, vintage 35mm

7. close-up same woman with eyes closed, soft breath visible, peaceful, 
   surrendering expression, dramatic blue side light, intimate

8. same woman walking through empty subway station at night, fluorescent 
   lights buzzing, looking down, lonely, cinematic wide shot, blue-violet
```

---

## Output specs por imagen

- **Aspect ratio**: `--ar 16:9` (Midjourney) o equivalente
- **Quality**: `--q 2 --s 250` (MJ) — más detalle, más estilizado
- **Style ref**: opcional, una imagen de referencia de estilo del nicho para consistencia visual

## Naming convention al descargar

```
assets/avatar/
├── ch1_01_rainy_window.jpg
├── ch1_02_bedroom_night.jpg
├── ch1_03_wet_street.jpg
├── ch1_04_car_passenger.jpg
├── ch1_05_cafe.jpg
├── ch1_06_balcony.jpg
├── ch1_07_crying.jpg
├── ch1_08_photos.jpg
├── ch2_01_insomnia.jpg
├── ch2_02_reading.jpg
... etc
```

## Quality filter — descarta si:

- Cara distorsionada / hands mal renderizados
- Iluminación warm/yellow (no encaja con palette)
- Demasiado sexualizado (puede bajar CTR + risk YouTube algorithm penalization)
- Demasiado "AI obvio" (skin texture plástica, ojos vacíos)
- Expresión muy alegre/risueña (no es el mood)
- Background limpio/aspirational (queremos atmospheric, no influencer-pretty)

## Refresh cadence

- Genera 8 inicial por canal pre-launch
- Cada 2-3 semanas: añade 4-6 nuevos al pool
- Después de mes 3: rotación visual para evitar "stale visuals"
