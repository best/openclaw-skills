# Gemini Image Prompting Guide

Based on official Google Gemini image generation best practices.

## Core Principle

**Describe the scene as a narrative paragraph, not a keyword list.**

The model's strength is deep language understanding. A descriptive sentence produces more coherent results than disconnected tags.

❌ `cyberpunk, city, sunset, neon, 4K, dramatic`
✅ `A dramatic sunset over a neon-lit cyberpunk cityscape, with flying cars weaving between towering skyscrapers. The sky transitions from deep orange to electric purple, reflecting off rain-slicked streets below.`

## Prompt Templates by Use Case

### 1. Photorealistic Scene

Think like a photographer — mention camera, lens, lighting, and mood.

```
A photorealistic [shot type] of [subject], [action or expression], set in [environment].
The scene is illuminated by [lighting description], creating a [mood] atmosphere.
Captured with a [camera/lens details], emphasizing [key textures and details].
```

Example:
```
A photorealistic close-up portrait of an elderly Japanese ceramicist with deep wrinkles
and a warm smile. He is inspecting a freshly glazed tea bowl in his rustic, sun-drenched
workshop. Soft golden hour light streams through a window. Captured with an 85mm portrait
lens with soft bokeh background.
```

### 2. Stylized Illustration / Sticker

Be explicit about style, line work, and background.

```
A [style] illustration of [subject], featuring [key characteristics] and a [color palette].
The design has [line style] and [shading style]. [Background instruction].
```

Example:
```
A kawaii-style sticker of a happy red panda wearing a tiny bamboo hat, munching on a green
bamboo leaf. Bold clean outlines, simple cel-shading, vibrant colors. White background.
```

### 3. Text in Images

Specify exact text, font style, and overall design intent.

```
Create a [image type] for [brand/concept] with the text "[exact text]" in a [font style].
The design should be [style description], with a [color scheme].
```

Example:
```
Create a modern minimalist logo for a coffee shop called "The Daily Grind". Clean bold
sans-serif font. A simple stylized coffee bean icon integrated with the text. Black and white.
```

### 4. Product Mockup

Describe lighting setup, surface, and camera angle professionally.

```
A high-resolution product photograph of [product] on [surface/background].
Lighting: [setup description]. Camera angle: [angle] to showcase [feature].
Sharp focus on [key detail].
```

### 5. Poster / Promotional Material

Combine visual elements with text and layout instructions.

```
A [style] promotional poster for [subject/brand]. [Visual scene description].
Text "[main title]" in [typography style] at [position]. Tagline "[tagline]" in smaller text.
[Background and color scheme]. [Mood/atmosphere].
```

Example:
```
A futuristic promotional poster for "LinkOS Agent" AI operating system. A glowing neural
network structure at center against a dark gradient background from deep blue to black.
Holographic UI panels float around the logo. Text "LinkOS Agent" in sleek white sans-serif
at center. Tagline "Your AI, Your Rules" below in lighter weight. Subtle circuit board
patterns in the background. Premium, professional feel.
```

### 6. Landscape / Cityscape

Describe atmosphere, weather, time of day, and architectural details.

```
A [style] view of [location/landmark] during [time/weather]. [Architectural details].
[Atmospheric elements like light, weather, people]. [Color palette and mood].
Composition: [wide/close/aerial shot].
```

Example:
```
A cinematic wide shot of Hefei's Sipailou (四牌楼) landmark during a heavy snowfall.
The classical Chinese memorial archway stands tall amid thick white snow. Large snowflakes
drift through the air. Warm yellow street lamps cast glowing halos against the cold blue
twilight. Modern city buildings are faintly visible in the background through the snow.
Warm-cool color contrast. Winter atmosphere.
```

## Best Practices

1. **Be hyper-specific**: Instead of "fantasy armor", say "ornate elven plate armor etched with silver leaf patterns, with pauldrons shaped like falcon wings"

2. **Provide context and intent**: "Create a logo for a high-end minimalist skincare brand" works better than "create a logo"

3. **Use semantic negative prompts**: Instead of "no cars", describe positively: "an empty deserted street with no signs of traffic"

4. **Control the camera**: Use photographic terms — wide-angle, macro, low-angle, 85mm portrait lens, Dutch angle, bird's-eye view

5. **Describe lighting specifically**: "soft golden hour light streaming through a window" beats "good lighting"

6. **Specify materials and textures**: "brushed aluminum with fingerprint smudges", "weathered oak with visible grain", "frosted glass catching morning light"

7. **Set the mood with atmosphere**: Include weather, time of day, ambient sounds implied by the scene, emotional tone

## Language Tips

- Both English and Chinese prompts work well
- For Chinese landmarks or cultural subjects, mixing Chinese names with English descriptions can improve accuracy: `Hefei's Sipailou (四牌楼) memorial archway`
- Describe the cultural context when relevant: "traditional Chinese memorial archway (牌楼) in Qing dynasty style"
