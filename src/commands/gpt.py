
from src.commands.helpers.Gemini import Gemini

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