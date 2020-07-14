FROM python:3.8

RUN pip install watchdog docker pyyaml

COPY ./hot-loader.py /hot-loader/

WORKDIR /hot-loader

ENTRYPOINT python hot-loader.py
