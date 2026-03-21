---
name: generate-image
description: "Generate images using Google Gemini API. Use when the user asks to generate, create, or make an image, picture, illustration, or visual. Triggers on /generate-image commands."
---

# Image Generation Skill

Generate images through the toolkit's shared Gemini image-generator entry point.

## Usage

Based on the argument provided by the user ($ARGUMENTS), generate an image.

### Steps

1. Run the **shared toolkit script** with the user's prompt:
```bash
python3 scripts/generate_image.py "$ARGUMENTS"
```

2. The script will:
   - Generate an image using the configured model (default: `nano-banana-pro-preview`)
   - Save it to `uploads/` with a timestamped filename
   - Print the file path on success

3. After the script completes, show the user the generated image by reading the output file path.

4. If the script fails, check:
   - Is `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable set locally?
   - Is the `google-genai` package installed? (`pip install google-genai`)
   - Override model with: `IMAGE_GEN_MODEL=gemini-3.1-flash-image-preview`
   - Review `docs/IMAGE_GENERATOR_SKILL.md`

5. **IMPORTANT**: Before generating, check `uploads/` for existing images to avoid duplicates. Coordinate in chatroom.

## Configuration

- **Shared script**: `scripts/generate_image.py`
- **Docs**: `docs/IMAGE_GENERATOR_SKILL.md`
- **Default model**: `nano-banana-pro-preview`
- **Alt model**: `gemini-3.1-flash-image-preview` (via IMAGE_GEN_MODEL env)
- **Default resolution**: 1K
- **Cost**: ~$0.045-$0.134 per image depending on model
- **Output directory**: `uploads/`
- **API key**: local `GEMINI_API_KEY` or `GOOGLE_API_KEY` only

## Examples

- `/generate-image a cute robot holding a stethoscope`
- `/generate-image a modern healthcare dashboard UI mockup`
- `/generate-image watercolor painting of a sunrise over mountains`
