import os
import glob
from dotenv import load_dotenv
from upstash_vector import Index, Vector

# Charger les variables
load_dotenv()

def parse_markdown_smart(file_path):
    """
    Découpe le fichier Markdown par titres (##) et sous-titres (###).
    Capture le titre de la section pour les métadonnées.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    filename = os.path.basename(file_path)
    chunks = []
    current_title = "Introduction"
    current_content = []
    
    for line in lines:
        # Détection des titres ## ou ###
        if line.startswith("## ") or line.startswith("### "):
            # Si on a déjà du contenu accumulé, on le sauvegarde
            if current_content:
                text = "".join(current_content).strip()
                if text:
                    chunks.append({
                        "id": f"{filename}-{len(chunks)}",
                        "content": f"## {current_title}\n{text}", 
                        "title": current_title
                    })
            
            # On met à jour le nouveau titre (sans les # et espaces)
            current_title = line.strip("#").strip()
            current_content = [] # On vide le tampon
        else:
            current_content.append(line)
            
    # Ne pas oublier la dernière section à la fin du fichier
    if current_content:
        text = "".join(current_content).strip()
        if text:
            chunks.append({
                "id": f"{filename}-{len(chunks)}",
                "content": f"## {current_title}\n{text}",
                "title": current_title
            })
            
    return chunks

def index_documents():
    """
    Fonction principale d'indexation mise à jour.
    """
    try:
        index = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        
        index.reset() # Attention : efface tout l'index existant
        print("Index réinitialisé.")
        
        md_files = glob.glob("data/*.md")
        vectors_to_upsert = []
        
        for file_path in md_files:
            # Utilisation de la nouvelle fonction de découpage
            chunks = parse_markdown_smart(file_path)
            
            for chunk in chunks:
                v = Vector(
                    id=chunk['id'],
                    data=chunk['content'],
                    metadata={
                        "filename": os.path.basename(file_path),
                        "section": chunk['title']  
                    }
                )
                vectors_to_upsert.append(v)
                
        if vectors_to_upsert:
            # On envoie par lots de 100 pour éviter les erreurs si beaucoup de données
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i+batch_size]
                index.upsert(vectors=batch)
                
            print(f"Succès : {len(vectors_to_upsert)} sections indexées avec métadonnées.")
            return True
            
    except Exception as e:
        print(f"Erreur d'indexation : {e}")
        return False

if __name__ == "__main__":
    index_documents()