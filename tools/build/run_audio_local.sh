#!/usr/bin/env bash
# Generate the audio clips that the web sandbox can't reach (edge-tts is
# blocked there). Run this on a machine with normal internet access:
#
#   bash tools/build/run_audio_local.sh
#
# It installs edge-tts if missing, fills in every absent audio/{char,word,
# sentence}/*.mp3 clip for the current data files (learn/*.js), and rewrites
# learn/audio-index.js from what's actually on disk. Safe to re-run — only
# missing clips are recorded. Pass extra flags straight through, e.g.:
#   bash tools/build/run_audio_local.sh --voice zh-CN-YunxiNeural
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 -c "import edge_tts" 2>/dev/null || pip install -q edge-tts

python3 tools/generate_audio.py "$@"

echo
echo "Updated files (review before committing):"
git status --short audio/ learn/audio-index.js || true
