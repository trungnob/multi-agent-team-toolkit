# Image Generator Skill

Canonical location for the shared image-generator workflow:

- Script: `scripts/generate_image.py`
- Claude skill: `.claude/skills/generate-image/SKILL.md`

## Usage

Run the toolkit script with a plain prompt:

```bash
python3 scripts/generate_image.py "a clinician-facing healthcare infographic"
```

## Environment

The script reads one of these environment variables:

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`

Do not paste keys into the team chatroom, chat archive, or any committed file.
Keep them only in a local gitignored `.env` or your shell environment.

## Model selection

Default model:

- `nano-banana-pro-preview`

Override if needed:

```bash
IMAGE_GEN_MODEL=gemini-3.1-flash-image-preview python3 scripts/generate_image.py "your prompt"
```

## Output

Generated images are written to `uploads/` by default.

## Coordination

- Check `uploads/` first to avoid duplicate generations.
- Assign image ownership before using quota-heavy prompts.
- Prefer one shared script over private per-agent copies.
