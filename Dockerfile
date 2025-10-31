# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Singapore \
    # headless matplotlib backend that is safe in containers bc a lot of spectrogram code saves images, and setting a headless backend so that it doesn't look for a display
    MPLBACKEND=Agg

WORKDIR /opt

# system libs (numpy/torch/vision/audio) + git + alsa tools for arecord
RUN set -eux; \
    apt-get update -o Acquire::Retries=3; \
    apt-get install -y --no-install-recommends \
        libopenblas0-pthread \
        libjpeg62-turbo-dev \
        libpng-dev \
        zlib1g-dev \
        libsndfile1 \
        libasound2 \
        alsa-utils \
        ffmpeg \
        procps \
        lftp \
        sox libsox-fmt-all \
        git \
        ca-certificates \
        build-essential; \
    rm -rf /var/lib/apt/lists/*

# pytorch 2.2 line for python 3.11 + ultralytics
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      numpy==1.26.* \
      torch==2.2.0 \
      torchvision==0.17.0 \
      torchaudio==2.2.0 \
      ultralytics \
      pandas==2.2.* \
      # audio / dsp (digital signal processing) stack for predictor
      librosa==0.10.* \
      scipy==1.11.* \
      soundfile==0.12.* \
      audioread \
      resampy \
      matplotlib==3.8.* \
      pydub \ 
      boto3

# repo
ARG REPO_URL="https://github.com/yuglyyy/bird-files.git"
ARG REPO_REF="main"
RUN git clone --depth=1 -b "$REPO_REF" "$REPO_URL" /opt/bird-files

# directory for persisted recordings (mapped from host)
ENV RECORDINGS_DIR="/opt/bird-files/recordings"

# default commands (override via compose if needed)
ENV RECORD_CMD="python -u record/record_upload.py" \
    PREDICT_CMD="python -u record/Code/predict_on_audio.py"

# arecord wrapper: force device if FORCE_ARECORD_DEVICE=1; otherwise inject only when no device provided
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -e' \
'force="${FORCE_ARECORD_DEVICE:-0}"' \
'dev="${ARECORD_DEVICE:-}"' \
'if [ "$force" = "1" ] && [ -n "$dev" ]; then' \
'  # remove any existing -D/--device args and replace with our device' \
'  args=()' \
'  skip=0' \
'  for a in "$@"; do' \
'    if [ "$skip" -eq 1 ]; then skip=0; continue; fi' \
'    case "$a" in' \
'      -D|--device) skip=1 ;;' \
'      --device=*) ;;' \
'      *) args+=("$a") ;;' \
'    esac' \
'  done' \
'  exec /usr/bin/arecord -D "$dev" "${args[@]}"' \
'fi' \
'# not forcing: only inject if caller did not provide device' \
'for a in "$@"; do' \
'  if [ "$a" = "-D" ] || [ "$a" = "--device" ] || [[ "$a" == --device=* ]]; then' \
'    exec /usr/bin/arecord "$@"' \
'  fi' \
'done' \
'if [ -n "$dev" ]; then' \
'  exec /usr/bin/arecord -D "$dev" "$@"' \
'else' \
'  exec /usr/bin/arecord "$@"' \
'fi' \
> /usr/local/bin/arecord && chmod +x /usr/local/bin/arecord

# tiny supervisor to run both tasks forever, restart if either exits
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
'cd /opt/bird-files' \
'mkdir -p "${RECORDINGS_DIR:-/opt/bird-files/recordings}"' \
'echo "[runner] RECORD_CMD=${RECORD_CMD:-unset}"' \
'echo "[runner] PREDICT_CMD=${PREDICT_CMD:-unset}"' \
'echo "[runner] RECORDINGS_DIR=${RECORDINGS_DIR:-/opt/bird-files/recordings}"' \
'while true; do' \
'  bash -lc "$RECORD_CMD" & PID1=$!' \
'  bash -lc "$PREDICT_CMD" & PID2=$!' \
'  wait -n $PID1 $PID2 || true' \
'  echo "[runner] one process exited. restarting both in 3s..."' \
'  kill -TERM $PID1 $PID2 2>/dev/null || true' \
'  sleep 3' \
'done' \
> /usr/local/bin/run-birds.sh && chmod +x /usr/local/bin/run-birds.sh

CMD ["/usr/local/bin/run-birds.sh"]
