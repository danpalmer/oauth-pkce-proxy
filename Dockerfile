FROM python:3.10-alpine

ARG HOST
ARG PORT

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY oauth_pkce_proxy oauth_pkce_proxy

EXPOSE $PORT
CMD ["sh", "-c", "uvicorn oauth_pkce_proxy.asgi:app --host ${HOST} --port ${PORT}"]
