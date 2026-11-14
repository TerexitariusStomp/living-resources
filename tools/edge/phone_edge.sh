# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/phone_edge.sh — bootstrap a phone-class edge node.
#
# The "cheap edge": any Linux-capable phone or single-board computer
# becomes a Playnet edge — it runs the durable UDP ingest + classifier
# and uplinks over whatever link it has (cellular, WiFi, or a CAT-1
# modem riding carrier direct-to-cell). It senses nothing itself; it is
# the smart half of a dumb node.
#
# Usage: ./phone_edge.sh [--install-only]
# Env overrides: EDGE_PORT (default 5055), EDGE_OUT, EDGE_STORE.

set -eu

EDGE_PORT="${EDGE_PORT:-5055}"
EDGE_OUT="${EDGE_OUT:-$HOME/ecocell-edge/ledger.jsonl}"
EDGE_STORE="${EDGE_STORE:-$HOME/ecocell-edge/store}"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HOME/ecocell-edge"

if command -v apt-get >/dev/null 2>&1; then
    PKG_MGR="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
else
    PKG_MGR="none"
fi

case "$PKG_MGR" in
    apt)   sudo apt-get update -qq && sudo apt-get install -y -qq python3 >/dev/null ;;
    dnf)   sudo dnf install -y -q python3 >/dev/null ;;
    pacman) sudo pacman -Sy --noconfirm python >/dev/null ;;
    none)  echo "no supported pkg manager — need python3 on PATH" >&2; exit 1 ;;
esac

command -v python3 >/dev/null || { echo "python3 missing after install" >&2; exit 1; }

echo "edge bootstrap: python3 $(python3 --version 2>&1 | awk '{print $2}')"
echo "  ledger : $EDGE_OUT"
echo "  store  : $EDGE_STORE"
echo "  port   : $EDGE_PORT (UDP — open it on the LAN the nodes join)"

cat <<EOF

Next:
  1. Field nodes join this edge's WiFi/LAN and send DET1/ENV1/AUD1 frames
     to UDP port $EDGE_PORT (firmware EDGE_PORT constant).
  2. Run the durable ingest:
       python3 $HERE/udp_edge.py --port $EDGE_PORT \\
           --out $EDGE_OUT --store $EDGE_STORE --via wifi
     --via labels committed records with the backhaul path
     (wifi | lora | cat1-sat | starlink-sat — adapters/backhaul.scm).
  3. Optional classifier on the committed spool:
       python3 $HERE/classify.py --spool <committed-audio-dir> \\
           --out detections.jsonl --backend none
  4. Uplink onward: point the edge host at the Playnet gateway, or —
     on cellular/satellite — run behind whatever NAT/tunnel the link
     provides; records are content-hashed so retries are idempotent.

On Android: run this inside Termux (pkg install python) or a chroot —
the scripts are plain CPython, no node-only deps.
EOF
