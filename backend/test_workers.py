"""
Script de test pour les workers Processing et Chunking.

Ce script crée un utilisateur de test, un document de test,
et lance les workers pour tester le pipeline complet.
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Ajouter le chemin de l'application
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.document import Document, DocumentStatus
from app.core.security import get_password_hash
from app.workers.processing_tasks import extract_document_text


def create_test_user(db):
    """Crée un utilisateur de test s'il n'existe pas."""
    # Chercher l'utilisateur existant
    user = db.query(User).filter(User.email == "test@test.com").first()
    
    if user:
        print(f"✅ Utilisateur existant trouvé: {user.email} (ID: {user.id})")
        return user
    
    # Créer un nouvel utilisateur
    user = User(
        id=uuid.uuid4(),
        email="test@beac.com",
        matricule="C2222",
        hashed_password=get_password_hash("test123"),
        nom="Test User",
        prenom="Test",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    print(f"✅ Utilisateur créé: {user.matricule} (ID: {user.id})")
    return user


def create_test_file():
    """Crée un fichier PDF de test."""
    test_file_path = Path("/app/uploads/test.pdf")
    
    # Créer le dossier uploads s'il n'existe pas
    test_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Créer un fichier PDF simple de test
    if not test_file_path.exists():
        # Contenu minimal d'un PDF valide
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World!) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
        with open(test_file_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ Fichier de test créé: {test_file_path}")
    else:
        print(f"✅ Fichier de test existant: {test_file_path}")
    
    return str(test_file_path)


def create_test_document(db, user_id, file_path):
    """Crée un document de test."""
    # Générer un hash simple pour le test
    file_hash = "a" * 64
    
    # Vérifier si le document existe déjà
    existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing_doc:
        print(f"✅ Document existant trouvé: {existing_doc.id}")
        return existing_doc
    
    # Créer le document
    document = Document(
        id=uuid.uuid4(),
        original_filename="test.pdf",
        file_path=file_path,
        file_hash=file_hash,
        file_size_bytes=1000,
        mime_type="application/pdf",
        file_extension="pdf",
        uploaded_by=user_id,
        status=DocumentStatus.PENDING,
        retry_count=0,
        total_chunks=0,
        uploaded_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    print(f"✅ Document créé: {document.id}")
    print(f"   - Filename: {document.original_filename}")
    print(f"   - Path: {document.file_path}")
    print(f"   - Status: {document.status}")
    
    return document


def test_extraction(document_id):
    """Teste l'extraction de texte."""
    print(f"\n🚀 Lancement de l'extraction pour le document {document_id}")
    
    try:
        # Lancer la tâche d'extraction de manière asynchrone
        result = extract_document_text.delay(str(document_id))
        
        print(f"✅ Task d'extraction lancée: {result.id}")
        print(f"   Vous pouvez suivre la progression dans Flower: http://localhost:5555")
        print(f"   Ou dans les logs: docker-compose logs -f celery-worker-processing")
        
        return result
        
    except Exception as e:
        print(f"❌ Erreur lors du lancement de l'extraction: {e}")
        return None


def check_document_status(db, document_id):
    """Vérifie le statut du document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        print(f"❌ Document {document_id} non trouvé")
        return
    
    print(f"\n📊 Statut du document {document_id}:")
    print(f"   - Status: {document.status}")
    print(f"   - Processing Stage: {document.processing_stage}")
    print(f"   - Total Pages: {document.total_pages}")
    print(f"   - Total Chunks: {document.total_chunks}")
    print(f"   - Extracted Text Length: {document.extracted_text_length}")
    print(f"   - Extraction Time: {document.extraction_time_seconds}s")
    print(f"   - Chunking Time: {document.chunking_time_seconds}s")
    print(f"   - Error: {document.error_message}")
    print(f"   - Retry Count: {document.retry_count}")


def main():
    """Fonction principale."""
    print("=" * 60)
    print("TEST DES WORKERS - SPRINT 4 PHASE 2")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Créer un utilisateur de test
        print("\n📝 Étape 1: Création de l'utilisateur de test")
        user = create_test_user(db)
        
        # 2. Créer un fichier de test
        print("\n📁 Étape 2: Création du fichier de test")
        file_path = create_test_file()
        
        # 3. Créer un document de test
        print("\n📄 Étape 3: Création du document de test")
        document = create_test_document(db, user.id, file_path)
        
        # 4. Lancer l'extraction
        print("\n🔧 Étape 4: Lancement de l'extraction")
        result = test_extraction(document.id)
        
        if result:
            print(f"\n✅ Test lancé avec succès!")
            print(f"\n📋 Prochaines étapes:")
            print(f"   1. Vérifier dans Flower: http://localhost:5555")
            print(f"   2. Vérifier les logs: docker-compose logs -f celery-worker-processing")
            print(f"   3. Vérifier le statut du document:")
            print(f"      python test_workers.py check {document.id}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()


def check_status_cmd():
    """Commande pour vérifier le statut d'un document."""
    if len(sys.argv) < 3:
        print("Usage: python test_workers.py check <document_id>")
        return
    
    document_id = sys.argv[2]
    db = SessionLocal()
    
    try:
        check_document_status(db, document_id)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_status_cmd()
    else:
        main()