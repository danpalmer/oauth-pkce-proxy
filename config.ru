require 'rubygems'
require 'bundler'

Bundler.require

require 'dotenv/load'

require_relative 'oauth_pkce_proxy/app'
require_relative 'oauth_pkce_proxy/redis'

provider = OauthPkceProxy::Provider.new(
  client_secret: ENV['OAUTH_CLIENT_SECRET'],
  authorize_url: ENV['OAUTH_AUTHORIZE_URL'],
  access_token_url: ENV['OAUTH_ACCESS_TOKEN_URL'],
)

redis = RedisStore.new(url: ENV['REDIS_URL'])

run OauthPkceProxy::App.new(provider: provider, challenge_store: redis)
