#!/usr/bin/env python3
"""Generate images using the shared team Gemini image generator setup."""

import mimetypes
import os
import sys
from datetime import datetime

from google import genai
from google.genai import types


def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)


def generate(prompt: str, output_dir: str = "uploads", model: str | None = None):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: set GEMINI_API_KEY or GOOGLE_API_KEY.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    client = genai.Client(api_key=api_key)
    model = model or os.environ.get("IMAGE_GEN_MODEL") or "nano-banana-pro-preview"

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    config = types.GenerateContentConfig(
        image_config=types.ImageConfig(image_size="1K"),
        response_modalities=["IMAGE", "TEXT"],
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_index = 0

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        if chunk.parts is None:
            continue
        for part in chunk.parts:
            if part.inline_data and part.inline_data.data:
                file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
                file_name = f"{output_dir}/generated_{timestamp}_{file_index}{file_extension}"
                file_index += 1
                save_binary_file(file_name, part.inline_data.data)
                print(f"Image saved: {file_name}")
            elif part.text:
                print(part.text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_image.py <prompt>")
        print('Example: python3 generate_image.py "a clinician-facing healthcare infographic"')
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    generate(prompt)
