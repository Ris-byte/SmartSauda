"""Portable launch command. No migrations or privileged credentials at startup."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn

if __name__ == "__main__":
    # Only trust explicitly configured proxy addresses. Never trust arbitrary
    # Forwarded/X-Forwarded-For headers from clients reaching the server directly.
    proxies = os.environ.get("FORWARDED_ALLOW_IPS", "")
    uvicorn.run("backend.asgi:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
                proxy_headers=bool(proxies), forwarded_allow_ips=proxies,
                workers=1, access_log=False)
