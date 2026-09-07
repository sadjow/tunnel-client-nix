#!/usr/bin/env bash
set -euo pipefail

tested_sha="$1"
remote_main=$(git ls-remote origin refs/heads/main | cut -f1)
if [[ "$remote_main" != "$tested_sha" ]]; then
  echo "A newer main commit is awaiting validation; leaving tags unchanged."
  exit 0
fi

version=$(jq -r .version release.json)
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
if ! git show-ref --verify --quiet "refs/tags/v$version"; then
  git tag -a "v$version" "$tested_sha" -m "Release v$version"
  git push origin "refs/tags/v$version"
fi
git tag -fa latest "$tested_sha" -m "Latest release: v$version"
git tag -fa "v${version%%.*}" "$tested_sha" -m "Latest major release: v$version"
git push --atomic --force origin refs/tags/latest "refs/tags/v${version%%.*}"
