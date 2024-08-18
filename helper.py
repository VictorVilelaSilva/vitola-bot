import os
from pytubefix import YouTube

def download_video(link):
    try: 
        yt = YouTube(link)
        yt_title = yt.title
        dest_dir = 'audios/'
        ys = yt.streams.get_highest_resolution()
        ys = yt.streams.filter(only_audio=True).first()

        # Começa o download
        arquivo = ys.download(output_path=dest_dir, filename=ys.default_filename)

        #troca o nome do arquivo para mp3
        base, ext = os.path.splitext(arquivo) 
        novo_arquivo = base + '.mp3'
        if os.path.exists(novo_arquivo):
            return novo_arquivo, yt_title
        os.rename(arquivo, novo_arquivo)
        dest_path = os.path.join(dest_dir, os.path.basename(novo_arquivo))

        print(f'\nDownload concluído! {dest_path}')
        return dest_path, yt_title
    except Exception as e:
        print(f'Ocorreu um erro: {e}')
        exit()



