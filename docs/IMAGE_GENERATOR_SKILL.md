# Shared Image Generator Skill

Team-shared image generation using Google Gemini API.

## Setup

1. Install the dependency:
```bash
pip install google-genai
```

2. Set your API key (either works):
```bash
export GEMINI_API_KEY="your-key-here"
# or
export GOOGLE_API_KEY="your-key-here"
```

## Usage

```bash
python3 scripts/generate_image.py "<prompt>"
```

Images are saved to `uploads/` with timestamped filenames.

## Model selection

Default model: `nano-banana-pro-preview`

Override with:
```bash
IMAGE_GEN_MODEL=gemini-3.1-flash-image-preview python3 scripts/generate_image.py "<prompt>"
```

## Available models

| Model | Quality | Cost/Image |
|-------|---------|------------|
| `imagen-4.0-fast-generate-001` | Good | ~$0.02 |
| `gemini-2.5-flash-image` | Good | ~$0.039 |
| `nano-banana-pro-preview` (default) | Excellent | ~$0.134 |
| `gemini-3.1-flash-image-preview` | Best | ~$0.045 |

## Coordination rule

Do not generate duplicate content. Before running, assign image ownership clearly across the team.

## Claude Code skill

The `/generate-image` skill is available at `.claude/skills/generate-image/SKILL.md` and wraps this script for use within Claude Code conversations.
