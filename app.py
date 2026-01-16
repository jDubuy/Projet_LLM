import streamlit as st
import os
from dotenv import load_dotenv
from upstash_vector import Index
from agents import Agent, Runner, function_tool
import indexer

# Charger les variables
load_dotenv()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Assistant portfolio de Jules")

# --- INITIALISATION DES VARIABLES DE SESSION ---
# On initialise l'historique
if "messages" not in st.session_state:
    st.session_state.messages = []

# On initialise la liste des questions suggérées
if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = [
        "Quelles sont tes compétences ?",
        "Parle-moi de tes projets",
        "Quelle est ton expérience pro ?",
        "Quelles sont tes passions ?"
    ]

# --- SIDEBAR (ADMINISTRATION & RESET) ---
with st.sidebar:
    st.header("⚙️ Administration")
    if st.button("🗑️ Réinitialiser la conversation"):
        st.session_state.messages = []
        # On remet les questions par défaut
        st.session_state.suggested_questions = [
            "Quelles sont tes compétences ?",
            "Parle-moi de tes projets",
            "Quelle est ton expérience pro ?",
            "Quelles sont tes passions ?"
        ]
        st.rerun() 

    st.divider()

# --- CONFIGURATION UPSTASH (LA TOOL) ---
@function_tool
def search_portfolio(query_text: str) -> str:
    """
    Cherche des informations dans le portfolio de Jules Dubuy.
    """
    try:
        index = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        results = index.query(
            data=query_text,
            top_k=7,
            include_metadata=True,
            include_data=True
        )
        
        context = ""
        for res in results:
            file_source = res.metadata.get('filename', 'Inconnu')
            section_source = res.metadata.get('section', 'Général')
            context += f"---\nSource: {file_source} (Section: {section_source})\nContenu:\n{res.data}\n"
        
        return context if context else "Aucune information trouvée."
    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"

# --- CONFIGURATION DE L'AGENT ---
system_prompt = """
Tu es l'assistant virtuel de Jules Dubuy, Data Analyst.
Ton but est de mettre en valeur son profil auprès des recruteurs.

Règles impératives :
1. **Utilisation de l'outil** : Pour CHAQUE question utilisateur, tu DOIS utiliser l'outil `search_portfolio`. Ne réponds jamais de mémoire.
2. **Reformulation** : L'outil de recherche fonctionne par mots-clés. Avant d'appeler l'outil, reformule la demande de l'utilisateur pour qu'elle soit précise.
3. **Réponse** : Sois professionnel, concis et utilise le Markdown.
4. **Contact** : Propose l'email (jules.dubuy1810@gmail.com) si nécessaire.
"""

if "portfolio_agent" not in st.session_state:
    st.session_state.portfolio_agent = Agent(
        name="Jules Assistant",
        model="gpt-4.1-nano",
        instructions=system_prompt,
        tools=[search_portfolio]
    )

# --- INTERFACE DE CHAT ---
st.markdown('<div class="main-header"><h1>💬 Discutez avec mon Portfolio</h1><p>Je peux vous parler de mes projets, de mes expériences ou de mes passions!</p></div>', unsafe_allow_html=True)

# Affichage de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- GESTION DES QUESTIONS PRÉDÉFINIES (QUICK REPLIES) ---
clicked_prompt = None

with st.container():
    if st.session_state.suggested_questions:
        st.write("Suggestions :")
        cols = st.columns(len(st.session_state.suggested_questions))

        for i, question in enumerate(st.session_state.suggested_questions):
            if cols[i].button(question):
                clicked_prompt = question
                st.session_state.suggested_questions.pop(i)
                # On laisse le code continuer pour traiter le prompt

# --- ZONE DE SAISIE PRINCIPALE ---
chat_input_prompt = st.chat_input("Posez votre question ici...")

# On détermine quelle est la source du prompt (Clic bouton OU Saisie clavier)
final_prompt = clicked_prompt if clicked_prompt else chat_input_prompt

if final_prompt:
    # 1. On affiche le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.markdown(final_prompt)

    # 2. Préparation du contexte (Historique)
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]]) 
    full_prompt = f"Historique :\n{history_str}\n\nNouvelle question : {final_prompt}"

    # 3. Réponse de l'agent
    with st.chat_message("assistant"):
        with st.spinner("Jules réfléchit..."):
            try:
                result = Runner.run_sync(st.session_state.portfolio_agent, full_prompt)
                response = result.final_output
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                if clicked_prompt:
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Erreur : {e}")