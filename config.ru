require 'rubygems'
require 'bundler'

Bundler.require

require 'dotenv/load'

require_relative 'oauth_pkce_proxy/app'
require_relative 'oauth_pkce_proxy/redis_store'

provider = OauthPkceProxy::Provider.new(
  client_secret: ENV['OAUTH_CLIENT_SECRET'],
  authorize_url: ENV['OAUTH_AUTHORIZE_URL'],
  access_token_url: ENV['OAUTH_ACCESS_TOKEN_URL'],
)

redis = RedisStore.new(ENV['REDIS_URL'])

set :port, ENV['PORT']
set :bind, '0.0.0.0'
run OauthPkceProxy::App.new(provider: provider, challenge_store: redis)
