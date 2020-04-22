Codecov API
-----------

A private Django REST Framework API intended to serve codecov's front end. 

## Getting Started

### Building

This project contains a makefile. To build the docker image:

    make build

`requirements.txt` is used in the base image. If you make changes to `requirements.txt` you will need to rebuild.

### Running Standalone

This project contains a `docker-compose.yml` file that is intended to run the api standalone. In this configuration it **does not** share codecov.io's development database; so don't expect parity there. 

To start the service, do

`docker-compose up`

Utilizing its own database provides a convenient way for the REST API to provide its own helpful seeds and migrations for active development without potentially destroying/modifying your development database for codecov.io.

Once running, the api will be available at `http://localhost:5100`

### Running with codecov.io

This service will startup when you run codecov.io normally. It is under that `api` block of codecov.io's `docker-compose.yml` file. 

### Testing

The easiest way to run tests (that doesn't require installing postgres and other dependencies) is to run inside of docker:

    docker-compose up
    docker exec -it codecov-api_api_1 pytest -rf

If you want to run the test locally, you can also just run `pytest` locally, but you'll have to install the requirements.txt and change the DATABASE host to point to something local in the `codecov/settings.py`.

### Secret and Credential Management

This project should store no secrets or credentials in its source. If you need to add to / modify / setup secrets for this project, contact Eli and he'll get you started. 
