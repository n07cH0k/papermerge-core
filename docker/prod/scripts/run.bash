#!/bin/bash

export PATH="/venv/bin:${PATH}"

CMD="$1"
PYTHON="/venv/bin/python"
MANAGE="${PYTHON} manage.py"


if [ -z $CMD ]; then
  echo "No command specified"
  exit 1
fi

exec_server() {
  exec uwsgi --ini /etc/uwsgi/papermerge.ini
}

exec_ws_server() {
  exec daphne -b 0.0.0.0 --port 8000 config.asgi:application
}

exec_collectstatic() {
  $MANAGE collectstatic --noinput
}

exec_migrate() {
  # run migrations
  $MANAGE migrate --no-input
}

exec_createsuperuser() {
  # user envrironment variables:
  #   (1) DJANGO_SUPERUSER_USERNAME
  #   (2) DJANGO_SUPERUSER_EMAIL
  #   (3) DJANGO_SUPERUSER_PASSWORD
  # to create superuser if (1) and (2) are set
  if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL}" ]; then
    echo "Creating superuser username=${DJANGO_SUPERUSER_USERNAME}"
    $MANAGE createsuperuser --noinput \
      --username ${DJANGO_SUPERUSER_USERNAME} \
      --email ${DJANGO_SUPERUSER_EMAIL} || true
  fi
}

exec_worker() {
  exec celery --app config worker \
   -n "worker-node-${HOSTNAME}@papermerge" ${PAPERMERGE_WORKER_ARGS}
}

exec_init() {
  exec_collectstatic
  exec_migrate
  exec_createsuperuser
}

case $CMD in
  init)
    exec_init
    ;;
  migrate)
    exec_migrate
    ;;
  collectstatic)
    exec_collectstatic
    ;;
  createsuperuser)
    exec_createsuperuser
    ;;
  server)
    # starts REST API webserver
    exec_init
    exec_server
    ;;
  ws_server)
    # start websockets server
    exec_init
    exec_ws_server
    ;;
  worker)
    # starts worker
    exec_init
    exec_worker
    ;;
  *)
    echo "Unkown command: '$CMD'. Exiting..."
    exit 1
    ;;
esac