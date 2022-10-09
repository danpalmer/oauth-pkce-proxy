import base64
import hashlib
import os
import urllib.parse

import falcon.asgi
import httpx
import pkce
import redis.asyncio as redis
from falcon import HTTP_302, HTTPBadRequest, HTTPFound


def create_app(local=False):
    storage = Storage(os.environ.get("REDIS_URL", "redis://localhost"))
    http_client = HTTPClient()

    app = falcon.asgi.App(middleware=[storage, http_client])
    app.add_route("/", IndexResource())
    app.add_route("/authorize", AuthorizeResource())
    app.add_route("/code", CodeResource())
    app.add_route("/access_token", AccessTokenResource())
    app.add_route("/refresh_access_token", RefreshResource())

    if local:
        app.resp_options.secure_cookies_by_default = False
        app.add_error_handler(Exception, print)

    return app


# Handlers


class IndexResource:
    async def on_get(self, req, resp):
        resp.text = """
            <h1>oauth-pkce-proxy</h1>
            <p>See <a href="https://github.com/danpalmer/oauth-pkce-proxy">https://github.com/danpalmer/oauth-pkce-proxy</a> for more details.</p>
        """
        resp.set_header("Content-Type", "text/html")


class AuthorizeResource:
    async def on_get(self, req, resp):
        code_challenge = req.get_param("code_challenge")
        if not code_challenge:
            raise HTTPBadRequest(title="Missing code_challenge query parameter")

        x_authorize_url = req.get_param("x_authorize_url")
        if not x_authorize_url:
            raise HTTPBadRequest(title="Missing x_authorize_url query parameter")

        original_redirect_uri = req.get_param("redirect_uri")
        if not original_redirect_uri:
            raise HTTPBadRequest(title="Missing redirect_uri query parameter")

        redirect_params = req.params.copy()
        del redirect_params["x_authorize_url"]
        redirect_uri = urllib.parse.urlparse(req.forwarded_uri)
        redirect_uri = redirect_uri._replace(path=req.root_path + "/code")
        redirect_uri = redirect_uri._replace(query="")
        redirect_uri = redirect_params["redirect_uri"] = urllib.parse.urlunparse(
            redirect_uri
        )

        redirect_to = urllib.parse.urlparse(x_authorize_url)
        redirect_to = redirect_to._replace(
            query=urllib.parse.urlencode(redirect_params)
        )

        resp.status = HTTP_302
        resp.append_header("Location", urllib.parse.urlunparse(redirect_to))
        resp.set_cookie("original_redirect_uri", original_redirect_uri, path="/")
        resp.set_cookie("code_challenge", code_challenge, path="/")


class CodeResource:
    async def on_get(self, req, resp):
        code = req.get_param("code")
        if not code:
            raise HTTPBadRequest(title="Missing code query parameter")

        state = req.get_param("state")
        if not state:
            raise HTTPBadRequest(title="Missing state query parameter")

        code_challenges = req.get_cookie_values("code_challenge")
        if not code_challenges or len(set(code_challenges)) > 1:
            raise HTTPBadRequest(title="Missing or ambiguous code_challenge cookie")
        code_challenge = code_challenges[0]

        original_redirect_urls = req.get_cookie_values("original_redirect_uri")
        if not original_redirect_urls or len(set(original_redirect_urls)) > 1:
            raise HTTPBadRequest(
                title="Missing or ambiguous original_redirect_uri cookie"
            )
        original_redirect_url = original_redirect_urls[0]

        await req.storage.set(code, code_challenge)

        redirect_to = urllib.parse.urlparse(original_redirect_url)
        redirect_to_query = urllib.parse.parse_qsl(redirect_to.query)
        redirect_to_query.extend([("code", code), ("state", state)])
        redirect_to = redirect_to._replace(
            query=urllib.parse.urlencode(redirect_to_query)
        )

        resp.status = HTTP_302
        resp.set_header("Location", urllib.parse.urlunparse(redirect_to))
        print(resp.get_header("Location"))


class AccessTokenResource:
    async def on_post(self, req, resp):
        form = await req.get_media()

        if not form:
            raise HTTPBadRequest(
                title="No application/x-www-form-urlencoded body found"
            )

        code_verifier = form.get("code_verifier")
        if not code_verifier:
            raise HTTPBadRequest(title="Missing code_verifier form parameter")

        code = form.get("code")
        if not code:
            raise HTTPBadRequest(title="Missing code form parameter")

        x_client_secret = form.get("x_client_secret")
        if not x_client_secret:
            raise HTTPBadRequest(title="Missing x_client_secret form parameter")

        x_access_token_uri = form.get("x_access_token_uri")
        if not x_access_token_uri:
            raise HTTPBadRequest(title="Missing x_access_token_uri form parameter")

        code_challenge = await req.storage.get(code)
        if not code_challenge:
            raise HTTPBadRequest(
                title="The code_challenge for this code was not found, please try again."
            )

        if pkce.get_code_challenge(code_verifier) != code_challenge:
            raise HTTPBadRequest(
                title="The code_verifier does not match code_challenge for this code"
            )

        redirect_body = form.copy()
        redirect_body["client_secret"] = x_client_secret
        del redirect_body["code_verifier"]
        del redirect_body["x_client_secret"]
        del redirect_body["x_access_token_uri"]
        if "redirect_uri" in redirect_body:
            redirect_uri = urllib.parse.urlparse(req.forwarded_uri)
            redirect_uri = redirect_uri._replace(path=req.root_path + "/code")
            redirect_uri = redirect_uri._replace(query="")
            redirect_body["redirect_uri"] = urllib.parse.urlunparse(redirect_uri)

        response = await req.http_client.post(x_access_token_uri, data=redirect_body)

        if response.status_code == 200:
            await req.storage.delete(code)

        resp.status = response.status_code
        resp.text = response.text


class RefreshResource:
    async def on_post(self, req, resp):
        x_client_secret = req.media.get("x_client_secret")
        if not x_client_secret:
            raise HTTPBadRequest(title="Missing x_client_secret form parameter")

        x_access_token_uri = req.media.get("x_access_token_uri")
        if not x_access_token_uri:
            raise HTTPBadRequest(title="Missing x_access_token_uri form parameter")

        redirect_body = req.media.copy()
        redirect_body["client_secret"] = x_client_secret

        response = await req.http_client.post(x_access_token_uri, data=redirect_body)

        resp.status = response.status_code
        resp.text = response.text


# Storage


class Storage:
    TTL_SECONDS = 60 * 60

    def __init__(self, redis_url):
        self._redis = redis.from_url(redis_url)

    async def process_startup(self, scope, event):
        await self._redis.ping()

    async def process_shutdown(self, scope, event):
        await self._redis.close()

    async def process_request(self, req, resp):
        req.storage = self

    async def set(self, key, value):
        await self._redis.set(key, value, ex=self.TTL_SECONDS)

    async def get(self, key):
        value = await self._redis.get(key)
        return value.decode("utf-8")

    async def delete(self, key):
        await self._redis.delete(key)


class HTTPClient:
    client = None

    def __init__(self):
        self.client = httpx.AsyncClient()

    async def process_startup(self, scope, event):
        await self.client.__aenter__()

    async def process_shutdown(self, scope, event):
        await self.client.__aexit__(None, None, None)

    async def process_request(self, req, resp):
        req.http_client = self.client
