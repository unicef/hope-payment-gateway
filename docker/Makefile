TARGET?=0.1.0
DATABASE_URL?=
DOCKER_PASS?=
DOCKER_USER?=
BASE?=$(shell echo "${TARGET}" | sed "s/\([0-9]\)\.\([0-9]\)\.\(.*\)/\1.\2/g" )
# below vars are used internally
BUILD_OPTIONS?=
CMD?=hope_payment_gateway
CONTAINER_NAME?=hope_payment_gateway-${TARGET}
ORGANIZATION=unicef
IMAGE_NAME=hope-payment-gateway
DOCKER_IMAGE_NAME?=${ORGANIZATION}/${IMAGE_NAME}
DOCKER_IMAGE?=${DOCKER_IMAGE_NAME}:${TARGET}
DOCKERFILE?=Dockerfile
RUN_OPTIONS?=
PORTS=
ABSOLUTE_BASE_URL?="http://192.168.66.66:8000"

help:
	@echo "dev                  build dev image (based on local code)"
	@echo "build                build production image (based on tag ${TARGET})"
	@echo "release              release tag ${TARGET} on docker hub"
	@echo "run                  run ${DOCKER_IMAGE} locally"


info:
	@echo 'docker images'
	@docker images | grep ${IMAGE_NAME}
	@echo '------------------'
	@echo 'docker containers'
	@docker ps -a | grep ${IMAGE_NAME}


build-base:
	cd .. && docker build \
			${BUILD_OPTIONS} \
			--no-cache \
			-t ${DOCKER_IMAGE_NAME}:${BASE}-base \
			-f docker/Dockerfile.base .
	@echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
	docker push ${DOCKER_IMAGE_NAME}:${BASE}-base


.build:
	cd .. && ./manage.py makemigrations --check --dry-run
	cd .. && docker build \
			${BUILD_OPTIONS} \
			--build-arg BASE_IMAGE=${BASE} \
			--build-arg VERSION=${TARGET} \
			-t ${DOCKER_IMAGE} \
			-f docker/Dockerfile .
	docker tag ${DOCKER_IMAGE_NAME}:${TARGET} ${DOCKER_IMAGE_NAME}:dev
	docker images | grep ${DOCKER_IMAGE_NAME}

build-test:
	TARGET=dev $(MAKE) .build test

build:
	$(MAKE) .build test

.run:
	cd .. && docker run \
	 		--rm \
			-e ABSOLUTE_BASE_URL=${ABSOLUTE_BASE_URL} \
			-e CACHE_URL=redis://192.168.66.66:6379/1 \
			-e CACHE_URL_API=redis://192.168.66.66:6379/2 \
			-e CACHE_URL_LOCK=redis://192.168.66.66:6379/3 \
			-e CACHE_URL_TEMPLATE=redis://192.168.66.66:6379/4 \
			-e CELERY_BROKER_URL=redis://192.168.66.66:6379/2 \
			-e CELERY_RESULT_BACKEND=redis://192.168.66.66:6379/3 \
			-e CSRF_COOKIE_SECURE=false \
			-e DATABASE_URL=${DATABASE_URL} \
			-e DEBUG=false \
			-e DJANGO_SETTINGS_MODULE=hope_payment_gateway.config.settings \
			-e SECURE_BROWSER_XSS_FILTER=0 \
			-e SECURE_CONTENT_TYPE_NOSNIFF=0 \
			-e SECURE_FRAME_DENY=0 \
			-e SECURE_HSTS_SECONDS=0 \
			-e SECURE_HSTS_PRELOAD=false \
			-e SECURE_SSL_REDIRECT=false \
			-e SESSION_COOKIE_HTTPONLY=false \
			-e SESSION_COOKIE_SECURE=false \
			-e STATIC_ROOT=/var/hope_payment_gateway/static/ \
			-e DEVELOPMENT_MODE=0 \
			-e X_FRAME_OPTIONS="SAMEORIGIN" \
			-e AZURE_CLIENT_ID=${AZURE_CLIENT_ID} \
			-e AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET} \
			-e AZURE_TENANT=${AZURE_TENANT} \
			-e INSIGHT_URL=${INSIGHT_URL} \
			-e SHAREPOINT_USERNAME=${SHAREPOINT_USERNAME} \
			-e SHAREPOINT_PASSWORD=${SHAREPOINT_PASSWORD} \
			${RUN_OPTIONS} \
			${DOCKER_IMAGE} \
			${CMD}

local:
	RUN_OPTIONS="-v ${PWD}/..:/code -e PYTHONPATH=/code -it" \
	CMD="/bin/bash" \
	$(MAKE) .run

release:
	@echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
	docker tag ${DOCKER_IMAGE_NAME}:${TARGET} ${DOCKER_IMAGE_NAME}:local
	docker push ${DOCKER_IMAGE_NAME}:${TARGET}
	docker push ${DOCKER_IMAGE_NAME}:local

bump:
	cd .. && bumpversion --commit --tag --config-file=.bumpversion.cfg num

run:
	RUN_OPTIONS="-p 8000:8000" \
		ABSOLUTE_BASE_URL=${ABSOLUTE_BASE_URL} \
		$(MAKE) .run

stack:
	RUN_OPTIONS="-p 8000:8000" \
		CMD=stack \
		ABSOLUTE_BASE_URL=${ABSOLUTE_BASE_URL} \
		$(MAKE) .run

workers:
	CONTAINER_NAME=hope_payment_gateway-workers \
			ABSOLUTE_BASE_URL=${ABSOLUTE_BASE_URL} \
			CMD=w2 $(MAKE) .run

beat:
	CONTAINER_NAME=hope_payment_gateway-beat \
		ABSOLUTE_BASE_URL=${ABSOLUTE_BASE_URL} \
		CMD=beat $(MAKE) .run


test:
	RUN_OPTIONS="-e DEBUG=0 \
				 -e X_FRAME_OPTIONS=DENY \
				 -e SESSION_COOKIE_SECURE=1 \
				 -e CSRF_COOKIE_SECURE=1 \
				 -e SECURE_HSTS_PRELOAD=1 \
				 -e SECURE_SSL_REDIRECT=1" \
	CMD='bash -c "touch /var/hope_payment_gateway/.touch && django-admin check --deploy "' \
	$(MAKE) .run

scratch:
	RUN_OPTIONS=-it CMD='/bin/bash' $(MAKE) .run

shell:
	RUN_OPTIONS="-p 8000:8000 -it" \
		ABSOLUTE_BASE_URL=${ABSOLUTE_BASE_URL} \
	CMD='/bin/bash' \
		$(MAKE) .run
#	docker exec -it ${CONTAINER_NAME} /bin/bash
#	RUN_OPTIONS=-it CMD='/bin/bash' $(MAKE) .run

docker-remove:
	docker-remove.sh ${IMAGE_NAME} -o ${ORGANIZATION}
