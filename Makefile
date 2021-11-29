ssh_private_key = `cat ~/.ssh/codecov-io_rsa`
sha := $(shell git rev-parse --short=7 HEAD)
release_version = `cat VERSION`
build_date ?= $(shell git show -s --date=iso8601-strict --pretty=format:%cd $$sha)
branch = $(shell git branch | grep \* | cut -f2 -d' ')
epoch := $(shell date +"%s")

build.local:
	docker build -f Dockerfile . -t codecov/api:latest

build.base:
	docker build -f Dockerfile.requirements . -t codecov/baseapi:latest --build-arg SSH_PRIVATE_KEY="${ssh_private_key}"

build:
	$(MAKE) build.base
	$(MAKE) build.local

build.enterprise:
	docker build -f Dockerfile.enterprise . -t codecov/enterprise-api:${release_version} \
		--label "org.label-schema.build-date"="$(build_date)" \
		--label "org.label-schema.name"="Self-Hosted API" \
		--label "org.label-schema.vendor"="Codecov" \
		--label "org.label-schema.version"="${release_version}" \
		--squash
	docker tag codecov/enterprise-api:${release_version} codecov/enterprise-api:latest-stable



build.enterprise-private:
	docker build -f Dockerfile.enterprise . -t codecov/enterprise-private-api:${release_version}-${sha} \
		--label "org.label-schema.build-date"="$(build_date)" \
		--label "org.label-schema.name"="Self-Hosted API Private" \
		--label "org.label-schema.vendor"="Codecov" \
		--label "org.label-schema.version"="${release_version}-${sha}" \
		--label "org.vcs-branch"="$(branch)" \
		--squash

run.enterprise:
	docker-compose -f docker-compose-enterprise.yml up -d

enterprise:
	$(MAKE) build
	$(MAKE) build.enterprise
	$(MAKE) run.enterprise

check-for-migration-conflicts:
	python manage.py check_for_migration_conflicts

push.enterprise-private:
	docker push codecov/enterprise-private-api:${release_version}-${sha}

# we don't want to do this locally anymore. Uncomment if you need it.
# push.enterprise:
# 	docker push codecov/enterprise-api:${release_version}
# 	docker tag codecov/enterprise-api:${release_version} codecov/enterprise-api:latest-stable
# 	docker push codecov/enterprise-api:latest-stable

test:
	python -m pytest --cov=./

test.unit:
	python -m pytest --cov=./ -m "not integration" --cov-report=xml:unit.coverage.xml

test.integration:
	python -m pytest --cov=./ -m "integration" --cov-report=xml:integration.coverage.xml

lint:
	pylint --load-plugins pylint_django --django-settings-module=codecov.settings_dev compare

tag.qa-release:
	git tag -a qa-${release_version}-${sha}-${epoch} -m "Autogenerated tag for enterprise api QA ${version}"
	git push origin qa-${release_version}-${sha}-${epoch}

tag.enterprise-release:
	git tag -a enterprise-${release_version} -m "Autogenerated tag for enterprise api release ${version}"
	git push origin enterprise-${release_version}
