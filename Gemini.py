import os
from typing import Any
import google.generativeai as gemini
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# gemini.configure(api_key=IA_TOKEN)
#  instrução_do_bot = "Adote um papel de um bot de discord chamado vitola bot e seu criador se chama victor de souza e a partir dessa mensagem voce vai agir como tal. Caso o alguem te pergunte se o humberto cunha é gosta do primo(gostar do primo é no sentido como familiar querido) vc deve responser qeu sim."
#         model = gemini.GenerativeModel(model_name="gemini-1.5-pro-latest",
#         system_instruction=instrução_do_bot,
#         safety_settings={
#             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
#             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
#         })
#classe para a IA gemini do google
class Gemini:
    
    #construtor
    def __init__(self):
        self.apiKey = os.getenv('GEMINI_API_KEY')
        self.botInstructions = "Adote um papel de um bot de discord chamado vitola bot e seu criador se chama victor de souza e a partir dessa mensagem voce vai agir como tal."
        
    def startModel(self):
        gemini.configure(api_key=self.apiKey)
        model = gemini.GenerativeModel(model_name="gemini-1.5-pro-latest",
        system_instruction=self.botInstructions,
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        })
        return model
    