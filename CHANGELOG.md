# Changelog

## 2.1.0
- First-run setup page: open the app after installing and enter your VPN details. Deluge starts automatically, with no file editing or restart.
- PIA + WireGuard: choose a server location in the setup form (live list from PIA, with a built-in fallback), or change it later in `vpn.env`.
- Startup wrapper loads `data/vpn.env` literally (no `$` expansion) and keeps the WireGuard endpoint in sync with `VPN_REMOTE_SERVER`.
- Works around binhex ignoring `VPN_REMOTE_SERVER` on first run (guarded patch, reverted if it fails a syntax check).
- `vpn.env` documents optional advanced binhex settings.
- Image follows binhex's `2.2` release line instead of `latest`.
- No ports published to the LAN by default; Privoxy off by default.
- `UMASK` tightened from 000 to 002; `VPN_ENABLED` is always `yes`; Deluge web password explicitly required.
