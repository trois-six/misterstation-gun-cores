#!/usr/bin/env bash
# Free disk space on a GitHub-hosted Ubuntu runner: the Quartus image (~8 GB
# unpacked), its cached archive and a Saturn/PSX build tree do not fit in the
# default free space. Removes preinstalled SDKs the build never uses.
set -u
df -h / | tail -n1
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /usr/local/.ghcup \
  /opt/hostedtoolcache/CodeQL /usr/local/share/boost /usr/share/swift \
  /usr/local/share/powershell /usr/local/lib/node_modules /opt/az /opt/microsoft \
  /opt/google /usr/lib/jvm 2>/dev/null || true
docker image prune --all --force >/dev/null 2>&1 || true
sudo swapoff -a 2>/dev/null && sudo rm -f /mnt/swapfile /swapfile 2>/dev/null || true
df -h / | tail -n1
