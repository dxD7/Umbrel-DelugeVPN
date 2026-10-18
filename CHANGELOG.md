# Changelog

## 2.0.0
- New app: **DelugeVPN** (`dxd7-deluge-vpn`), replacing the one-day "Deluge PIA" test.
- Settings (provider, protocol, credentials, DNS, LAN) moved to `data/vpn.env`.
- Image follows binhex's `2.2` release line instead of `latest`.
- No ports published to the LAN by default; Privoxy off by default.
- `UMASK` tightened from 000 to 002.
- `VPN_ENABLED` is fixed to `yes` so the VPN and kill switch can't be switched off by accident.
