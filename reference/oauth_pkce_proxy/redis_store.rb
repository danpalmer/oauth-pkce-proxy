require 'redis'

class RedisStore
  def initialize(url)
  	@redis = Redis.new(url: url)
  end

  def get(key)
	  @redis.get(key)
  end

  def set(key, value)
  	@redis.set(key, value)
  end
end
