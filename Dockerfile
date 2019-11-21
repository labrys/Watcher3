FROM alpine:3.8

ENV LANG="en_US.utf8" APP_NAME="watcher3" IMG_NAME="watcher3"

RUN apk add --no-cache bash curl git nano vim ca-certificates python3 su-exec

COPY . /opt/$APP_NAME

RUN rm -rf /tmp/* /var/tmp/* /opt/$APP_NAME/entrypoint.sh /opt/$APP_NAME/Docker

WORKDIR /opt/watcher3

COPY Docker/entrypoint.sh /

RUN chmod +x /entrypoint.sh

VOLUME ["/config"]

EXPOSE 9090

ENTRYPOINT ["/entrypoint.sh"]

CMD ["python3 /opt/$APP_NAME/watcher.py --userdata /config"]

