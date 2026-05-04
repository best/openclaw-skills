# Prompting Guide

Write prompts as **clear scene descriptions**, not loose keyword piles.

## Text-to-Image Template

Use one compact paragraph covering:

1. Subject
2. Environment
3. Composition / camera angle
4. Lighting
5. Style / material / mood
6. Important constraints

Example:

> A quiet tea room at sunrise, viewed from a slightly low three-quarter angle. Soft morning light enters through paper windows and falls across a dark wooden table with a celadon teapot and two porcelain cups. The atmosphere is calm, minimal, and refined, with muted natural colors, fine wood grain detail, and realistic shadows. Keep the composition uncluttered and elegant.

## Edit Prompt Template

Describe both the **preserved parts** and the **intended change**.

Example:

> Keep the character pose, facial features, outfit silhouette, and overall framing unchanged. Replace the background with a rainy neon-lit city street at night, add wet reflections on the ground, and shift the color palette toward blue and magenta while preserving a cinematic realistic style.

## Multi-Image Composition

When combining multiple reference images, explicitly state the merge rule:

- which image provides the subject
- which image provides style
- which image provides background
- what must stay consistent

Example:

> Use image 1 as the main subject identity, image 2 as the clothing reference, and image 3 as the environment/style reference. Blend them into one coherent portrait with consistent lighting, perspective, and color grading. Avoid collage artifacts.

## Anti-Patterns

Avoid:

- long keyword dumps
- contradictory styles in one prompt
- vague edits like "make it better"
- omitting what must remain unchanged during edits

## Useful Constraint Phrases

- "Preserve the original composition and subject identity"
- "Do not change facial structure"
- "Keep the logo position unchanged"
- "Avoid extra fingers, duplicated objects, and collage seams"
- "Use a clean background with no text or watermark"
