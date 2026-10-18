# DelugeVPN for Umbrel

[Deluge](https://deluge-torrent.org/) running entirely inside a VPN tunnel, with a kill switch, for [umbrelOS](https://umbrel.com). Packaged from [binhex/arch-delugevpn](https://github.com/binhex/arch-delugevpn) and preconfigured for Private Internet Access (WireGuard).

> Unofficial community package. Not affiliated with binhex, Umbrel, or any VPN provider.

## Features

- All traffic goes through your VPN, and is blocked if the tunnel drops
- Works with PIA out of the box; other providers supported through binhex
- Settings live in one small file that survives app updates
- No extra ports opened on your network by default

## Install

1. In umbrelOS go to **App Store → ⋯ → Community App Stores** and add:
   ```
   https://github.com/dxD7/Umbrel-DelugeVPN
   ```
2. Install **DelugeVPN**. It won't connect to the VPN yet.
3. Open the **Files** app and edit `Apps/dxd7-deluge-vpn/data/vpn.env` (choose "Edit anyway" if prompted).
4. Set your provider, protocol, username and password, then save.
5. Restart the app from the Umbrel dashboard and open it.
6. Log in to Deluge with the default password `deluge` and **change it right away** under **Preferences**.

## Configuration

Everything you need to change is in `Apps/dxd7-deluge-vpn/data/vpn.env`. Restart the app after editing.

| Setting | Default | Description |
|---|---|---|
| `VPN_PROV` | `pia` | `pia`, `airvpn`, `protonvpn` or `custom` |
| `VPN_CLIENT` | `wireguard` | `wireguard` or `openvpn` |
| `VPN_USER` | `CHANGE_ME` | VPN account username |
| `VPN_PASS` | `CHANGE_ME` | VPN account password (wrap in single quotes if it contains `$`) |
| `STRICT_PORT_FORWARD` | `yes` | PIA/ProtonVPN only: require a forwarded port |
| `ENABLE_PRIVOXY` | `no` | HTTP proxy through the VPN (also needs port 8118 published) |
| `LAN_NETWORK` | `192.168.1.0/24` | Your home subnet; only needed if you publish extra ports |
| `NAME_SERVERS` | binhex defaults | DNS servers, comma separated |

## Supported providers

| Provider | Status |
|---|---|
| PIA (WireGuard) | Tested |
| PIA (OpenVPN) | Untested |
| ProtonVPN | Untested |
| AirVPN | Untested |
| Custom (Mullvad, etc.) | Untested |

Untested means it follows binhex's documented behavior but hasn't been verified by me.

<details>
<summary><b>Using a provider other than PIA</b></summary>

Set `VPN_PROV` and `VPN_CLIENT` in `vpn.env`. Some providers, and `custom`, also need a config file instead of (or as well as) a username and password:

- OpenVPN: put your `.ovpn` file(s) in `Apps/dxd7-deluge-vpn/data/openvpn/`
- WireGuard: put `wg0.conf` in `Apps/dxd7-deluge-vpn/data/wireguard/`

If those folders don't exist yet, start and stop the app once to create them. See [binhex's documentation](https://github.com/binhex/arch-delugevpn) for each provider's exact requirements.

</details>

## Security

<details>
<summary><b>What this package does, and what to know</b></summary>

- **Kill switch:** `VPN_ENABLED` is fixed to `yes` and can't be turned off from `vpn.env`. binhex's firewall rules block traffic if the tunnel drops.
- **Deluge's password is the only login:** anyone on your network who can reach the app can see the page, so change the default `deluge` password right after installing. To also require your Umbrel login, remove the `PROXY_AUTH_ADD: "false"` line in `docker-compose.yml`.
- **No extra ports opened:** the Deluge web UI is reachable through Umbrel as usual, but the other ports (Privoxy 8118, Deluge daemon 58846, torrent traffic) are not opened on your network. Other Umbrel apps can still reach Deluge over Umbrel's internal Docker network. If you need direct access to Privoxy or the daemon, uncomment the `ports` section in `docker-compose.yml`.
- **Privileged container:** binhex documents that WireGuard needs privileged mode plus a sysctl, so the container runs privileged. If you only use OpenVPN you can try `cap_add: NET_ADMIN` instead (see comments in `docker-compose.yml`; untested).
- **Plain-text credentials:** your VPN login is stored in `vpn.env` on your Umbrel. Don't share that file.
- **Verify the tunnel:** from a shell inside the container, `curl ifconfig.me` should print your VPN's IP, not your home IP.

</details>

## Updating

The app follows binhex's `2.2` release line. When a new package version appears in Umbrel, update it from the App Store. Your `vpn.env` is kept. New settings added in later versions are listed in the [changelog](CHANGELOG.md) and won't appear in your existing file automatically.

## Troubleshooting

| Problem | What to check |
|---|---|
| App starts but never connects | `VPN_USER` and `VPN_PASS` aren't still `CHANGE_ME`; provider and protocol are correct |
| Login fails with a valid password | Try a simple password to rule out special characters; single-quote it if it contains `$` |
| Other apps can't write to downloads | Files are created with permissions `664`/`775`; check the other app runs as user 1000 |
| Need more detail | The log is `Apps/dxd7-deluge-vpn/data/supervisord.log` |

Issues and provider test reports are welcome on the [issue tracker](https://github.com/dxD7/Umbrel-DelugeVPN/issues).

## Credits

All the heavy lifting is [binhex's](https://github.com/binhex/arch-delugevpn) work. This repo only packages it for Umbrel.
