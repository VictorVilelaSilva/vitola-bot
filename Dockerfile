FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        bash \
        curl \
        build-essential \
        ffmpeg

WORKDIR /opt/app
COPY . /opt/app

RUN python -m venv /opt/app/venv \
    && /opt/app/venv/bin/pip install --upgrade pip \
    && /opt/app/venv/bin/pip install --no-cache-dir -r requirements.txt

RUN useradd -ms /bin/bash botuser \
    && chown -R botuser:botuser /opt/app \
    && chmod +x /opt/app/entrypoint.sh

USER botuser

SHELL ["/bin/bash", "-c"]
ENTRYPOINT /opt/app/entrypoint.sh $0 $@
CMD [ "/opt/app/venv/bin/python", "src/main.py" ]