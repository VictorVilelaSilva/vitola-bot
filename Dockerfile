FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        bash \
        curl \
        build-essential \
        ffmpeg

WORKDIR /opt/app
COPY . /opt/app

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN useradd -ms /bin/bash botuser \
    && chown -R botuser:botuser /opt/app

USER botuser

SHELL ["/bin/bash", "-c"]
CMD [ "python", "src/main.py" ]