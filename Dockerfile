FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY oauth_pkce_proxy oauth_pkce_proxy

CMD ["uvicorn", "oauth_pkce_proxy.asgi:app"]
