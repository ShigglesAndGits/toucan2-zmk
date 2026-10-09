#!/usr/bin/env bash
# Wait for a XIAO nRF52840 UF2 bootloader drive, then copy the given UF2 onto it.
#   scripts/flash-when-ready.sh firmware/<half>.uf2 [timeout-seconds]
set -euo pipefail
uf2=$1; timeout=${2:-1800}
[[ -f $uf2 ]] || { echo "no such file: $uf2"; exit 1; }
echo "waiting for XIAO bootloader drive (double-tap RST)..."
deadline=$((SECONDS + timeout))
while (( SECONDS < deadline )); do
  dev=$(lsblk -rpno NAME,LABEL | awk '$2 ~ /^XIAO/ {print $1; exit}')
  if [[ -n $dev ]]; then
    mnt=$(lsblk -no MOUNTPOINT "$dev" | head -1)
    if [[ -z $mnt ]]; then
      udisksctl mount -b "$dev" >/dev/null 2>&1 || true
      mnt=$(lsblk -no MOUNTPOINT "$dev" | head -1)
    fi
    # Only write to a real UF2 bootloader for the XIAO nRF52840.
    if [[ -n $mnt && -f $mnt/INFO_UF2.TXT ]] && grep -qi 'nrf52840' "$mnt/INFO_UF2.TXT"; then
      echo "found $dev at $mnt: $(grep -i 'board-id' "$mnt/INFO_UF2.TXT" || true)"
      cp "$uf2" "$mnt/" && sync || true   # drive vanishes mid-sync when it reboots; that's normal
      echo "copied $(basename "$uf2"); waiting for reboot..."
      for _ in $(seq 30); do lsblk -rno LABEL | grep -q '^XIAO' || { echo "drive gone - flashed OK"; exit 0; }; sleep 1; done
      echo "WARNING: drive still present 30s after copy"; exit 2
    fi
  fi
  sleep 1
done
echo "timed out waiting for the drive"; exit 3
