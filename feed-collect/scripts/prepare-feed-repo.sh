#!/usr/bin/env bash
set -euo pipefail

repo="${1:-/data/code/github.com/astralor/feed}"
cd "$repo"

generated_paths=(.astro dist node_modules/.astro public/pagefind)

if [ -n "$(git status --porcelain -- "${generated_paths[@]}")" ]; then
  backup_dir=".git/feed-cron-backups"
  mkdir -p "$backup_dir"
  stamp="$(TZ=Asia/Shanghai date +%Y%m%d-%H%M%S)"
  backup_path="$backup_dir/generated-artifacts-$stamp.tgz"

  tar -czf "$backup_path" --ignore-failed-read "${generated_paths[@]}"
  git restore -- "${generated_paths[@]}"
  git clean -fd -- "${generated_paths[@]}"
  echo "cleaned generated artifacts; backup=$backup_path"
fi

other_dirty="$(git status --porcelain -- . ':!.astro' ':!dist' ':!node_modules/.astro' ':!public/pagefind')"
if [ -n "$other_dirty" ]; then
  echo "refusing to pull; non-generated dirty files remain:" >&2
  printf '%s\n' "$other_dirty" >&2
  exit 2
fi

git pull --rebase
