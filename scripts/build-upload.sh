#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".deploy.env" ]]; then
    # shellcheck disable=SC1091
    source ".deploy.env"
fi

HUGO_BIN="${HUGO_BIN:-hugo}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
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

if [[ "$DEPLOY_USER" == "root" ]]; then
    log "WARNING: deploying as root; prefer DEPLOY_USER=blogdeploy"
fi

command -v "$HUGO_BIN" >/dev/null 2>&1 || die "Hugo not found: $HUGO_BIN"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "Python not found: $PYTHON_BIN"

log "Building with Hugo"
"$HUGO_BIN" --gc --minify --cleanDestinationDir --baseURL "$BASE_URL"
[[ -f "public/index.html" ]] || die "public/index.html was not generated"

log "Checking internal links"
"$PYTHON_BIN" scripts/check_links.py

log "Checking release quality"
"$PYTHON_BIN" scripts/quality_check.py

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

STAMP="$(date -u +%Y%m%d-%H%M%S)"
RELEASE_ID="${STAMP}-${RANDOM}"
RELEASE_PATH="/var/www/blog-release-${RELEASE_ID}"
BACKUP_PATH="/var/www/blog-old-${RELEASE_ID}"
FAILED_PATH="/var/www/blog-failed-${RELEASE_ID}"
ARCHIVE_NAME="xuanwo-blog-${RELEASE_ID}.tar.gz"
LOCAL_ARCHIVE="$(mktemp -t xuanwo-blog.XXXXXX.tar.gz)"
REMOTE_ARCHIVE="/tmp/${ARCHIVE_NAME}"

cleanup() {
    rm -f -- "$LOCAL_ARCHIVE"
}
trap cleanup EXIT

rollback() {
    ssh "${SSH_ARGS[@]}" "$DEPLOY_TARGET" \
        "if [ -d '$BACKUP_PATH' ]; then if [ -e '$DEPLOY_PATH' ]; then mv -- '$DEPLOY_PATH' '$FAILED_PATH'; fi; mv -- '$BACKUP_PATH' '$DEPLOY_PATH'; fi"
}

log "Packaging public/"
tar -C public -czf "$LOCAL_ARCHIVE" .

log "Uploading release archive"
scp "${SCP_ARGS[@]}" "$LOCAL_ARCHIVE" "${DEPLOY_TARGET}:${REMOTE_ARCHIVE}"

log "Preparing atomic release at ${RELEASE_PATH}"
REMOTE_SCRIPT=$(
    cat <<EOF
set -eu
archive='${REMOTE_ARCHIVE}'
release='${RELEASE_PATH}'
deploy='${DEPLOY_PATH}'
backup='${BACKUP_PATH}'
mkdir -p -- "\$release"
tar -xzf "\$archive" -C "\$release"
find "\$release" -type d -exec chmod 755 {} +
find "\$release" -type f -exec chmod 644 {} +
test -f "\$release/index.html"
if [ -e "\$deploy" ]; then mv -- "\$deploy" "\$backup"; fi
if ! mv -- "\$release" "\$deploy"; then
  if [ -e "\$backup" ] && [ ! -e "\$deploy" ]; then mv -- "\$backup" "\$deploy"; fi
  exit 1
fi
rm -f -- "\$archive"
EOF
)

if ! ssh "${SSH_ARGS[@]}" "$DEPLOY_TARGET" "$REMOTE_SCRIPT"; then
    die "Remote release swap failed"
fi

log "Verifying live site"
if ! curl -fsS --max-time 20 "$BASE_URL" >/tmp/xuanwo-blog-health.html; then
    rollback
    die "Live site health request failed"
fi

if ! grep -Eq 'class=stat-num[^>]*data-count="?[1-9][0-9]*"?[^>]*>[1-9][0-9]*<' /tmp/xuanwo-blog-health.html; then
    rollback
    die "Live homepage does not contain rendered non-zero counters"
fi

rm -f -- /tmp/xuanwo-blog-health.html
log "Deployment finished: ${BASE_URL}"
log "Rollback directory: ${BACKUP_PATH}"
