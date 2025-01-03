
import discord
from io import BytesIO
from commands.helpers.Gemini import Gemini

async def gptFunc(ctx, bot, message=" "):
    def check_author(m):
        return m.author == ctx.author

    if bot.IS_EXECUTING_COMMAND:
        await ctx.send("Bot ocupado no momento.")
        return

    bot.IS_EXECUTING_COMMAND = True
    chat = Gemini().startModel().start_chat(history=[])
    prompt = message
    await ctx.send('Sua conversa com o vitola bot vai começar! Digite "fim" para encerrar a conversa.')

    while prompt != "fim":
        response = chat.send_message(prompt)
        await ctx.send(response.text)
        prompt_msg = await bot.client.wait_for("message", check=check_author)
        prompt = prompt_msg.content

    bot.IS_EXECUTING_COMMAND = False
    await ctx.send("Conversa com o vitola bot encerrada!")


async def geminiImageGen(ctx, bot, prompt=" "):
    """
    Gera uma imagem usando google.generativeai (Imagen) e envia no Discord.
    
    :param ctx: Contexto do Discord (usado para enviar mensagens)
    :param bot: Instância do seu bot
    :param prompt: Texto que descreve a imagem
    """
    # Configure a API (pode ser feito uma vez só, em outro lugar)
    imagen_model = Gemini().startImagemModel()

    # Se não passaram prompt no comando, talvez extrair do ctx.message.content
    if not prompt.strip() or prompt.strip() == " ":
        user_input = ctx.message.content.split(" ", 1)
        if len(user_input) > 1:
            prompt = user_input[1]
        else:
            prompt = "Retrato de um gato usando chapéu..."

    try:
        # Gera a imagem (vamos pedir só 1, mas você pode mudar para 4, etc.)
        result = imagen_model.generate_images(
            prompt=prompt,
            number_of_images=1,            # quantas imagens gerar
            safety_filter_level="block_only_high",
            person_generation="allow_adult",
            aspect_ratio="3:4",
        )

        # Se não retornou nenhuma imagem, avise no Discord
        if not result.images:
            await ctx.send("Não foi possível gerar a imagem ou não retornou nenhuma.")
            return

        # Pegamos a primeira imagem (ou você pode iterar)
        image_obj = result.images[0] 

        # O objeto "image_obj._pil_image" é um PIL Image, segundo o exemplo oficial
        pil_image = image_obj._pil_image

        # Convertendo o PIL Image em bytes para enviar ao Discord
        img_bytes = BytesIO()
        pil_image.save(img_bytes, format="PNG")  # ou "JPEG"
        img_bytes.seek(0)

        # Enviando no Discord
        file_discord = discord.File(img_bytes, filename="generated_image.png")
        await ctx.send(file=file_discord, content=f"Prompt: `{prompt}`")

    except Exception as e:
        await ctx.send(f"Ocorreu um erro ao gerar a imagem: {e}")

    