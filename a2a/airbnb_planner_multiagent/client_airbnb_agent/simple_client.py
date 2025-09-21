#!/usr/bin/env python3
import os, sys, json, argparse, requests
from urllib.parse import urljoin

# Common places an A2A/Starlette app might expose the card/health
PROBE_PATHS = [
    "/healthz",
    "/agent/card",
    "/agent-card",
    "/agent",
    "/.well-known/agent-card.json",
    "/card",
    "/",
]

def pretty(d): return json.dumps(d, indent=2, sort_keys=True)

def get_json(session, base, path):
    try:
        r = session.get(urljoin(base, path), timeout=10)
        ctype = r.headers.get("content-type","")
        if r.ok and "application/json" in ctype:
            return r.json(), r
        # some frameworks return JSON without a content-type
        if r.ok:
            try:
                return r.json(), r
            except Exception:
                pass
        return None, r
    except requests.RequestException as e:
        return {"_error": str(e)}, None

def main():
    ap = argparse.ArgumentParser(description="Probe an A2A server and print its AgentCard/capabilities.")
    ap.add_argument("--base-url", default=os.getenv("A2A_BASE_URL", "http://localhost:8081/"),
                    help="Base URL of the A2A server (default: %(default)s)")
    ap.add_argument("--token", default=os.getenv("A2A_TOKEN"),
                    help="Optional Bearer token")
    ap.add_argument("--insecure", action="store_true", help="Skip TLS verification")
    args = ap.parse_args()

    base = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    headers = {"Accept": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    s = requests.Session()
    s.headers.update(headers)
    verify = not args.insecure

    print(f"Probing {base}")
    # 1) Health probe (best-effort)
    j, r = get_json(s, base, "/healthz")
    if j is not None:
        print("• /healthz:", r.status_code if r else "ERR", pretty(j) if isinstance(j, dict) else j)
    else:
        print("• /healthz: (no JSON)")

    # 2) Try to find an AgentCard
    card = None
    card_path = None
    for p in PROBE_PATHS[1:]:
        try:
            resp = s.get(urljoin(base, p), timeout=10, verify=verify)
            if resp.ok:
                try:
                    data = resp.json()
                except Exception:
                    continue
                # Heuristic: AgentCard likely has name/description/url/capabilities/skills
                if isinstance(data, dict) and (
                    "capabilities" in data or
                    {"name","description"}.issubset(data.keys())
                ):
                    card, card_path = data, p
                    break
        except requests.RequestException:
            continue

    if card:
        print(f"\n✅ AgentCard found at {card_path}:")
        print(pretty(card))
        caps = card.get("capabilities", {})
        # Capabilities may be object or list; handle both
        print("\nCapabilities summary:")
        if isinstance(caps, dict):
            for k, v in caps.items():
                print(f"  - {k}: {v}")
        elif isinstance(caps, list):
            for k in caps:
                print(f"  - {k}")
        else:
            print(f"  (unrecognized format: {caps!r})")
    else:
        print("\n❌ Could not find an AgentCard JSON at common endpoints.")
        print("Tried:", ", ".join(PROBE_PATHS[1:]))
        print("Tip: expose one of these routes (e.g., /agent-card) to return your AgentCard dict.")

if __name__ == "__main__":
    # Silence InsecureRequestWarning when --insecure is used
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass
    main()
