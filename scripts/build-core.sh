#!/usr/bin/env bash
# Build one MiSTer core with the Sinden light gun border.
#
# usage: build-core.sh NAME REPO COMMIT PROJECT REVISION IMAGE OUT_DIR [BORDER INSET]
#
#   NAME      core name used for the asset (<NAME>-Sinden_<YYYYMMDD>.rbf)
#   REPO      upstream GitHub repository (owner/name)
#   COMMIT    upstream commit to build
#   PROJECT   Quartus project (.qpf without extension)
#   REVISION  Quartus revision (.qsf without extension)
#   IMAGE     Docker image providing quartus_sh (Quartus Prime Lite)
#   OUT_DIR   receives the .rbf, its manifest (<asset>.json) and the build logs
#
# The upstream sources are checked out at COMMIT, sys/ascal.vhd is patched by
# sinden_border.py (the script fails, and this build with it, if the patch
# does not apply), and the full Quartus flow runs inside IMAGE. Nothing else of
# the core is changed.
set -euo pipefail

name=$1 repo=$2 commit=$3 project=$4 revision=$5 image=$6 out=$7
border=${8:-20} inset=${9:-28}
here=$(cd "$(dirname "$0")" && pwd)
work=${WORK_DIR:-$(mktemp -d)}/src-$name
mkdir -p "$out"
out=$(cd "$out" && pwd)

echo "::group::checkout $repo@$commit"
rm -rf "$work"; mkdir -p "$work"
git -C "$work" init -q
git -C "$work" fetch -q --depth=1 "https://github.com/$repo" "$commit"
git -C "$work" checkout -q FETCH_HEAD
git -C "$work" submodule update --init --recursive --depth=1 -q || true
commit_date=$(git -C "$work" log -1 --format=%cI)
echo "::endgroup::"

python3 -I "$here/sinden_border.py" --border "$border" --inset "$inset" "$work/sys/ascal.vhd"
git -C "$work" diff --ignore-cr-at-eol --stat

echo "::group::quartus $project / $revision"
start=$(date +%s)
status=0
docker run --rm -v "$work:/project" -w /project "$image" \
  quartus_sh --flow compile "$project" -c "$revision" > "$out/$name-quartus.log" 2>&1 || status=$?
secs=$(( $(date +%s) - start ))
tail -n 40 "$out/$name-quartus.log"
for f in "$work"/output_files/"$revision".{flow,map,fit,sta}.summary; do
  [ -f "$f" ] && cp "$f" "$out/$name-$(basename "$f")"
done
echo "::endgroup::"
echo "quartus exit $status after ${secs}s"
if [ "$status" -ne 0 ]; then
  grep -E "^(Error|Critical Warning)" "$out/$name-quartus.log" | head -n 30 >&2 || true
  exit "$status"
fi
# Timing is recorded, not enforced: MiSTer releases routinely ship with
# negative slack in the core's own clocks. The patch only adds logic to the
# scaler's output (HDMI) clock, so a failure there is flagged.
slack_json=$(python3 -I "$here/setup_slack.py" "$work/output_files/$revision.sta.summary")
echo "setup slack per clock (worst corner): $slack_json"

rbf="$work/output_files/$revision.rbf"
[ -f "$rbf" ] || { echo "::error::$rbf not produced" >&2; exit 1; }
date=$(date -u +%Y%m%d)
asset="$name-Sinden_$date.rbf"
cp "$rbf" "$out/$asset"
sha=$(sha256sum "$out/$asset" | cut -d' ' -f1)
size=$(stat -c %s "$out/$asset")

python3 -I - "$out/$asset.json" <<PY
import json, sys
json.dump({
    "core": "$name",
    "asset": "$asset",
    "sha256": "$sha",
    "size": $size,
    "upstream_repo": "$repo",
    "upstream_commit": "$commit",
    "upstream_commit_date": "$commit_date",
    "quartus_project": "$project",
    "quartus_revision": "$revision",
    "quartus_image": "$image",
    "border": $border,
    "inset": $inset,
    **json.loads("""$slack_json"""),
    "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "build_seconds": $secs,
}, open(sys.argv[1], "w"), indent=2)
PY
cat "$out/$asset.json"
