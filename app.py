import streamlit as st
import os
from dotenv import load_dotenv
from upstash_vector import Index
from agents import Agent, Runner, function_tool
import indexer  # <--- 1. On importe notre script d'indexation

# Charger les variables
load_dotenv()

# --- LANCEMENT AUTOMATIQUE DE L'INDEXATION ---
# On vérifie si on a déjà fait la mise à jour dans cette session
if "indexation_done" not in st.session_state:
    with st.spinner('Mise à jour des connaissances de l\'IA en cours...'):
        success = indexer.index_documents() # <--- 2. On lance l'indexation
        if success:
            st.toast("✅ Base de connaissances mise à jour avec succès !", icon="🚀")
        else:
            st.toast("⚠️ Attention : Problème lors de la mise à jour des données.", icon="⚠️")
    
    # On marque l'action comme faite pour ne pas recommencer au prochain clic
    st.session_state.indexation_done = True


# --- CONFIGURATION UPSTASH (LA TOOL) ---
@function_tool
def search_portfolio(query_text: str) -> str:
    """
    Cherche des informations dans le portfolio de Jules Dubuy en utilisant la base de données vectorielle.
    Utilisez cet outil dès qu'une question concerne le parcours, les projets ou les compétences de Jules.
    """
    try:
        index = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        results = index.query(
            data=query_text,
            top_k=3,
            include_metadata=True,
            include_data=True
        )
        
        context = ""
        for res in results:
            source = res.metadata.get('filename', 'Inconnu')
            context += f"---\nSource: {source}\nContenu:\n{res.data}\n"
        
        return context if context else "Aucune information trouvée dans le portfolio."
    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"

# --- CONFIGURATION DE L'AGENT ---
if "portfolio_agent" not in st.session_state:
    st.session_state.portfolio_agent = Agent(
        name="Jules Assistant",
        model="gpt-4.1-nano",
        instructions=(
            "Tu es l'assistant virtuel de Jules Dubuy. Ton but est de répondre aux recruteurs "
            "et visiteurs de son portfolio. "
            "Utilise TOUJOURS l'outil 'search_portfolio' pour vérifier les faits avant de répondre. "
            "Sois professionnel, concis et courtois. Si tu ne trouves pas l'info, dis-le honnêtement."
        ),
        tools=[search_portfolio]
    )

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Chat avec le Portfolio de Jules", page_icon="🤖")

st.title("💬 Discutez avec mon Portfolio")
st.write("Posez-moi des questions sur mes projets, mes expériences ou mes compétences !")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ex: Quelles sont tes compétences en Python ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Recherche dans le portfolio..."):
            try:
                result = Runner.run_sync(st.session_state.portfolio_agent, prompt)
                response = result.final_output
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Une erreur est survenue : {e}")