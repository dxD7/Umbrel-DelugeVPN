#!/usr/bin/env python3
"""DelugeVPN first-run setup page.

Serves a small form on port 8112 (the port Umbrel already points at), writes
vpn.env, then exits so the wrapper can start Deluge on the same port.
Only runs while VPN credentials are missing.
"""
import html
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

ENV_FILE = os.environ.get("DXD7_ENV_FILE", "/config/vpn.env")
PORT = int(os.environ.get("DXD7_PORT", "8112"))
OWNER = int(os.environ.get("PUID", "1000"))
GROUP = int(os.environ.get("PGID", "1000"))

PROVIDERS = {
    "pia": "Private Internet Access (PIA)",
    "protonvpn": "ProtonVPN",
    "airvpn": "AirVPN",
    "custom": "Custom (my own config files)",
}
CLIENTS = {"wireguard": "WireGuard", "openvpn": "OpenVPN"}

DEFAULTS = {
    "VPN_PROV": "pia",
    "VPN_CLIENT": "wireguard",
    "STRICT_PORT_FORWARD": "yes",
    "ENABLE_PRIVOXY": "no",
    "LAN_NETWORK": "192.168.1.0/24",
    "NAME_SERVERS": "84.200.69.80,37.235.1.174,1.1.1.1",
}

IP = r"\d{1,3}(?:\.\d{1,3}){3}"
LAN_RE = re.compile(rf"^{IP}/\d{{1,2}}(?:,{IP}/\d{{1,2}})*$")
DNS_RE = re.compile(rf"^{IP}(?:,{IP})*$")


