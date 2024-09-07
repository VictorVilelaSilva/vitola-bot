## Dependencies before using

### Windows

Download and install [FFmpeg](https://ffmpeg.org/download.html).

### Ubuntu

```bash
sudo apt update && sudo apt upgrade -y && sudo apt install ffmpeg -y
```

## Create a virtual environment

```bash
python -m venv venv
```

## Activate the virtual environment

### Windows

```bash
venv\Scripts\activate
```

### Ubuntu

```bash
source venv/bin/activate
```

## Install dependencies after activating virtual environment

```bash
pip install -r requirements.txt
```

## Save installed dependencies

```bash
pip freeze > requirements.txt
```

> Note: This will overwrite the current requirements.txt file


## Build docker image

```bash
docker build -t bot-vitola .
```

## Deploy with minikube and kubectl

```bash
kubectl apply -f deploy/
```