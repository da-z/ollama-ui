import time

import ollama
import streamlit as st

title = "Ollama Chat"
ver = "0.1.0"

model_refs = {model["name"] for model in ollama.list()["models"]}

st.set_page_config(
    page_title=title,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title(title)

assistant_greeting = "How may I help you?"

model_ref = st.sidebar.selectbox("model", model_refs,
                                 help="See https://ollama.ai/library for more models. "
                                      "Use ollama pull <model> and refresh this app")

system_prompt = st.sidebar.text_area("system prompt", "You are a helpful AI assistant trained on a vast amount of "
                                                      "human knowledge. Answer as concisely as possible.")

context_length = st.sidebar.number_input('context length', value=400, min_value=100, step=100, max_value=32000,
                                         help="how many maximum words to print, roughly")

temperature = st.sidebar.slider('temperature', min_value=0., max_value=1., step=.10, value=.5,
                                help="lower means less creative but more accurate")

st.sidebar.markdown("---")
actions = st.sidebar.columns(2)

st.sidebar.markdown("---")
st.sidebar.markdown(f"v{ver} / st {st.__version__}")

# give a bit of time for sidebar widgets to render
time.sleep(0.05)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": assistant_greeting}]


def show_chat(the_messages, previous=""):
    with ((st.chat_message("assistant"))):
        message_placeholder = st.empty()
        response = previous

        for chunk, n in zip(ollama.chat(model_ref, messages=the_messages,
                                        options={'temperature': temperature},
                                        stream=True), range(context_length)):
            response = response + chunk['message']['content']
            message_placeholder.markdown(response + "▌")

        message_placeholder.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


def remove_last_occurrence(array, criteria_fn):
    for i in reversed(range(len(array))):
        if criteria_fn(array[i]):
            del array[i]
            break


def build_memory():
    if len(st.session_state.messages) > 2:
        return st.session_state.messages[1:-1]
    return []


def queue_chat(messages, continuation=""):
    # workaround because the chat boxes are not really replaced until a rerun
    st.session_state["prompt"] = messages
    st.session_state["continuation"] = continuation
    st.rerun()


if actions[0].button("😶‍🌫️ Forget", use_container_width=True,
                     help="Forget the previous conversations."):
    st.session_state.messages = [{"role": "assistant", "content": assistant_greeting}]
    if "prompt" in st.session_state and st.session_state["prompt"]:
        st.session_state["prompt"] = None
        st.session_state["continuation"] = None
    st.rerun()

if actions[1].button("🔂 Continue", use_container_width=True,
                     help="Continue the generation."):

    user_prompts = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"]

    if user_prompts:

        last_user_prompt = user_prompts[-1]

        assistant_responses = [msg["content"] for msg in st.session_state.messages
                               if msg["role"] == "assistant" and msg["content"] != assistant_greeting]
        last_assistant_response = assistant_responses[-1] if assistant_responses else ""

        # remove last line completely, so it is regenerated correctly (in case it stopped mid-word or mid-number)
        last_assistant_response_lines = last_assistant_response.split('\n')
        if len(last_assistant_response_lines) > 1:
            last_assistant_response_lines.pop()
            last_assistant_response = "\n".join(last_assistant_response_lines)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": last_user_prompt},
            {"role": "assistant", "content": last_assistant_response},
        ]

        # remove last assistant response from state, as it will be replaced with a continued one
        remove_last_occurrence(st.session_state.messages,
                               lambda msg: msg["role"] == "assistant" and msg["content"] != assistant_greeting)

        queue_chat(messages, last_assistant_response)

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

    messages = [{"role": "system", "content": system_prompt}]
    messages += build_memory()
    messages += [{"role": "user", "content": prompt}]

    queue_chat(messages)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# give a bit of time for messages to render
time.sleep(0.05)

if "prompt" in st.session_state and st.session_state["prompt"]:
    show_chat(st.session_state["prompt"], st.session_state["continuation"])
    st.session_state["prompt"] = None
    st.session_state["continuation"] = None
