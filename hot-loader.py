import logging
import queue
import sys
import threading
import time
from os import environ

import docker
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import yaml


class SetQueue(queue.Queue):
    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()


logger = logging.getLogger("reloader")

client = docker.DockerClient(base_url="unix://var/run/docker.sock")
volumes_to_containers = {}
containers = {}

not_watched = ["/var/run/docker.sock"]
reloader_volumes = []

restart_timeout = 10
label_env = environ["HOT_LOADER_LABEL"]
config_env = environ["HOT_LOADER_CONFIG"]
reload_delay_env = environ["RELOAD_DELAY"]
reload_delay = int(reload_delay_env) if reload_delay_env else 30

restart_queue = SetQueue()


def setup_logger():
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s | [%(levelname)s] | [%(filename)s:%(lineno)d] | %(message)s")
    ch.setFormatter(formatter)
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)


def watch_handler(*args, patterns=["*"], ignore_directories=True, **kwargs):
    event_handler = PatternMatchingEventHandler(
        *args, patterns=patterns, ignore_directories=ignore_directories, **kwargs
    )

    def on_any_event_callback(event):
        logger.info(f"file change event: {event}")
        logger.info(event.src_path)

        containers_to_restart = []
        for target_dir in volumes_to_containers.keys():
            if event.src_path.startswith(target_dir):
                target_container = volumes_to_containers[target_dir]
                containers_to_restart.extend(target_container)
                logger.info(f"target containers {target_container}")

        schedule_restart(set(containers_to_restart))

    event_handler.on_any_event = on_any_event_callback
    return event_handler


def schedule_restart(containers_to_restart):
    for container_name in containers_to_restart:
        logger.info(f"Adding container to reload queue: {container_name}")
        restart_queue.put(container_name)
        logger.info(f"Pushed to queue, size is {restart_queue.qsize()}")


def reloader():
    logger.info("starting queue reloader thread")

    while True:
        try:
            if restart_queue.qsize() > 0:
                time.sleep(reload_delay)
                logger.info(f"Pulling from queue, size is {restart_queue.qsize()}")
                container_name = restart_queue.get(block=False)
                logger.info(f"Reloading container: {container_name}")
                containers[container_name].restart(timeout=restart_timeout)
            else:
                time.sleep(1)
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Something went wrong while reloading: ")
            logger.error(e)


def readConfig():
    with open(config_env, "r") as file:
        config_parsed = yaml.load(file, Loader=yaml.FullLoader)
        return config_parsed


def init():
    logger.info(f"using reload delay: {reload_delay}")
    logger.info(f"using label: {label_env}")
    logger.info(f"using config: {config_env}")

    config_parsed = readConfig()
    logger.info(f"parsed config: {config_parsed}")

    labelled_containers = client.containers.list(filters={"label": label_env, "status": "running"})

    for container in labelled_containers:
        name = container.attrs["Name"]
        containers[name] = container
        logger.info(f"labelled container: {name}")

        stripped_name = name.strip("/")
        target_dirs = config_parsed[stripped_name] if stripped_name in config_parsed else []

        for target in target_dirs:
            if not target:
                continue

            target = target.rstrip("/")

            if target in volumes_to_containers:
                volumes_to_containers[target].append(name)
            else:
                volumes_to_containers[target] = [name]

    logger.info(f"watched directories: {volumes_to_containers.keys()}")
    logger.info(f"containers: {containers}")
    logger.info(f"mapped watched directories to containers: {volumes_to_containers}")


def watch():
    observer = Observer()

    for target_dir in volumes_to_containers.keys():
        logger.info(f"watching {target_dir}")
        observer.schedule(watch_handler(), target_dir, recursive=True)

    observer.start()
    logger.info("started watching")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    restart_queue.join()
    observer.join()


def start():
    setup_logger()
    init()
    threading.Thread(target=reloader).start()
    watch()


if __name__ == "__main__":
    start()
