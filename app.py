import streamlit as st
import os
from dotenv import load_dotenv
from upstash_vector import Index
from agents import Agent, Runner, function_tool
import indexer

# Charger les variables
load_dotenv()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Portfolio de Jules", page_icon="👋")

# --- SIDEBAR (ADMINISTRATION) ---
with st.sidebar:
    st.header("⚙️ Administration")
    st.write("Utilisez ce bouton pour mettre à jour l'IA après avoir modifié vos fichiers Markdown.")
    
    if st.button("Mettre à jour les connaissances"):
        with st.spinner('Indexation en cours...'):
            success = indexer.index_documents()
            if success:
                st.success("Index mis à jour avec succès ! 🚀")
            else:
                st.error("Erreur lors de la mise à jour.")

# --- CONFIGURATION UPSTASH (LA TOOL) ---
@function_tool
def search_portfolio(query_text: str) -> str:
    """
    Cherche des informations dans le portfolio de Jules Dubuy.
    À utiliser pour toute question sur le parcours, les projets, les compétences ou les passions.
    """
    try:
        index = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        results = index.query(
            data=query_text,
            top_k=5, # On augmente un peu pour avoir plus de contexte
            include_metadata=True,
            include_data=True
        )
        
        context = ""
        for res in results:
            source = res.metadata.get('filename', 'Inconnu')
            context += f"---\nSource: {source}\nContenu:\n{res.data}\n"
        
        return context if context else "Aucune information trouvée."
    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"

# --- CONFIGURATION DE L'AGENT ---
# Amélioration du Prompt Système (Personnalité + Formatage)
system_prompt = """
Tu es l'assistant virtuel de Jules Dubuy, un Data Analyst passionné et curieux.
Ton rôle est de répondre aux recruteurs et visiteurs de son portfolio.

Règles de comportement :
1. **Ton** : Sois professionnel mais enthousiaste et dynamique. Montre que Jules est quelqu'un d'agréable.
2. **Précision** : Utilise TOUJOURS l'outil 'search_portfolio' pour répondre. N'invente rien.
3. **Formatage** : Utilise le Markdown pour rendre la lecture agréable (listes à puces, gras pour les mots clés).
4. **Honnêteté** : Si tu ne trouves pas l'info dans les documents, dis-le simplement et propose de contacter Jules directement.
5. **Contact** : Si l'utilisateur souhaite contacter Jules, donne-lui toujours son email et son LinkedIn de manière claire (ces infos sont dans le fichier contact.md).
"""

if "portfolio_agent" not in st.session_state:
    st.session_state.portfolio_agent = Agent(
        name="Jules Assistant",
        model="gpt-4.1-nano",
        instructions=system_prompt,
        tools=[search_portfolio]
    )

# --- INTERFACE DE CHAT ---
st.title("💬 Discutez avec mon Portfolio")
st.write("Je peux vous parler de mes projets, de mes expériences ou de mes passions!")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie
if prompt := st.chat_input("Ex: Parle-moi de tes projets en Python..."):
    # 1. On affiche le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. On prépare le contexte (Mémoire de conversation)
    # On concatène les derniers échanges pour que l'agent ait le contexte
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]]) 
    full_prompt = f"Historique de la conversation récente :\n{history_str}\n\nNouvelle question utilisateur : {prompt}"

    # 3. L'agent répond
    with st.chat_message("assistant"):
        with st.spinner("Jules réfléchit..."):
            try:
                # On envoie le prompt enrichi avec l'historique
                result = Runner.run_sync(st.session_state.portfolio_agent, full_prompt)
                response = result.final_output
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Oups, une erreur est survenue : {e}")