#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".deploy.env" ]]; then
    # shellcheck disable=SC1091
    source ".deploy.env"
fi

HUGO_BIN="${HUGO_BIN:-hugo}"
BASE_URL="${BASE_URL:-http://47.93.123.112/}"
DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_HOST="${DEPLOY_HOST:-47.93.123.112}"
DEPLOY_PATH="${DEPLOY_PATH:-/var/www/blog}"
DEPLOY_TARGET="${DEPLOY_TARGET:-${DEPLOY_USER}@${DEPLOY_HOST}}"
SSH_KEY="${SSH_KEY:-}"
SSH_PORT="${SSH_PORT:-22}"

log() {
    printf '[blog] %s\n' "$*"
}

die() {
    printf '[blog] ERROR: %s\n' "$*" >&2
    exit 1
}

[[ -d "themes/PaperMod" ]] || die "themes/PaperMod is missing"
[[ -f "hugo.yaml" ]] || die "hugo.yaml is missing"

if [[ ! "$DEPLOY_PATH" =~ ^/var/www/[A-Za-z0-9._/-]+$ ]]; then
    die "DEPLOY_PATH must be a simple absolute path below /var/www"
fi

command -v "$HUGO_BIN" >/dev/null 2>&1 || die "Hugo not found: $HUGO_BIN"

log "Building with Hugo"
"$HUGO_BIN" --gc --minify --cleanDestinationDir --baseURL "$BASE_URL"
[[ -f "public/index.html" ]] || die "public/index.html was not generated"

SSH_ARGS=(-o StrictHostKeyChecking=accept-new)
SCP_ARGS=(-o StrictHostKeyChecking=accept-new)

if [[ -n "$SSH_KEY" ]]; then
    SSH_ARGS+=(-i "$SSH_KEY")
    SCP_ARGS+=(-i "$SSH_KEY")
fi

if [[ "$SSH_PORT" != "22" ]]; then
    SSH_ARGS+=(-p "$SSH_PORT")
    SCP_ARGS+=(-P "$SSH_PORT")
fi

log "Preparing remote directory ${DEPLOY_TARGET}:${DEPLOY_PATH}"
ssh "${SSH_ARGS[@]}" "$DEPLOY_TARGET" "mkdir -p -- '$DEPLOY_PATH'"

if command -v rsync >/dev/null 2>&1; then
    log "Uploading with rsync (stale files are removed)"
    RSYNC_SSH=(ssh "${SSH_ARGS[@]}")
    printf -v RSYNC_SSH_CMD '%q ' "${RSYNC_SSH[@]}"
    rsync -az --delete --chmod=D755,F644 -e "$RSYNC_SSH_CMD" ./public/ "${DEPLOY_TARGET}:${DEPLOY_PATH}/"
else
    log "rsync not found; falling back to scp (stale remote files are not removed)"
    scp -r "${SCP_ARGS[@]}" ./public/* "${DEPLOY_TARGET}:${DEPLOY_PATH}/"
fi

log "Fixing remote permissions"
ssh "${SSH_ARGS[@]}" "$DEPLOY_TARGET" \
    "find '$DEPLOY_PATH' -type d -exec chmod 755 {} +; find '$DEPLOY_PATH' -type f -exec chmod 644 {} +; test -f '$DEPLOY_PATH/index.html'"

log "Deployment finished: ${BASE_URL}"

