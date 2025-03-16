import streamlit as st
import ollama
from PIL import Image
import base64
from io import BytesIO

# Konfiguracja strony
st.set_page_config(
    page_title="Gemma-3 AI Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Funkcja do konwersji obrazu na base64
def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Funkcja do wysyłania zapytań do modelu
def query_model(messages, model_name="gemma3"):
    try:
        response = ollama.chat(model=model_name, messages=messages)
        return response["message"]["content"]
    except Exception as e:
        return f"Wystąpił błąd: {str(e)}"

# Inicjalizacja stanu sesji
if "text_messages" not in st.session_state:
    st.session_state.text_messages = []
    
if "image_messages" not in st.session_state:
    st.session_state.image_messages = []

# Stylizacja
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e1f5fe;
        border-left: 5px solid #039be5;
    }
    .bot-message {
        background-color: #f0f4c3;
        border-left: 5px solid #afb42b;
    }
    .message-content {
        display: flex;
        flex-direction: column;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e1f5fe;
    }
    
    /* Styl dla kontenera wiadomości tekstowych */
    .text-chat-container {
        display: flex;
        flex-direction: column;
        height: 70vh;
        overflow-y: auto;
        padding: 10px;
        margin-bottom: 20px;
    }
    
    /* Styl dla kontenera inputu tekstowego na dole */
    .text-input-container {
        position: fixed;
        bottom: 20px;
        width: 100%;
        padding: 10px;
        background-color: #f5f5f5;
        z-index: 1000;
    }
    
    /* Centrowanie wiadomości */
    .centered-messages {
        max-width: 800px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# Tytuł aplikacji
st.title("🤖 Gemma-3 AI Assistant")
st.markdown("Asystent AI oparty na modelu Gemma-3 z Ollama")

# Sidebar z informacjami
with st.sidebar:
    st.header("Informacje")
    st.info("Ta aplikacja wykorzystuje model Gemma-3 uruchomiony lokalnie przez Ollama.")
    
    st.header("Ustawienia")
    model_choice = st.selectbox(
        "Wybierz model",
        ["gemma3:1b", "gemma3:4b", "gemma3:12b", "gemma3:27b"],
        index=3
    )
    
    st.header("O aplikacji")
    st.markdown("""
    ### Funkcje:
    - Chat tekstowy
    - Analiza obrazów
    - Lokalne przetwarzanie (prywatność)
    
    ### Wymagania:
    - Zainstalowany Ollama
    - Pobrany model Gemma-3
    """)
    
    if st.button("Wyczyść historię"):
        st.session_state.text_messages = []
        st.session_state.image_messages = []
        st.rerun()

# Zakładki
tab1, tab2 = st.tabs(["💬 Chat tekstowy", "🖼️ Chat z obrazami"])

# Zakładka 1: Chat tekstowy - NOWY UKŁAD
with tab1:
    # Kontener na historię wiadomości
    chat_container = st.container()
    
    # Kontener na input
    input_container = st.container()
    
    # Wyświetl historię wiadomości w kontenerze
    with chat_container:
        st.markdown('<div class="centered-messages">', unsafe_allow_html=True)
        for message in st.session_state.text_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Pole wprowadzania tekstu w kontenerze na dole
    with input_container:
        user_input = st.chat_input("Wpisz wiadomość...")
    
    if user_input:
        # Dodaj wiadomość użytkownika do historii
        st.session_state.text_messages.append({"role": "user", "content": user_input})
        
        # Przygotuj wiadomości dla modelu
        messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.text_messages]
        
        # Uzyskaj odpowiedź od modelu
        response = query_model(messages)
        
        # Dodaj odpowiedź modelu do historii
        st.session_state.text_messages.append({"role": "assistant", "content": response})
        
        # Odśwież stronę, aby pokazać nowe wiadomości
        st.rerun()

# Zakładka 2: Chat z obrazami - POPRZEDNI UKŁAD
with tab2:
    # Wyświetl historię wiadomości
    for message in st.session_state.image_messages:
        with st.chat_message(message["role"]):
            if "images" in message and message["images"] is not None:
                st.image(message["images"][0], caption="Przesłany obraz", width=300)
            st.write(message["content"])
    
    # Pole do przesyłania obrazu
    uploaded_file = st.file_uploader("Choose an image...", type=['png', 'jpg', 'jpeg'])
    
    # Pole wprowadzania tekstu
    image_prompt = st.text_input("Opisz obraz lub zadaj pytanie...")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Przesłany obraz", width=300)
    
    # Przycisk do wysłania
    if st.button("Wyślij zapytanie z obrazem") and image_prompt and uploaded_file is not None:
        # Dodaj wiadomość użytkownika do historii
        st.session_state.image_messages.append({
            "role": "user", 
            "content": str(image_prompt),
            "images": [uploaded_file.getvalue()]
        })
        
        # Wyświetl wiadomość użytkownika
        with st.chat_message("user"):
            st.image(uploaded_file, caption="Przesłany obraz", width=300)
            st.write(image_prompt)
            
        # Przygotuj wiadomości dla modelu multimodalnego
        messages = [{
            "role": "user",
            "content": str(image_prompt),
            "images": [uploaded_file.getvalue()]
        }]
        
        # Pokaż, że model myśli
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.write("Analizuję obraz...")
            
            # Uzyskaj odpowiedź od modelu
            response = query_model(messages)
            
            # Wyświetl odpowiedź
            message_placeholder.write(response)
        
        # Dodaj odpowiedź modelu do historii
        st.session_state.image_messages.append({
            "role": "assistant", 
            "content": response,
            "images": None
        })
