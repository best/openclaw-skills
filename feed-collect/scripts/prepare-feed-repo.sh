#!/usr/bin/env bash
# prepare-feed-repo.sh — safely prepare feed repo for deterministic collection.
set -euo pipefail

repo="${FEED_REPO:-${1:?FEED_REPO is required}}"
cd "$repo"

generated_paths=(.astro dist node_modules/.astro public/pagefind)

if git status --porcelain -- "${generated_paths[@]}" | grep -q .; then
  backup_dir=".git/feed-cron-backups"
  mkdir -p "$backup_dir"
  stamp="$(TZ=Asia/Shanghai date +%Y%m%d-%H%M%S)"
  backup_path="$backup_dir/generated-artifacts-$stamp.tgz"
  tar -czf "$backup_path" --ignore-failed-read "${generated_paths[@]}" 2>/dev/null || true
  git restore -- "${generated_paths[@]}" 2>/dev/null || true
  git clean -fd -- "${generated_paths[@]}" 2>/dev/null || true
  echo "cleaned generated artifacts; backup=$backup_path" >&2
fi

other_dirty="$(git status --porcelain -- . ':!.astro' ':!dist' ':!node_modules/.astro' ':!public/pagefind' ':!data/scored-results.json' ':!src/data/blog')"
if [ -n "$other_dirty" ]; then
  echo "refusing to pull; non-generated dirty files remain:" >&2
  printf '%s\n' "$other_dirty" >&2
  exit 2
fi

git pull --rebase --autostash
