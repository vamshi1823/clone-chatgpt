import json

import requests
import streamlit as st

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Vamshi's Chatbot — Ollama + Groq",
    page_icon="🤖",
    layout="centered"
)

# -----------------------------
# Custom CSS
# -----------------------------
st.markdown("""
<style>
.block-container { max-width: 850px; padding-top: 2rem; }
.hero-card {
    background: linear-gradient(135deg, #111827, #020617);
    border: 1px solid rgba(34,197,94,0.40);
    border-radius: 24px;
    padding: 26px;
    margin-bottom: 20px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.20);
}
.brand-title { font-size: 34px; font-weight: 800; color: #f8fafc; margin-bottom: 6px; }
.brand-subtitle { font-size: 16px; color: #d1d5db; }
.green { color: #22c55e; }
.small-note { color: #9ca3af; font-size: 13px; margin-top: 8px; }
.stButton button {
    border-radius: 12px;
    background-color: #22c55e;
    color: #052e16;
    font-weight: 700;
    border: none;
}
.stButton button:hover { background-color: #16a34a; color: #052e16; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="hero-card">
    <div class="brand-title">🤖 <span class="green">AI Chatbot</span></div>
    <div class="brand-subtitle">Streaming chatbot powered by open-source LLMs — run locally via Ollama or in the cloud via Groq.</div>
    <div class="small-note">Features: Chat Memory · Streaming · Temperature Control · Local + Cloud LLM modes</div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# URLs
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/chat"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# -----------------------------
# Helper: Check if Ollama is running locally
# -----------------------------
def check_ollama_running():
    try:
        response = requests.get("http://localhost:11434", timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

# -----------------------------
# Helper: Get Groq API key safely
# -----------------------------
def get_groq_key():
    # First try Streamlit secrets (used on Streamlit Cloud)
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    # Then try sidebar input (used locally)
    return st.session_state.get("groq_key_input", "")

# -----------------------------
# Sidebar Settings
# -----------------------------
with st.sidebar:
    st.title("⚙️ Settings")

    # --- Mode Toggle ---
    mode = st.radio(
        "LLM Mode",
        ["☁️ Groq Cloud (Public)", "💻 Local Ollama"],
        index=0,
        help="Use Groq for the live public demo. Use Local Ollama if running on your own machine."
    )

    st.markdown("---")

    # --- Model Selection based on mode ---
    if mode == "☁️ Groq Cloud (Public)":
        model = st.selectbox(
            "Choose Groq Model",
            [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ],
            index=0
        )
        # Only show API key input if not already in secrets
        if not get_groq_key():
            groq_key_input = st.text_input(
                "Groq API Key",
                type="password",
                placeholder="Paste your Groq API key here",
                help="Get a free key at console.groq.com"
            )
            st.session_state["groq_key_input"] = groq_key_input
        else:
            st.success("✅ Groq API key loaded")

    else:
        model = st.selectbox(
            "Choose Ollama Model",
            ["llama3.2", "llama3.1", "llama3", "mistral", "gemma2", "qwen2.5", "qwen2.5:3b"],
            index=0
        )

    st.markdown("---")

    temperature = st.slider(
        "Temperature / Creativity",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="0 = focused/factual  |  1 = creative/random"
    )

    system_prompt = st.text_area(
        "System Prompt",
        value="You are a helpful AI assistant. Explain concepts clearly and simply. When useful, respond with examples.",
        height=120
    )

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📚 How it works")
    st.markdown("- **Groq**: Free cloud API, runs LLMs fast")
    st.markdown("- **Ollama**: Runs LLM locally on your laptop")
    st.markdown("- **Streaming**: Response prints word by word")
    st.markdown("- **Memory**: Full chat history sent each time")
    st.markdown("- **Temperature**: Controls creativity level")

# -----------------------------
# Session State / Memory
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# Show Chat History
# -----------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -----------------------------
# Chat Input
# -----------------------------
user_prompt = st.chat_input("Ask me anything...")

if user_prompt:
    # 1. Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Build message history to send
    messages_to_send = [{"role": "system", "content": system_prompt}]
    messages_to_send.extend(st.session_state.messages)

    # 3. Stream response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # ---- GROQ MODE ----
        if mode == "☁️ Groq Cloud (Public)":
            groq_key = get_groq_key()

            if not groq_key:
                response_placeholder.error("❌ No Groq API key found. Please enter your key in the sidebar.")
            else:
                try:
                    headers = {
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model,
                        "messages": messages_to_send,
                        "temperature": temperature,
                        "stream": True
                    }

                    with requests.post(GROQ_API_URL, headers=headers, json=payload, stream=True, timeout=60) as resp:
                        resp.raise_for_status()

                        for line in resp.iter_lines():
                            if line:
                                decoded = line.decode("utf-8")
                                if decoded.startswith("data: "):
                                    decoded = decoded[6:]  # strip "data: " prefix
                                if decoded.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(decoded)
                                    delta = chunk["choices"][0]["delta"].get("content", "")
                                    full_response += delta
                                    response_placeholder.markdown(full_response + "▌")
                                except (json.JSONDecodeError, KeyError):
                                    continue

                    response_placeholder.markdown(full_response)

                except requests.exceptions.HTTPError as e:
                    full_response = f"❌ Groq API Error: {str(e)}\n\nCheck that your API key is valid."
                    response_placeholder.error(full_response)
                except Exception as e:
                    full_response = f"❌ Error: {str(e)}"
                    response_placeholder.error(full_response)

        # ---- OLLAMA LOCAL MODE ----
        else:
            if not check_ollama_running():
                full_response = "❌ Ollama is not running. Open a terminal and run: `ollama serve`"
                response_placeholder.error(full_response)
            else:
                try:
                    payload = {
                        "model": model,
                        "messages": messages_to_send,
                        "stream": True,
                        "options": {"temperature": temperature}
                    }

                    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120) as resp:
                        resp.raise_for_status()

                        for line in resp.iter_lines():
                            if line:
                                chunk = json.loads(line.decode("utf-8"))
                                if "message" in chunk and "content" in chunk["message"]:
                                    full_response += chunk["message"]["content"]
                                    response_placeholder.markdown(full_response + "▌")
                                if chunk.get("done", False):
                                    break

                    response_placeholder.markdown(full_response)

                except requests.exceptions.HTTPError as e:
                    full_response = (
                        f"❌ HTTP Error: {str(e)}\n\n"
                        f"Model `{model}` may not be downloaded.\n\n"
                        f"Run in terminal: `ollama pull {model}`"
                    )
                    response_placeholder.error(full_response)
                except Exception as e:
                    full_response = f"❌ Error: {str(e)}"
                    response_placeholder.error(full_response)

    # 4. Save assistant response to memory
    st.session_state.messages.append({"role": "assistant", "content": full_response})
