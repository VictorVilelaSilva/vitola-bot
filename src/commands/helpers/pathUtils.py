import os

def get_audio_path(filename: str) -> str:
    """
    Monta o caminho absoluto até o arquivo de áudio em 'src/assets/audios',
    independente de onde o script é executado.
    """
    # __file__ é o caminho completo deste arquivo Python (por ex.: /opt/app/src/commands/silence_commands.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # sobe 3 níveis até chegar em 'src'
    project_src = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Monta o caminho absoluto até a pasta 'assets/audios'
    assets_dir = os.path.join(project_src, "assets", "audios")

    return os.path.join(assets_dir, filename)

