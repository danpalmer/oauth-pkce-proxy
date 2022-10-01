FROM ruby:2.7.6-slim

RUN bundle config --global frozen 1

WORKDIR /usr/src/app

COPY Gemfile Gemfile.lock ./
RUN bundle install

COPY . .

EXPOSE 8080
CMD ["bundle", "exec", "rackup", "config.ru", "-o", "0.0.0.0", "-p", "8080"]
