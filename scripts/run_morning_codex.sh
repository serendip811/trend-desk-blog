#!/bin/bash
set -euo pipefail

PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

ROOT="/Users/seren/workspace/money"
PROMPT_FILE="$ROOT/scripts/morning_codex_prompt.md"
LOG_DIR="$ROOT/outputs/logs"
LOCAL_ENV_FILE="$ROOT/.secrets/morning_codex.env"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
LOG_FILE="$LOG_DIR/morning-codex-$TIMESTAMP.log"
LAST_MESSAGE_FILE="$LOG_DIR/morning-codex-last-$TIMESTAMP.txt"
RUN_STATUS="failed"
RUN_STAGE="starting"
ALLOWED_DIRTY_PATHS=(
  "scripts/run_morning_codex.sh"
  "scripts/morning_codex_prompt.md"
)

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

if [ -f "$LOCAL_ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$LOCAL_ENV_FILE"
fi

notify_discord() {
  if [ -z "${DISCORD_WEBHOOK_URL:-}" ] && { [ -z "${DISCORD_BOT_TOKEN:-}" ] || [ -z "${DISCORD_CHANNEL_ID:-}" ]; }; then
    return 0
  fi

  local emoji
  local title
  local body

  if [ "$RUN_STATUS" = "success" ]; then
    emoji="✅"
    title="Trend Desk morning run succeeded"
  else
    emoji="❌"
    title="Trend Desk morning run failed"
  fi

  body="$emoji $title\n- Host: $(hostname)\n- Repo: money\n- Time: $(date '+%Y-%m-%d %H:%M:%S')\n- Branch: ${BRANCH:-unknown}\n- Stage: ${RUN_STAGE:-unknown}\n- Log: $LOG_FILE"

  if [ -f "$LAST_MESSAGE_FILE" ]; then
    body="$body\n- Last message: $LAST_MESSAGE_FILE"
  fi

  if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
    DISCORD_MESSAGE_BODY="$body" python3 - <<'PY' | curl -sS -X POST "$DISCORD_WEBHOOK_URL" -H "Content-Type: application/json" --data-binary @- >/dev/null
import json
import os
print(json.dumps({"content": os.environ.get("DISCORD_MESSAGE_BODY", "")}))
PY
    return 0
  fi

  DISCORD_MESSAGE_BODY="$body" python3 - <<'PY'
import json
import os
import urllib.request

token = os.environ.get("DISCORD_BOT_TOKEN")
channel_id = os.environ.get("DISCORD_CHANNEL_ID")
content = os.environ.get("DISCORD_MESSAGE_BODY", "")

if token and channel_id and content:
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=payload,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        response.read()
PY
}

finish() {
  local exit_code=$?
  if [ "$exit_code" -eq 0 ]; then
    RUN_STATUS="success"
  fi
  notify_discord || true
  exit "$exit_code"
}

trap finish EXIT

push_with_retry() {
  local attempt
  local max_attempts=3

  for attempt in 1 2 3; do
    echo "Pushing branch $BRANCH (attempt $attempt/$max_attempts)"
    if git push origin "$BRANCH"; then
      return 0
    fi
    if [ "$attempt" -lt "$max_attempts" ]; then
      echo "Push failed; retrying in 5 seconds"
      sleep 5
    fi
  done

  return 1
}

get_blocking_git_status() {
  local line
  local path
  local allowed_path
  local is_allowed
  local blocking_status=""

  while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    path="${line:3}"
    is_allowed=0

    for allowed_path in "${ALLOWED_DIRTY_PATHS[@]}"; do
      if [ "$path" = "$allowed_path" ]; then
        is_allowed=1
        break
      fi
    done

    if [ "$is_allowed" -eq 0 ]; then
      blocking_status+="$line"
      blocking_status+=$'\n'
    fi
  done < <(git status --porcelain)

  printf '%s' "$blocking_status"
}

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

BLOCKING_GIT_STATUS="$(get_blocking_git_status)"

if [ -n "$BLOCKING_GIT_STATUS" ]; then
  echo "Repository is dirty. Aborting automated run to avoid mixing changes."
  printf '%s' "$BLOCKING_GIT_STATUS"
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Ignoring local automation file changes and continuing."
  git status --short
fi

BRANCH="$(git branch --show-current)"

if [ -z "$BRANCH" ]; then
  echo "Could not determine current git branch"
  exit 1
fi

echo "Pulling latest changes for $BRANCH"
RUN_STAGE="pulling_latest_changes"
git pull --ff-only origin "$BRANCH"

echo "Running Codex with morning prompt"
RUN_STAGE="running_codex"
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --cd "$ROOT" \
  --model gpt-5.4 \
  --output-last-message "$LAST_MESSAGE_FILE" \
  - < "$PROMPT_FILE"

if [ -z "$(git status --porcelain)" ]; then
  echo "No file changes produced by Codex. Nothing to commit."
  RUN_STAGE="no_changes"
  exit 0
fi

echo "Staging generated changes"
RUN_STAGE="staging_changes"
git add -A

COMMIT_MESSAGE="chore: publish morning trend posts ($(date '+%Y-%m-%d'))"
echo "Creating commit: $COMMIT_MESSAGE"
RUN_STAGE="creating_commit"
git commit -m "$COMMIT_MESSAGE"

RUN_STAGE="pushing_to_remote"
push_with_retry

RUN_STAGE="completed"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Morning Codex run completed"
echo "Log: $LOG_FILE"
echo "Last message: $LAST_MESSAGE_FILE"
