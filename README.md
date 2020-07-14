# docker-hot-loader

Docker compose volume watcher container restarter.

[Based on this approach](https://medium.com/better-programming/live-reloading-with-docker-compose-for-efficient-development-356d50e91e39), but expanded upon to be flexible enough to handle the different use cases I have come across.

## Introduction

The purpose of this project is to provide a docker container that is configured to restart certain other containers when files they depend on change. The target audience are developers who make extensive use of docker to aid in their typical dev workflow.

The flexibility of the configuration should be able to cover a complex ecosystem. This is the reason behind this offering.

This is intended to work in a linux/mac development environment with docker compose. The is not intended for production, so use discretion.

The output of this repository is a docker image that runs a python script which connects a docker client to the host docker service and monitors the mounted volumes of the hot loaded containers for any changes in the filesystem and triggers a container restart.

The use a custom yaml file to capture the mapping of container to specific directories and allowing you to control which containers are restarted.

### Features

- uses docker compose
- flexible container to directory mapping
- watches for changes in the mounted volumes
- restarts containers upon file system changes based on the directory mapping
- uses a unique queue with a configurable delay to allow for multiple file changes within a given window before a restart is triggered

## Configuration

The moving parts are:

- docker compose
- environment variables
- custom yaml file

Hot loader service
: The container that is responsible for watching the filesystem and restarting the correct container.

Hot loaded service
: a container to be restarted when a change on filesystem happens.

### Docker compose

Each intended hot loaded docker container should:

- be labelled with the [configured label](#environment-variables) that indicates to the hot loader container.
- mount the files on the file system the hot loader container is [configured to watch](#mapping-container-to-volumes).

The hot loader container should:

- mount the docker socket to allow the python docker client to connect to the host.
- mount the configured files.

### Mapping container to volumes

A custom yaml file map container names to a sequence of absolute directories to watch.

```yaml
container-name-1:
    - /mounted/source/dir/a
    - /mounted/source/dir/b
    - /mounted/source/dir/c
```

### Environment variables

HOT_LOADER_LABEL
: Sets the label to identify hot loaded containers.

HOT_LOADER_CONFIG
: Sets the location of the hot loader configuration yaml file within the mounted volume.

RELOAD_DELAY
: Sets the time in seconds to wait between container restarts as well as the initital file change event.

## Example


## Possible extensions
