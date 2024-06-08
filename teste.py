
import google.generativeai as gemini


gemini.configure(api_key="AIzaSyBgFq-5MGshJl1_ntCnDci4KYGfHoCdbRM")


model = gemini.GenerativeModel("gemini-1.5-pro-latest")
chat = model.start_chat(history=[])

prompt =input("Digite algo: ")
while prompt != "fim":
    response = chat.send_message(prompt)
    print(response.text)
    prompt = input("Digite algo: ")