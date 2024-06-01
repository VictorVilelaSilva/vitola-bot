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
