#!/bin/bash
# DelugeVPN start wrapper (runs instead of the image's default command).
#  - If VPN credentials are already in vpn.env: load them and start binhex as usual.
#  - If not: serve a small setup form on port 8112, wait for it to be saved,
#    then start binhex. No manual file editing or restart needed.

ENV_FILE="${DXD7_ENV_FILE:-/config/vpn.env}"
SETUP_PY="${DXD7_SETUP_PY:-/setup/setup.py}"
INIT_SH="${DXD7_INIT_SH:-init.sh}"

# Reads KEY=VALUE lines literally (no shell evaluation, no $ expansion).
# One pair of matching outer quotes around a value is removed.
load_env() {
  [ -f "$ENV_FILE" ] || return 0
  local line key val first last
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in *=*) ;; *) continue ;; esac
    key="${line%%=*}"
    val="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    if [ "${#val}" -ge 2 ]; then
      first="${val:0:1}"
      last="${val: -1}"
      if [ "$first" = "$last" ] && { [ "$first" = '"' ] || [ "$first" = "'" ]; }; then
        val="${val:1:${#val}-2}"
      fi
    fi
    export "$key=$val"
  done < "$ENV_FILE"
}

is_configured() {
  [ "$SETUP_COMPLETE" = "yes" ] && return 0
  [ -n "$VPN_USER" ] && [ "$VPN_USER" != "CHANGE_ME" ] \
    && [ -n "$VPN_PASS" ] && [ "$VPN_PASS" != "CHANGE_ME" ]
}

# binhex's init.sh overwrites VPN_REMOTE_SERVER with a fixed default (Amsterdam)
# on first run, ignoring the value we pass in (upstream issue binhex/arch-qbittorrentvpn#377).
# Make it respect the variable when one was chosen. This is a no-op if the line
# isn't there (for example once upstream fixes it) and is reverted if it breaks the script.
patch_binhex() {
  [ -n "$VPN_REMOTE_SERVER" ] || return 0
  local f="$INIT_SH"
  [ -f "$f" ] || f="$(command -v init.sh 2>/dev/null)"
  if [ -z "$f" ] || [ ! -f "$f" ] || [ ! -w "$f" ]; then
    echo "[dxd7] could not find a writable init.sh - your server choice may be ignored"
    return 0
  fi
  if grep -qF 'export VPN_REMOTE_SERVER="nl-amsterdam.privacy.network"' "$f"; then
    cp "$f" "$f.dxd7.bak"
    sed -i 's|export VPN_REMOTE_SERVER="nl-amsterdam\.privacy\.network"|export VPN_REMOTE_SERVER="${VPN_REMOTE_SERVER:-nl-amsterdam.privacy.network}"|g' "$f"
    if bash -n "$f" 2>/dev/null; then
      rm -f "$f.dxd7.bak"
      echo "[dxd7] patched binhex init.sh so your server choice is honored"
    else
      mv "$f.dxd7.bak" "$f"
      echo "[dxd7] patch failed the syntax check and was reverted"
    fi
  elif grep -qF '${VPN_REMOTE_SERVER:-nl-amsterdam.privacy.network}' "$f"; then
    echo "[dxd7] binhex init.sh already honors your server choice"
  else
    echo "[dxd7] binhex init.sh has no fixed default server - nothing to patch"
  fi
}

while true; do
  unset VPN_USER VPN_PASS SETUP_COMPLETE VPN_REMOTE_SERVER
  load_env
  if is_configured; then
    break
  fi
  echo "[dxd7] VPN not configured yet - starting setup page on port 8112"
  python3 "$SETUP_PY" || sleep 2
done

# An empty server setting means "use binhex's default", so it must be unset.
[ -n "$VPN_REMOTE_SERVER" ] || unset VPN_REMOTE_SERVER

# The VPN (and its kill switch) can never be switched off from vpn.env.
export VPN_ENABLED=yes

patch_binhex
echo "[dxd7] provider=${VPN_PROV:-?} client=${VPN_CLIENT:-?} server=${VPN_REMOTE_SERVER:-default}"
echo "[dxd7] VPN settings found - starting binhex"
exec /bin/bash init.sh
