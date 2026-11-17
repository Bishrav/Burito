#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
log() { printf 'Burito auto-update: %s\n' "$*"; }
fail() { log "$*" >&2; exit 1; }

[[ -d "$repo/.git" ]] || fail "expected a normal Git checkout at $repo"
cd "$repo"

branch="$(git symbolic-ref --quiet --short HEAD)" || fail "detached HEAD; skipping"
[[ "$branch" == main ]] || fail "branch is '$branch', expected main; skipping"
upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}')" || fail "main has no upstream; skipping"
[[ "$upstream" == origin/main ]] || fail "upstream is '$upstream', expected origin/main; skipping"

remote="$(git remote get-url origin)"
case "$remote" in
  https://github.com/Bishrav/Burito.git|git@github.com:Bishrav/Burito.git) ;;
  *) fail "origin is not the expected Burito GitHub repository; skipping" ;;
esac

lock_path="$(git rev-parse --git-path burito-auto-update.lock)"
exec 9>"$lock_path"
flock -n 9 || { log "another update check is running"; exit 0; }

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  log "local changes found; update deferred to protect your work"
  exit 0
fi

# Do not replace source files while an Eve chat or local web runtime is active.
if pgrep -af "$repo/runtime/node_modules/.bin/eve" >/dev/null; then
  log "Eve is running; update deferred until the chat/runtime is closed"
  exit 0
fi

git fetch --quiet origin '+refs/heads/main:refs/remotes/origin/main' || fail "fetch failed; will retry on the next timer"
if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  log "local changes appeared during fetch; update deferred"
  exit 0
fi

if ! git diff --quiet HEAD origin/main -- runtime/package.json runtime/package-lock.json \
  requirements.txt requirements-dev.txt pyproject.toml; then
  log "dependency manifests changed upstream; update deferred for manual dependency review"
  exit 0
fi

if git merge-base --is-ancestor HEAD origin/main; then
  if [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]]; then
    log "already current"
    exit 0
  fi
  git merge --ff-only --quiet origin/main || fail "fast-forward failed; inspect the checkout manually"
  log "updated to $(git rev-parse --short HEAD)"
else
  fail "local main is ahead of or diverged from origin/main; refusing to rewrite history"
fi
