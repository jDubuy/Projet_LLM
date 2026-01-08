import os
import glob
from dotenv import load_dotenv
from upstash_vector import Index, Vector

# Charger les variables
load_dotenv()

def parse_markdown_file(file_path):
    """
    Lit un fichier Markdown et le découpe en morceaux basés sur les titres '##'.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(file_path).replace(".md", "")
    sections = content.split("## ")
    
    chunks = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        text_content = section.strip()
        if i > 0: 
            text_content = "## " + text_content
            
        chunks.append({
            "id": f"{filename}-{i}",
            "content": text_content
        })
    return chunks

def index_documents():
    """
    Fonction principale qui lance l'indexation de tous les fichiers.
    Retourne True si succès, False sinon.
    """
    try:
        # Connexion
        index = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        
        # --- AMÉLIORATION 1 : Reset de l'index ---
        # On supprime tout avant de réindexer pour éviter les doublons ou données fantômes
        index.reset()
        print("Index réinitialisé avec succès.")
        
        # Récupération des fichiers
        md_files = glob.glob("data/*.md")
        if not md_files:
            print("Aucun fichier Markdown trouvé dans le dossier 'data'.")
            return False
        
        vectors_to_upsert = []
        
        for file_path in md_files:
            chunks = parse_markdown_file(file_path)
            for chunk in chunks:
                v = Vector(
                    id=chunk['id'],
                    data=chunk['content'],
                    metadata={"filename": os.path.basename(file_path)}
                )
                vectors_to_upsert.append(v)
                
        if vectors_to_upsert:
            index.upsert(vectors=vectors_to_upsert)
            print(f"Succès : {len(vectors_to_upsert)} sections indexées.")
            return True
            
    except Exception as e:
        print(f"Erreur d'indexation : {e}")
        return False

if __name__ == "__main__":
    index_documents()