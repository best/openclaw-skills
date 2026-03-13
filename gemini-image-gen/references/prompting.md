# Gemini Image Prompting Guide

Based on official Google Gemini image generation best practices (updated March 2026).

Sources: [DeepMind Prompt Guide](https://deepmind.google/models/gemini-image/prompt-guide/), [Developer Blog](https://developers.googleblog.com/en/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/), [Google Blog](https://blog.google/products-and-platforms/products/gemini/image-generation-prompting-tips/)

## Core Principle

**Describe the scene as a narrative paragraph, not a keyword list.**

The model's strength is deep language understanding. A descriptive sentence produces more coherent results than disconnected tags.

❌ `cyberpunk, city, sunset, neon, 4K, dramatic`
✅ `A dramatic sunset over a neon-lit cyberpunk cityscape, with flying cars weaving between towering skyscrapers. The sky transitions from deep orange to electric purple, reflecting off rain-slicked streets below.`

## 6 Elements of a Good Prompt

1. **Subject** — Who or what? Be specific (e.g., "a stoic robot barista with glowing blue optics")
2. **Composition** — How is the shot framed? (e.g., extreme close-up, wide shot, low angle, portrait)
3. **Action** — What's happening? (e.g., brewing coffee, casting a spell, mid-stride running)
4. **Setting** — Where? (e.g., a futuristic café on Mars, a sun-drenched meadow at golden hour)
5. **Style** — What aesthetic? (e.g., 3D animation, film noir, watercolor, photorealistic, 1990s product photography)
6. **Editing Instructions** — For modifications, be direct (e.g., "change the tie to green", "remove the car in the background")

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

Specify exact text in quotes, font style, and design intent.

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
Sharp focus on [key detail]. [Aspect ratio].
```

### 5. Poster / Promotional Material

Combine visual elements with text and layout instructions.

```
A [style] promotional poster for [subject/brand]. [Visual scene description].
Text "[main title]" in [typography style] at [position]. Tagline "[tagline]" in smaller text.
[Background and color scheme]. [Mood/atmosphere].
```

### 6. Landscape / Cityscape

Describe atmosphere, weather, time of day, and architectural details.

```
A [style] view of [location/landmark] during [time/weather]. [Architectural details].
[Atmospheric elements like light, weather, people]. [Color palette and mood].
Composition: [wide/close/aerial shot].
```

### 7. Minimalist / Negative Space Design

For backgrounds, presentations, or overlays where text will be added later.

```
A minimalist composition featuring a single [subject] positioned in the [bottom-right/top-left/etc.]
of the frame. The background is a vast, empty [color] canvas, creating significant negative space.
Soft, subtle lighting. [Aspect ratio].
```

Example:
```
A minimalist composition featuring a single, delicate red maple leaf positioned in the
bottom-right of the frame. The background is a vast, empty off-white canvas, creating
significant negative space for text. Soft, diffused lighting from the top left. Square image.
```

### 8. Sequential Art / Storyboard

For comic panels, visual narratives, and storyboarding.

```
A single comic book panel in a [art style] style. In the foreground, [character description
and action]. In the background, [setting details]. The panel has a [dialogue/caption box]
with the text "[Text]". The lighting creates a [mood] mood. [Aspect ratio].
```

Example:
```
A single comic book panel in a gritty, noir art style with high-contrast black and white inks.
In the foreground, a detective in a trench coat stands under a flickering streetlamp, rain soaking
his shoulders. In the background, the neon sign of a desolate bar reflects in a puddle. A caption
box at the top reads "The city was a tough place to keep secrets." Dramatic, somber mood. Landscape.
```

## Editing & Composition Techniques

### Iterative Refinement

Use conversational follow-ups to progressively refine:
- "That's great, but make the lighting warmer."
- "Keep everything the same, but change the expression to be more serious."
- "Now zoom out to show the full scene."

### Character Consistency

To maintain a character's appearance across multiple images:
1. Define the character with specific details in the first prompt
2. Assign a distinct name to each character or object
3. Upload reference images when available
4. If features drift after many edits, restart a new conversation with the full character description

### Inpainting (Local Edits)

Edit specific areas while preserving everything else:
```
Using the provided image, change only the [specific element] to [new element].
Keep everything else exactly the same, preserving the original style, lighting, and composition.
```

### Style Transfer

Apply an art style to an existing image:
```
Transform the provided photograph of [subject] into the style of [artist/art style].
Preserve the original composition but render with [stylistic elements].
```

### Multi-Image Composition

Combine elements from multiple input images:
```
Create a new image by combining elements from the provided images.
Take the [element from image 1] and place it with [element from image 2].
The final image should be [description of desired result].
```

### Logic and Reasoning

Let the model predict outcomes:
```
Generate an image of [initial scene].
```
Then follow up: "Show what would happen if [event occurred]."

## Best Practices

1. **Be hyper-specific**: Instead of "fantasy armor", say "ornate elven plate armor etched with silver leaf patterns, with pauldrons shaped like falcon wings"

2. **Provide context and intent**: "Create a logo for a high-end minimalist skincare brand" beats "create a logo"

3. **Use semantic negative prompts**: Instead of "no cars", describe positively: "an empty deserted street with no signs of traffic"

4. **Control the camera**: Use photographic terms — wide-angle, macro, low-angle, 85mm portrait lens, Dutch angle, bird's-eye view

5. **Describe lighting specifically**: "soft golden hour light streaming through a window" beats "good lighting"

6. **Specify materials and textures**: "brushed aluminum with fingerprint smudges", "weathered oak with visible grain", "frosted glass catching morning light"

7. **Set the mood with atmosphere**: Include weather, time of day, emotional tone

8. **Iterate, don't regenerate**: Use conversational follow-ups for small adjustments rather than rewriting the entire prompt

9. **Control aspect ratios**: When editing, the model preserves input aspect ratio. For new images, describe format explicitly: "a widescreen backdrop", "a vertical social post". If prompting doesn't produce the right ratio, provide a reference image with correct dimensions

10. **Ask for variations**: Request "three distinct variations" or "four color palettes" to compare ideas side-by-side

## Language Tips

- Both English and Chinese prompts work well
- For Chinese landmarks or cultural subjects, mix Chinese names with English: `Hefei's Sipailou (四牌楼) memorial archway`
- For specific foreign text in images, provide the exact translated text in quotes
- Describe cultural context when relevant: "traditional Chinese memorial archway (牌楼) in Qing dynasty style"
