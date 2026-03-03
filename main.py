import dotenv

dotenv.load_dotenv()
import time
import asyncio
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life Coach Agent",
        instructions="""
            ## Role & Persona
            You are an empathetic, encouraging, and highly practical Life Coach. 
            Your goal is to help users bridge the gap between where they are and where they want to be.

            ## Guidelines
            1. **Active Listening**: Acknowledge the user's feelings before giving advice. 
            2. **Actionable Steps**: Always break down big goals into small, "atomic" habits or tasks.
            3. **Tone**: Warm, professional, and non-judgmental. Use "Growth Mindset" language.

            ## Tool Usage: Web Search Tool
            - Use this tool when the user's query involves:
                - Latest trends in productivity, psychology, or wellness.
                - Specific self-improvement techniques (e.g., "The latest research on Pomodoro").
                - Motivational stories or case studies that are not in your training data.
            - If the user asks for advice on a topic with new developments, ALWAYS cross-check with the Web Search Tool to provide the most current and evidence-based guidance.
            """,
        tools=[
            WebSearchTool(),
        ],
    )
agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "life-coach-agent-memory.db",
    )
session = st.session_state["session"]

async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"])
        if "type" in message and message["type"] == "web_search_call":
            with st.chat_message("ai"):
                st.write("🔍 웹 검색중...")


def update_status(status_container, event):

    status_messages = {
        "response.web_search_call.completed": ("✅ 웹 검색 완료.", "complete"),
        "response.web_search_call.in_progress": (
            "🔍 웹 검색 중...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔍 웹 검색 진행 중...",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)

asyncio.run(paint_history())

async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":

                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)


prompt = st.chat_input("Write a message for your assistant")

if prompt:
    with st.chat_message("human"):
        st.write(prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))