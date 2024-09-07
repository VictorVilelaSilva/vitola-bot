FROM python:3.12-slim-bookworm

RUN adduser --system --group --no-create-home bot \
    && usermod -aG sudo bot \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        bash \
        curl \
        build-essential \
        ffmpeg

WORKDIR /app
COPY ./src ./src
COPY ./assets ./assets
COPY ./requirements.txt ./requirements.txt
COPY ./entrypoint.sh ./entrypoint.sh

RUN chown -R bot . && chmod u+x ./entrypoint.sh

USER bot

RUN python -m venv venv \
    && . ./venv/bin/activate \
    && pip install -r requirements.txt

SHELL ["/bin/bash", "-c"]
ENTRYPOINT ./entrypoint.sh $0 $@
CMD [ "python", "src/main.py" ]