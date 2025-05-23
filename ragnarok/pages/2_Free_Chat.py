import streamlit as st
# from transformers import AutoModelForSequenceClassification, AutoTokenizer
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from streamlit_cookies_manager import CookieManager
import time
import torch
import asyncio
from ollama import AsyncClient


cookies = CookieManager()
while not cookies.ready():
    time.sleep(1)

if "mode" not in cookies:
    st.error("Your cookies are broken, please go back to the main settings page.")
    st.stop()

if "mode_index" not in st.session_state:
    st.session_state["mode_index"] = 0  # Default to the first mode

def get_mode_index(cookies):
    if "mode" in cookies:
        if cookies["mode"] == "Local LLM":
            return 0
        elif cookies["mode"] == "Remote Ollama Server (Local Reranker)":
            return 1
        elif cookies["mode"] == "Remote Ollama Server (No Reranker)":
            return 2
    return 0  # Default to 0 if no mode is set

@st.cache_resource
def get_ollama_client(ollama_url):
    client = AsyncClient(ollama_url)
    return client

mode_index = get_mode_index(cookies)

if mode_index == 0:
    if "llm_model" not in cookies and "ollama_model" not in cookies:
        st.error("Please select a LLM model on the main settings page.")
        st.stop()
    if "llm_temperature" not in cookies:
        st.error("Please select a LLM model temperature on the main settings page.")
        st.stop()

if mode_index == 1 or mode_index == 2:
    if "ollama_url" not in cookies:
        st.error("Please select an Ollama server on the main settings page.")
        st.stop()
    if "ollama_model" not in cookies:
        st.error("Please select an Ollama model on the main settings page.")
        st.stop()

if mode_index == 1 or mode_index == 2:
    if "ollama_url" not in cookies:
        st.error("Please select an Ollama server on the main settings page.")
        st.stop()
    if "ollama_model" not in cookies:
        st.error("Please select an Ollama model on the main settings page.")
        st.stop()
    if cookies["ollama_model"] == "":
        st.error("Please select an Ollama model on the main settings page.")
        st.stop()


if mode_index == 0:
    llm_generation_kwargs = {
        "max_tokens": 512,
        "stream": True, 
        "temperature": float(cookies["llm_temperature"]),
        "echo": False
    }
if mode_index == 0 or mode_index == 1:
    # check for GPU presence
    if torch.cuda.is_available():
        # traditional Nvidia cuda GPUs
        device = torch.device("cuda:0")
        n_gpu_layers = int(cookies["n_gpu_layers"])
    elif torch.backends.mps.is_available():
        # for macOS M1/M2s
        device = torch.device("mps")
        n_gpu_layers = int(cookies["n_gpu_layers"])
    else:
        device = torch.device("cpu")
        n_gpu_layers = 0

@st.cache_resource
def get_llm(llm_model_path, n_gpu_layers):
    llm = Llama(
        model_path=llm_model_path,
        n_ctx=8192,
        n_gpu_layers=n_gpu_layers,
        verbose=False
    )
    return llm
if mode_index == 0:
    try:
        if cookies["llm_model"] == "Intel/neural-chat-7b-v3-3":
            llm_model_path = hf_hub_download("TheBloke/neural-chat-7B-v3-3-GGUF", filename="neural-chat-7b-v3-3.Q5_K_M.gguf", local_files_only=True)
        elif cookies["llm_model"] == "openchat-3.5-0106":
            llm_model_path = hf_hub_download("TheBloke/openchat-3.5-0106-GGUF", filename="openchat-3.5-0106.Q5_K_M.gguf", local_files_only=True)
        elif cookies["llm_model"] == "Starling-LM-7B-alpha":
            llm_model_path = hf_hub_download("TheBloke/Starling-LM-7B-alpha-GGUF", filename="starling-lm-7b-alpha.Q5_K_M.gguf", local_files_only=True)
        else:
            llm_model = cookies["llm_model"]
            st.error(f"Invalid llm_model: {llm_model}")
    except:
        with st.spinner("Downloading LLM model (this will take some time)..."):
            if cookies["llm_model"] == "Intel/neural-chat-7b-v3-3":
                llm_model_path = hf_hub_download("TheBloke/neural-chat-7B-v3-3-GGUF", filename="neural-chat-7b-v3-3.Q5_K_M.gguf")
            elif cookies["llm_model"] == "openchat-3.5-0106":
                llm_model_path = hf_hub_download("TheBloke/openchat-3.5-0106-GGUF", filename="openchat-3.5-0106.Q5_K_M.gguf")
            elif cookies["llm_model"] == "Starling-LM-7B-alpha":
                llm_model_path = hf_hub_download("TheBloke/Starling-LM-7B-alpha-GGUF", filename="starling-lm-7b-alpha.Q5_K_M.gguf")
            else:
                llm_model = cookies["llm_model"]
                st.error(f"Invalid llm_model_path: {llm_model}")

    llm = get_llm(llm_model_path, n_gpu_layers)

st.title("Free Chat With Selected Model")
st.warning('*WARNING: results not guaranteed to be correct!*', icon="⚠️")

if "freeform_messages" not in st.session_state:
    st.session_state.freeform_messages = []

for message in st.session_state.freeform_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("<enter a question>"):
    st.session_state.freeform_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        if "neural-chat" in cookies["llm_model"]:
            single_turn_prompt = f"### System:\nYou are a helpful assistant chatbot.\n### User:\n{prompt}\n### Assistant:\n"
        else:
            single_turn_prompt = f"GPT4 Correct User: {prompt}<|end_of_turn|>GPT4 Correct Assistant:"

        with st.spinner("LLM is processing the prompt..."):
            start = time.time()
            if mode_index == 0:
                stream = llm.create_completion(single_turn_prompt, **llm_generation_kwargs)
                for output in stream:
                    full_response += (output['choices'][0]['text'] or "").split("### Assistant:\n")[-1]
                    message_placeholder.markdown(full_response + "▌")
            elif mode_index == 1 or mode_index == 2:
                client = get_ollama_client(cookies["ollama_url"])
                async def chat():
                    full_response = ""
                    # TODO: remove hardcoded model
                    message = {'role': 'user', 'content': single_turn_prompt}
                    async for part in await AsyncClient().chat(model='dolphin3:8b', messages=[message], stream=True):
                        print(part['message']['content'], end='', flush=True)
                        full_response += part['message']['content']
                        message_placeholder.markdown(full_response + "▌")
                    return full_response
                
                full_response = asyncio.run(chat())


            end = time.time()
            print(f"LLM generation completed in {(end - start):.2f} seconds")

    st.session_state.freeform_messages.append({"role": "assistant", "content": f"{full_response}"})
