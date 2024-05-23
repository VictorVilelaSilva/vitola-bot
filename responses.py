def handle_response(message)->str:
    p_message = message.lower()
    print("Mensagem recebida:")
    print(message.lower())

    if p_message == "oi":
        return "Do neida?"
    
    if p_message == "dota ou lol?":
        return "Dota é melhor"
    
    