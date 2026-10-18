#!/bin/bash
# DelugeVPN start wrapper (runs instead of the image's default command).
#  - If VPN credentials are already in vpn.env: load them and start binhex as usual.
#  - If not: serve a small setup form on port 8112, wait for it to be saved,
#    then start binhex. No manual file editing or restart needed.

ENV_FILE="${DXD7_ENV_FILE:-/config/vpn.env}"
SETUP_PY="${DXD7_SETUP_PY:-/setup/setup.py}"

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

while true; do
  unset VPN_USER VPN_PASS SETUP_COMPLETE
  load_env
  if is_configured; then
    break
  fi
  echo "[dxd7] VPN not configured yet - starting setup page on port 8112"
  python3 "$SETUP_PY" || sleep 2
done

# The VPN (and its kill switch) can never be switched off from vpn.env.
export VPN_ENABLED=yes

echo "[dxd7] VPN settings found - starting binhex"
exec /bin/bash init.sh
