import os
import logging
from openai import OpenAI
import chromadb
from chromadb.config import Settings
import numpy as np
import json

from app import app, db
from models import Document, Chat, ChatMessage
from utils import extract_text_from_file, split_text_into_chunks

# Configure logger
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# Initialize ChromaDB
PERSISTENCE_DIRECTORY = os.path.join(os.getcwd(), 'chromadb')
os.makedirs(PERSISTENCE_DIRECTORY, exist_ok=True)

chroma_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=PERSISTENCE_DIRECTORY
))

# Create a collection for document embeddings
try:
    document_collection = chroma_client.get_or_create_collection(
        name="esa_documents",
        metadata={"hnsw:space": "cosine"}
    )
except Exception as e:
    logger.error(f"Error initializing ChromaDB collection: {str(e)}")
    document_collection = None

def generate_embedding(text):
    """
    Generate embedding vector for a piece of text using OpenAI's embedding API
    
    Args:
        text (str): The text to embed
        
    Returns:
        list: The embedding vector
    """
    try:
        if not text.strip():
            return []
        
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return []

def process_document(document_id):
    """
    Process a document: extract text, chunk it, generate embeddings, and store in vector db
    
    Args:
        document_id (int): ID of the document to process
        
    Returns:
        bool: Success status
    """
    document = db.session.get(Document, document_id)
    
    if not document:
        logger.error(f"Document with ID {document_id} not found")
        return False
    
    try:
        # Extract text from file
        text = extract_text_from_file(document.file_path)
        
        if not text:
            logger.warning(f"No text extracted from document {document.filename}")
            return False
        
        # Split text into chunks
        chunks = split_text_into_chunks(text)
        
        # Generate embeddings and add to ChromaDB
        if not chunks:
            logger.warning(f"No chunks generated for document {document.filename}")
            return False
        
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = generate_embedding(chunk)
            
            if not embedding:
                logger.warning(f"Could not generate embedding for chunk {i} of document {document.filename}")
                continue
            
            chunk_id = f"doc_{document_id}_chunk_{i}"
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            metadatas.append({
                "document_id": document_id,
                "chunk_index": i,
                "document_name": document.filename,
                "user_id": document.user_id
            })
            documents.append(chunk)
        
        if not ids:
            logger.warning(f"No valid embeddings generated for document {document.filename}")
            return False
        
        # Add to ChromaDB
        document_collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        # Update document status
        document.is_processed = True
        document.vector_store_id = f"doc_{document_id}"
        db.session.commit()
        
        logger.info(f"Successfully processed document {document.filename} with {len(ids)} chunks")
        return True
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        return False

def query_knowledge_base(query, user_id, top_k=5):
    """
    Query the knowledge base using RAG to retrieve relevant context
    
    Args:
        query (str): User query
        user_id (int): ID of the current user
        top_k (int): Number of top results to return
        
    Returns:
        list: Retrieved relevant document chunks
    """
    try:
        # Generate embedding for query
        query_embedding = generate_embedding(query)
        
        if not query_embedding:
            logger.warning("Could not generate embedding for query")
            return []
        
        # Query ChromaDB for similar documents from this user
        results = document_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id}
        )
        
        if not results or not results['documents']:
            logger.info("No relevant documents found in knowledge base")
            return []
        
        # Return retrieved documents
        return results['documents'][0]
        
    except Exception as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        return []

def get_ai_response(user_message, context, chat_id):
    """
    Generate AI response using OpenAI with RAG context
    
    Args:
        user_message (str): User's message
        context (list): List of relevant document chunks from RAG
        chat_id (int): ID of the current chat
        
    Returns:
        str: AI response
    """
    try:
        # Get chat history
        chat_messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.timestamp).all()
        
        # Format chat history for OpenAI API
        messages = [{"role": "system", "content": (
            "You are an AI assistant helping to create Emotional Support Animal (ESA) reports. "
            "Your goal is to gather information about the user's mental health condition, "
            "how an emotional support animal helps them, and relevant medical history. "
            "Be empathetic, professional, and thorough in your responses."
        )}]
        
        # Add chat history (max 10 messages to stay within context limits)
        for msg in chat_messages[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add RAG context if available
        if context:
            context_message = (
                "I've found some relevant information from your documents that might help: \n\n" +
                "\n\n---\n\n".join(context) +
                "\n\nLet me use this information to help you better."
            )
            messages.append({"role": "assistant", "content": context_message})
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Generate response
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return "I apologize, but I encountered an error while processing your request. Please try again later."
