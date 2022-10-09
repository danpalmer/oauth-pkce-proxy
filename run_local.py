"""
Local run script for debugging purposes.

In production oauth_pkce_proxy should be run with:

$ uvicorn oauth_pkce_proxy.asgi:app
"""

import uvicorn

from oauth_pkce_proxy.app import create_app

if __name__ == "__main__":
    app = create_app(local=True)
    uvicorn.run(app, host="127.0.0.1", port=8000)
