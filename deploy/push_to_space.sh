#!/bin/bash
# Uploads the committed code to a Hugging Face Space.
# Needs the Hugging Face CLI and a login first: hf auth login
# Usage: bash deploy/push_to_space.sh your-name/teller
set -e

SPACE="$1"
if [ -z "$SPACE" ]; then
    echo "Usage: bash deploy/push_to_space.sh your-name/teller"
    exit 1
fi

# Use the project's own copy of the CLI when there is one
HF_CLI="hf"
if [ -x ".venv/bin/hf" ]; then
    HF_CLI=".venv/bin/hf"
fi

# Only committed files go up, so local notes, keys and data never leave this machine
WORK_DIR="$(mktemp -d)"
git archive HEAD | tar -x -C "$WORK_DIR"

# A Space reads its settings from the top of README.md
cp deploy/space-README.md "$WORK_DIR/README.md"

"$HF_CLI" repos create "$SPACE" --repo-type space --space-sdk docker --exist-ok --public
"$HF_CLI" upload "$SPACE" "$WORK_DIR" . --repo-type space --commit-message "Update from GitHub $(git rev-parse --short HEAD)"

rm -rf "$WORK_DIR"
echo "Done. The Space builds itself: https://huggingface.co/spaces/$SPACE"