def read_existing():
    """Read current values from vpn.env (same literal rules as the wrapper)."""
    values = dict(DEFAULTS)
    try:
        with open(ENV_FILE, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.rstrip("\r\n")
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                if key in DEFAULTS:
                    values[key] = val
    except OSError:
        pass
    return values


def render_form(values, error=""):
    def options(choices, selected):
        return "".join(
            f'<option value="{k}"{" selected" if k == selected else ""}>{html.escape(v)}</option>'
            for k, v in choices.items()
        )

    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DelugeVPN setup</title>
<!-- dxd7-setup -->
<style>
:root {{ --bg:#f4f5f7; --card:#fff; --text:#1c1f24; --muted:#5b6370; --line:#d5d9e0; --accent:#2f6fed; --err:#c0392b; color-scheme: light dark; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14161a; --card:#1e2127; --text:#e8eaee; --muted:#9aa3b2; --line:#343944; --accent:#5b8cff; --err:#ff7a6b; }} }}
body {{ margin:0; font:16px/1.5 system-ui,sans-serif; background:var(--bg); color:var(--text); }}
main {{ max-width:30rem; margin:0 auto; padding:2rem 1rem; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1.5rem; }}
h1 {{ margin:0 0 .25rem; font-size:1.4rem; }}
p.sub {{ margin:0 0 1.25rem; color:var(--muted); font-size:.95rem; }}
label {{ display:block; margin:1rem 0 .25rem; font-weight:600; font-size:.9rem; }}
input, select {{ width:100%; box-sizing:border-box; padding:.6rem .7rem; font:inherit; color:var(--text); background:var(--bg); border:1px solid var(--line); border-radius:8px; }}
small {{ display:block; margin-top:.25rem; color:var(--muted); font-size:.8rem; }}
button {{ margin-top:1.5rem; width:100%; padding:.75rem; font:inherit; font-weight:600; color:#fff; background:var(--accent); border:0; border-radius:8px; cursor:pointer; }}
details {{ margin-top:1rem; }}
summary {{ cursor:pointer; color:var(--muted); font-size:.9rem; }}
.err {{ color:var(--err); font-weight:600; }}
</style></head><body><main><div class="card">
<h1>DelugeVPN setup</h1>
<p class="sub">Enter your VPN details once. Deluge starts automatically afterwards.</p>
{err}
<form method="post" action="/">
<label for="prov">VPN provider</label>
<select id="prov" name="VPN_PROV">{options(PROVIDERS, values["VPN_PROV"])}</select>
<label for="client">Protocol</label>
<select id="client" name="VPN_CLIENT">{options(CLIENTS, values["VPN_CLIENT"])}</select>
<label for="user">VPN username</label>
<input id="user" name="VPN_USER" autocomplete="off" autocapitalize="off" spellcheck="false">
<label for="pass">VPN password</label>
<input id="pass" name="VPN_PASS" type="password" autocomplete="new-password">
<small>Stored in plain text in vpn.env on your Umbrel. For "Custom", username and password are optional.</small>
<details><summary>Advanced</summary>
<label for="lan">Home network (CIDR)</label>
<input id="lan" name="LAN_NETWORK" value="{html.escape(values["LAN_NETWORK"])}">
<label for="dns">DNS servers</label>
<input id="dns" name="NAME_SERVERS" value="{html.escape(values["NAME_SERVERS"])}">
</details>
<button type="submit">Save and start Deluge</button>
</form></div></main></body></html>"""


def render_done():
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DelugeVPN setup</title><!-- dxd7-setup -->
<style>
:root { color-scheme: light dark; }
body { font:16px/1.5 system-ui,sans-serif; display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0; padding:1rem; text-align:center; }
div.box { max-width:26rem; }
p { color:#7a8392; margin:.5rem 0; }
p.small { font-size:.85rem; }
#timer { font-variant-numeric:tabular-nums; }
.spin { width:2rem; height:2rem; margin:1rem auto; border:3px solid #7a839255; border-top-color:#7a8392; border-radius:50%; animation:s 1s linear infinite; }
@keyframes s { to { transform:rotate(360deg); } }
</style></head><body><div class="box">
<h1>Saved</h1>
<div class="spin"></div>
<p>Connecting to your VPN and starting Deluge. This usually takes 1 to 2 minutes.</p>
<p id="timer">0:00 elapsed</p>
<p class="small">This page opens Deluge automatically when it is ready. If you see an Umbrel error page in the meantime, Deluge just isn't up yet: wait a moment and refresh.</p>
</div>
<script>
const started = Date.now();
const timer = document.getElementById('timer');
setInterval(function () {
  const s = Math.floor((Date.now() - started) / 1000);
  timer.textContent = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') + ' elapsed';
}, 1000);
async function poll() {
  try {
    const r = await fetch('/', {cache: 'no-store'});
    if (r.status === 200) {
      const t = await r.text();
      const isSetup = t.includes('dxd7-setup');
      const isProxyError = /Oops, there was an error|error connecting to/i.test(t);
      if (!isSetup && !isProxyError) { location.replace('/'); return; }
    }
  } catch (e) {}
  setTimeout(poll, 3000);
}
poll();
</script></body></html>"""


def validate(form):
    def get(name):
        return form.get(name, [""])[0].strip("\r\n")

    prov, client = get("VPN_PROV"), get("VPN_CLIENT")
    user, pw = get("VPN_USER"), form.get("VPN_PASS", [""])[0]
    lan, dns = get("LAN_NETWORK").strip(), get("NAME_SERVERS").strip()

    if prov not in PROVIDERS:
        return None, "Please choose a provider."
    if client not in CLIENTS:
        return None, "Please choose a protocol."
    for label, val in (("username", user), ("password", pw)):
        if any(c in val for c in "\r\n\x00") or len(val) > 256:
            return None, f"The {label} contains characters that can't be saved."
    if prov != "custom" and (not user or not pw):
        return None, "Username and password are required for this provider."
    if not LAN_RE.match(lan):
        return None, "Home network must look like 192.168.1.0/24."
    if not DNS_RE.match(dns):
        return None, "DNS servers must be IP addresses separated by commas."
    return {"VPN_PROV": prov, "VPN_CLIENT": client, "VPN_USER": user,
            "VPN_PASS": pw, "LAN_NETWORK": lan, "NAME_SERVERS": dns}, ""


def write_env(new):
    existing = read_existing()
    values = {
        "VPN_PROV": new["VPN_PROV"],
        "VPN_CLIENT": new["VPN_CLIENT"],
        "VPN_USER": new["VPN_USER"] or "CHANGE_ME",
        "VPN_PASS": new["VPN_PASS"] or "CHANGE_ME",
        "STRICT_PORT_FORWARD": existing["STRICT_PORT_FORWARD"],
        "ENABLE_PRIVOXY": existing["ENABLE_PRIVOXY"],
        "LAN_NETWORK": new["LAN_NETWORK"],
        "NAME_SERVERS": new["NAME_SERVERS"],
        "SETUP_COMPLETE": "yes",
    }
    lines = [
        "# DelugeVPN settings - written by the setup page.",
        "# To change them, edit this file and restart the app.",
        "# One pair of outer quotes around a value is allowed; $ is taken literally.",
        "",
    ] + [f'{k}="{v}"' for k, v in values.items()] + [""]
    directory = os.path.dirname(ENV_FILE) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".vpn.env.")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    os.chmod(tmp, 0o600)
    try:
        os.chown(tmp, OWNER, GROUP)
    except OSError:
        pass
    os.replace(tmp, ENV_FILE)


class Handler(BaseHTTPRequestHandler):
    server_version = "dxd7-setup"

    def log_message(self, fmt, *args):
        sys.stderr.write("[dxd7-setup] " + fmt % args + "\n")

    def _send(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
            self.wfile.flush()

    def do_GET(self):
        self._send(render_form(read_existing()))

    do_HEAD = do_GET

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 8192:
            self._send(render_form(read_existing(), "Invalid request."), 400)
            return
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"),
                        keep_blank_values=True)
        new, error = validate(form)
        if error:
            self._send(render_form(read_existing(), error), 400)
            return
        write_env(new)
        self._send(render_done())
        threading.Timer(1.0, self.server.shutdown).start()


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
