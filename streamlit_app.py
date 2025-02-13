import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF per estrarre testo dal PDF
import pandas as pd  # Per leggere file Excel
import os
import tempfile
import sys

# Controllo autenticazione
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Accesso a Legis Pro")
    password = st.text_input("Inserisci la password per accedere:", type="password")
    
    if st.button("Accedi"):
        if password == st.secrets["pw"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Password errata. Riprova.")
    
    st.stop()  # Ferma l'esecuzione del resto del codice finché non autenticati

# Imposta la lingua italiana per tutta l'app
def set_italian_locale():
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
    except:
        pass
set_italian_locale()

# Titolo e icona
st.set_page_config(
    page_title="Legis Pro",
    page_icon="🤖",  # Emoji, URL, o percorso di un'immagine
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configura il client OpenAI con l'API Key
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Tone di default
DEFAULT_TONE = "Rispondi in modo sintetico, chiaro e professionale."

# Configura lo stato della sessione
if "chats" not in st.session_state:
    st.session_state.chats = []  # Lista per memorizzare le chat
if "selected_chat" not in st.session_state:
    st.session_state.selected_chat = None  # Chat selezionata
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""  # Testo estratto dal PDF
if "tone_of_voice" not in st.session_state:
    st.session_state.tone_of_voice = "Rispondi in modo sintetico, chiaro e professionale."  # Prompt predefinito
if "show_tone_settings" not in st.session_state:
    st.session_state.show_tone_settings = False  # Controllo per mostrare il box di impostazione del tone of voice
if "tone_of_voice" not in st.session_state:
    # Imposta il valore predefinito come costante separata
    st.session_state.tone_of_voice = DEFAULT_TONE
if "messages" not in st.session_state:
    st.session_state.messages = []  # Memorizza la chat corrente

# Mostra il logo dell'app
st.image("media/LegisPro.png", width=350)

# Funzione per estrarre testo dal PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

# Carica un documento (PDF o Excel) dalla sidebar
uploaded_file = st.sidebar.file_uploader("📄 Carica il documento da memorizzare", type=["pdf", "xlsx", "xls"])
if uploaded_file:
    file_ext = uploaded_file.name.split('.')[-1].lower()
    if file_ext == "pdf":
        # Salva il file temporaneamente e ne estrae il testo
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_pdf_path = temp_file.name
        st.session_state.pdf_text = extract_text_from_pdf(temp_pdf_path)
        st.sidebar.success("PDF caricato e analizzato con successo!")
    elif file_ext in ["xlsx", "xls"]:
        # Usa Pandas per leggere il file Excel e convertirlo in una stringa
        df = pd.read_excel(uploaded_file)
        # Pulizia avanzata del DataFrame
        cleaned_data = (
            df.fillna('')  # Sostituisce i NaN con stringhe vuote
            .applymap(lambda x: str(x).strip() if pd.notnull(x) else '')  # Rimuove spazi extra e converte a stringa
            .replace(r'^\s*$', '', regex=True)  # Sostituisce celle vuote/whitespace con stringa vuota
        )
        # Generazione testo compatto
        excel_text = "\n".join(
            "|".join(row) 
            for row in cleaned_data.astype(str).values
            if any(field.strip() for field in row)
        )
        st.session_state.pdf_text = excel_text
        st.sidebar.success("Excel caricato e analizzato con successo!")    

#st.warning(sys.getsizeof(st.session_state.pdf_text), icon="⚠️")

# Visualizza le chat esistenti nella sidebar
st.sidebar.title("Gestione conversazioni")
if st.sidebar.button("➕ Nuova Conversazione"):
    chat_id = f"Conversazione {len(st.session_state.chats) + 1}"
    st.session_state.chats.append({"id": chat_id, "messages": []})
    st.session_state.selected_chat = chat_id

for chat in st.session_state.chats:
    if st.sidebar.button(chat["id"]):
        st.session_state.selected_chat = chat["id"]

# Pulsante per mostrare/nascondere le impostazioni del tone of voice
if st.sidebar.button("⚙️ Imposta Tone of Voice"):
    st.session_state.show_tone_settings = not st.session_state.show_tone_settings

# Modifica nella sezione delle impostazioni del tone of voice
if st.session_state.show_tone_settings:
    # Usa value per mantenere esplicitamente lo stato corrente
    new_tone = st.sidebar.text_area(
        "Modifica il tone of voice:",
        value=st.session_state.tone_of_voice,
        key="tone_input",
        help="Il tone of voice verrà applicato a tutte le nuove risposte"
    )
    # Pulsanti per gestire il reset
    col1, col2 = st.sidebar.columns(2)
    if col1.button("💾 Salva modifiche"):
        st.session_state.tone_of_voice = new_tone
    if col2.button("↩️ Ripristina default"):
        st.session_state.tone_of_voice = DEFAULT_TONE

# Visualizza la chat
st.title("🤖 Chiedi a Legis Pro")
if not st.session_state.selected_chat:
    st.write("Seleziona una conversazione o creane una nuova dalla barra laterale.")
else:
    chat_data = next(c for c in st.session_state.chats if c["id"] == st.session_state.selected_chat)
    
    # Visualizza i messaggi esistenti
    for message in chat_data["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input per l'utente
    if user_input := st.chat_input("Fai una domanda sul tuo PDF"):
        # Aggiungi e visualizza il messaggio dell'utente
        chat_data["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Prepara i messaggi per la chiamata all'API
        messages_for_api = []
        # Se è stato caricato un PDF, includi il suo contenuto come contesto
        if st.session_state.pdf_text:
            messages_for_api.append({
                "role": "system",
                "content": f"Utilizza il seguente testo del PDF come contesto per rispondere alle domande:\n\n{st.session_state.pdf_text}\n\n"
            })
        # Aggiungi il tone of voice come indicazione per lo stile delle risposte
        if st.session_state.tone_of_voice:
            messages_for_api.append({
                "role": "system",
                #"content": f"Mantieni questo tone of voice nelle risposte: {st.session_state.tone_of_voice}\n\n"
                "content": f"ISTRUZIONE PRIORITARIA: {st.session_state.tone_of_voice}"
            })
        # Aggiungi i messaggi della conversazione
        messages_for_api.extend([{"role": m["role"], "content": m["content"]} for m in chat_data["messages"]])
        
        # Genera la risposta in streaming
        #st.warning(messages_for_api, icon="⚠️")
        with st.chat_message("assistant"):
            response = st.write_stream(
                client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_for_api,
                    stream=True,
                )
            )
        # Aggiungi la risposta generata alla conversazione
        chat_data["messages"].append({"role": "assistant", "content": response})