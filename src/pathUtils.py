import os

def get_audio_path(filename: str) -> str:
    """
    Monta o caminho absoluto até o arquivo de áudio na pasta 'assets/audios',
    independente de onde o script é executado.
    """
    # __file__ é o caminho completo deste arquivo Python (por ex.: /opt/app/src/commands/silence_commands.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Monta o caminho absoluto até a pasta 'assets/audios'
    assets_dir = os.path.join(current_dir,"assets", "audios")

    return os.path.join(assets_dir, filename)

def helper(filename: str) -> str:
    return get_audio_path(filename)
