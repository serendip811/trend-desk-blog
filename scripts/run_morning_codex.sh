#!/bin/bash
set -euo pipefail

PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

ROOT="/Users/seren/workspace/money"
PROMPT_FILE="$ROOT/scripts/morning_codex_prompt.md"
LOG_DIR="$ROOT/outputs/logs"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
LOG_FILE="$LOG_DIR/morning-codex-$TIMESTAMP.log"
LAST_MESSAGE_FILE="$LOG_DIR/morning-codex-last-$TIMESTAMP.txt"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting morning Codex run"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex command not found"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 command not found"
  exit 1
fi

cd "$ROOT"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Prompt file not found: $PROMPT_FILE"
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Repository is dirty. Aborting automated run to avoid mixing changes."
  git status --short
  exit 1
fi

BRANCH="$(git branch --show-current)"

if [ -z "$BRANCH" ]; then
  echo "Could not determine current git branch"
  exit 1
fi

echo "Pulling latest changes for $BRANCH"
git pull --ff-only origin "$BRANCH"

echo "Running Codex with morning prompt"
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --cd "$ROOT" \
  --model gpt-5.4 \
  --output-last-message "$LAST_MESSAGE_FILE" \
  - < "$PROMPT_FILE"

if [ -z "$(git status --porcelain)" ]; then
  echo "No file changes produced by Codex. Nothing to commit."
  exit 0
fi

echo "Staging generated changes"
git add -A

COMMIT_MESSAGE="chore: publish morning trend posts ($(date '+%Y-%m-%d'))"
echo "Creating commit: $COMMIT_MESSAGE"
git commit -m "$COMMIT_MESSAGE"

echo "Pushing branch $BRANCH"
git push origin "$BRANCH"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Morning Codex run completed"
echo "Log: $LOG_FILE"
echo "Last message: $LAST_MESSAGE_FILE"
