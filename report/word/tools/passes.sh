#!/bin/zsh
# Build the project report until its page numbers settle.
# Pages renders each build to PDF; page_map.py reads the PDF text and writes pages.json
# (contents/figure/table page numbers and stranded-caption breaks) for the next build.
#
#   report/word/tools/passes.sh [python-with-python-docx] [max passes]
set -u
HERE=${0:A:h}
WORD=${HERE:h}
PY=${1:-python3}
Q="$HOME/Downloads/.indicbridge_qa"   # Pages only opens files from user folders such as Downloads
TMP=$(mktemp -d)
mkdir -p "$Q"
cd "$WORD" || exit 1
for i in $(seq 1 ${2:-5}); do
  "$PY" build_report.py loop.docx pages.json | tail -1 || exit 1
  cp loop.docx "$Q/loop.docx"
  rm -f "$Q/loop.pdf"
  osascript "$HERE/pages_export.applescript" "$Q/loop.docx" "$Q/loop.pdf" >/dev/null 2>&1
  swift "$HERE/pagetext.swift" "$Q/loop.pdf" "$TMP/pages.json" | tail -1
  cp pages.json "$TMP/before.json"
  python3 page_map.py "$TMP/pages.json" pages.json | tail -2
  if python3 -c "import json,sys; sys.exit(json.load(open('$TMP/before.json')) != json.load(open('pages.json')))"; then
    echo "stable after pass $i: $WORD/loop.docx and $Q/loop.pdf"
    exit 0
  fi
done
echo "page numbers did not settle"
exit 1
