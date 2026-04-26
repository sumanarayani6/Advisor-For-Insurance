import streamlit as st
import asyncio, os
from dotenv import load_dotenv

# Semantic Kernel Imports
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.google_ai import GoogleAIChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.google.google_ai.google_ai_prompt_execution_settings import GoogleAIPromptExecutionSettings
from plugins import InsuranceWorkPlugin, WebSearchPlugin

load_dotenv()

# --- AGENT LOGIC ---
async def run_agent(user_input, chat_history):
    # Initialize the kernel normally
    kernel = Kernel()
    
    # Add the Gemini Service
    kernel.add_service(GoogleAIChatCompletion(
        gemini_model_id="gemini-3-flash-preview", 
        api_key=os.getenv("GEMINI_API_KEY")
    ))
    
    # Register your plugins
    kernel.add_plugin(WebSearchPlugin(), plugin_name="Searcher")
    kernel.add_plugin(InsuranceWorkPlugin(), plugin_name="Worker")
    
    # Configure the "Auto" behavior
    settings = GoogleAIPromptExecutionSettings(
    function_choice_behavior=FunctionChoiceBehavior.Auto(),
    # Some hosted versions of SK need this explicitly if the model 
    # returns unexpected reasoning parts
    extra_parameters={"include_thoughts": False} 
)

    # Combine history and new prompt for Gemini's memory
   # Change the prompt_with_context to be more "Command" oriented
    prompt_with_context = (
    "You are a Senior Insurance Advisor. You have two sources of truth: "
    "1. The 'KnowledgeBase' (Use this first for policy facts). "
    "2. The 'Searcher' (Use this ONLY for current pricing or news). "
    
    "CRITICAL INSTRUCTIONS: "
    "- Do NOT let search results override your logical reasoning. "
    "- If search results are messy or 'noisy', ignore the junk and use your internal "
    "knowledge of insurance principles to fill the gaps. "
    "- If a tool fails, stay professional and use the information you ALREADY HAVE "
    "to provide a helpful estimate instead of an apology."
    "If the user asks you to calculate premium, you MUST have the following data from the user: "
    "1. Age, 2. Tobacco/Smoking Status, 3. Any Pre-Existing Diseases (PED), 4. Number of claim-free years (NCB). "
    
    "INSTRUCTIONS: "
    "Only do the premium calcualtion if the user asks otherwise don't do"
    "- If the user hasn't provided these, ask for them politely one by one or as a list. "
    "- Once you have the data, call 'MathEngine-CalculatePremium' to get the final numbers. "
    "- Use the 2026 GST rule (0 percent for health) in your explanation.\n"
    f"--- HISTORY ---\n{chat_history}\n"
    f"--- REQUEST ---\n{user_input}"
)
    # Invoke the prompt
    result = await kernel.invoke_prompt(
        prompt=prompt_with_context,
        settings=settings
    )
    return result

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Insurance AI", page_icon="🛡️")
# Bold and Colored highlights
import streamlit as st

# Custom HTML for the logo and title
import streamlit as st

# Custom HTML for the typographical logo
import streamlit as st

# Custom HTML for the typographical logo
st.markdown(
    """
    <div style='text-align: left; margin-bottom: 20px;'>
        <h1 style='font-family: sans-serif; letter-spacing: -1px; margin: 0;'>
            <span style='color: #007BFF; font-weight: bold;'>A</span>dvisor 
            for <span style='color: #007BFF; font-weight: bold;'>I</span>nsurance
        </h1>
    </div>
    """, 
    unsafe_allow_html=True
)
#st.markdown(
#    "<h1>🛡️ <span style='color:red; font-weight:bold;'>A</span>dvisor for <span style='color:red; font-weight:bold;'>I</span>nsurance</h1>", 
 #   unsafe_allow_html=True
#)

# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# This loop ensures previous chats stay on the screen after the page reruns
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("Ask me something..."):
    # Clear any old PDFs from previous turns
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            os.remove(file)

    # 1. Display user message and save to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("Searching and thinking..."):
            try:
                # Format previous messages for Gemini's context
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                
                final_result = asyncio.run(run_agent(prompt, history_text))
                response_text = str(final_result)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

                # 3. Dynamic PDF Handling
                # Check if a new PDF was created in this turn
                pdfs = [f for f in os.listdir(".") if f.endswith(".pdf")]
                if pdfs:
                    # Get the most recently created PDF
                    latest_pdf = max(pdfs, key=os.path.getmtime)
                    with open(latest_pdf, "rb") as f:
                        st.download_button(
                            label=f"📄 Download {latest_pdf}",
                            data=f,
                            file_name=latest_pdf,
                            mime="application/pdf"
                        )

            except Exception as e:
                st.error(f"Error: {e}")
