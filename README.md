# oauth-pkce-proxy

This codebase implements an OAuth PKCE Proxy. PKCE is the new flow for OAuth designed for client applications that can't store a client secret. For OAuth providers that do not yet support the PKCE flow, this proxy can be used to provide a PKCE-compliant proxy-provider for PKCE clients.

### Dual mode

This codebase implements two modes (aspirational).

1. A standard PKCE implementation, configured server-side with the necessary _authorize_ URI, _access token_ URI, and _client secret_.
2. A multi-provider supporting, client-configured, PKCE implementation, that takes these configuration values from incoming requests.

The latter is designed to support [esoteric OAuth implementations](https://developers.monzo.com/) that do not support more than one user per registered OAuth client. As this requires no server-side per-use-case configuration, a public instance is provided at <https://oauth-pkce-proxy-public.fly.dev/>.

### Architecture

`oauth-pkce-proxy` is a lightweight Python application, based on Falcon and Uvicorn. It uses Redis for ephemeral storage.
