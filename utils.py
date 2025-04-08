import os
import logging
from app import app
from PyPDF2 import PdfReader
import docx
import re

# Configure logger
logger = logging.getLogger(__name__)

# File extension whitelist
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'rtf'}

def allowed_file(filename):
    """Check if a file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    """
    Extract text content from various file types
    Supports PDF, DOCX, TXT
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: Extracted text content
    """
    file_ext = file_path.rsplit('.', 1)[1].lower()
    
    try:
        if file_ext == 'pdf':
            return extract_text_from_pdf(file_path)
        elif file_ext == 'docx':
            return extract_text_from_docx(file_path)
        elif file_ext == 'txt':
            return extract_text_from_txt(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        return ""

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
    
    return clean_text(text)

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
    
    return clean_text(text)

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    text = ""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            text = file.read()
    except Exception as e:
        logger.error(f"Error extracting text from TXT: {str(e)}")
    
    return clean_text(text)

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters
    text = re.sub(r'[^\w\s\.\,\?\!\:\;\-\']', '', text)
    
    return text.strip()

def split_text_into_chunks(text, chunk_size=1000, overlap=200):
    """
    Split text into overlapping chunks for embedding
    
    Args:
        text (str): Text to split
        chunk_size (int): Size of each chunk in characters
        overlap (int): Overlap between chunks in characters
        
    Returns:
        list: List of text chunks
    """
    if not text:
        return []
    
    # Split by paragraphs first
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) <= chunk_size:
            current_chunk += paragraph + "\n"
        else:
            # Add current chunk to list if it's not empty
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Start new chunk, but include overlap from previous chunk
            if len(current_chunk) > overlap:
                # Take the last 'overlap' characters from the previous chunk
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + paragraph + "\n"
            else:
                current_chunk = paragraph + "\n"
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
