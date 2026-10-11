#!/usr/bin/env bash
# Regenerate reference.html, smoke-test it, and publish it to
# https://keymap.home.bironfamily.net (caddy-internal on gloves-of-thievery, .20).
#
#   scripts/deploy-site.sh            # generate + check + publish
#   SKIP_CHECK=1 scripts/deploy-site.sh
#
# Files land in /root/caddy-internal/static/keymap/ (mounted read-only into the
# caddy-internal container as /srv/static). version.txt lets open copies of the
# page notice the update and reload themselves.
set -euo pipefail
cd "$(dirname "$0")/.."

HOST=${KEYMAP_HOST:-root@10.100.10.20}
DEST=/root/caddy-internal/static/keymap

python3 scripts/reference.py
if [[ -z "${SKIP_CHECK:-}" ]]; then
  node scripts/check-site.mjs reference.html
fi

version=$(python3 - <<'EOF'
import json, re
page = open("reference.html").read()
data = json.loads(re.search(r"const D = (\{.*?\});\n", page, re.S).group(1))
print(f"{data['rev']} {data['generated']}")
EOF
)

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp reference.html "$tmp/index.html"
printf '%s\n' "$version" > "$tmp/version.txt"

ssh -o BatchMode=yes "$HOST" "mkdir -p $DEST"
# Upload beside the live files, then rename into place so a reader never sees half a page.
scp -q "$tmp/index.html" "$HOST:$DEST/index.html.new"
scp -q "$tmp/version.txt" "$HOST:$DEST/version.txt.new"
ssh -o BatchMode=yes "$HOST" "cd $DEST && chmod 644 index.html.new version.txt.new && mv index.html.new index.html && mv version.txt.new version.txt"

echo "published $version -> https://keymap.home.bironfamily.net"
