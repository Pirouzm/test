import os
import json
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, send_file, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import io

from app import app, db
from models import User, Document, Chat, ChatMessage, Report
from utils import allowed_file, extract_text_from_file
from rag import process_document, query_knowledge_base
from report_generator import generate_esa_report

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Add a global context processor to provide current date/time to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Main routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('index.html', register=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('index.html', login=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/chat')
@login_required
def chat():
    # Get active chat or create new one
    active_chat_id = session.get('active_chat_id')
    active_chat = None
    
    if active_chat_id:
        active_chat = Chat.query.filter_by(id=active_chat_id, user_id=current_user.id).first()
    
    if not active_chat:
        # Create new chat
        active_chat = Chat(user_id=current_user.id)
        db.session.add(active_chat)
        db.session.commit()
        session['active_chat_id'] = active_chat.id
    
    # Get chat history
    chat_history = ChatMessage.query.filter_by(chat_id=active_chat.id).order_by(ChatMessage.timestamp).all()
    
    # Get user's documents
    documents = Document.query.filter_by(user_id=current_user.id).all()
    
    return render_template('chat.html', 
                           chat=active_chat, 
                           chat_history=chat_history,
                           documents=documents)

@app.route('/api/chat/new', methods=['POST'])
@login_required
def new_chat():
    # Create new chat
    new_chat = Chat(user_id=current_user.id)
    db.session.add(new_chat)
    db.session.commit()
    
    # Set as active chat
    session['active_chat_id'] = new_chat.id
    
    return jsonify({
        'success': True,
        'chat_id': new_chat.id
    })

@app.route('/api/chat/message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    chat_id = session.get('active_chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No active chat'}), 400
    
    # Save user message
    user_message = ChatMessage(
        chat_id=chat_id,
        role='user',
        content=data.get('message')
    )
    db.session.add(user_message)
    db.session.commit()
    
    # Get relevant context from the user's documents using RAG
    context = query_knowledge_base(data.get('message'), current_user.id)
    
    # Generate AI response with RAG context
    from rag import get_ai_response
    ai_response_text = get_ai_response(data.get('message'), context, chat_id)
    
    # Save AI response
    ai_message = ChatMessage(
        chat_id=chat_id,
        role='assistant',
        content=ai_response_text
    )
    db.session.add(ai_message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': ai_response_text
    })

@app.route('/api/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    chat_id = session.get('active_chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No active chat'}), 400
    
    chat_messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.timestamp).all()
    
    messages = []
    for msg in chat_messages:
        messages.append({
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({
        'success': True,
        'chat_id': chat_id,
        'messages': messages
    })

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Create document record
            doc = Document(
                filename=filename,
                file_path=file_path,
                file_type=file.content_type,
                user_id=current_user.id
            )
            db.session.add(doc)
            db.session.commit()
            
            # Process the document asynchronously (in a real app)
            # Here we do it synchronously for simplicity
            try:
                process_document(doc.id)
                flash('Document uploaded and processed successfully!', 'success')
            except Exception as e:
                app.logger.error(f"Error processing document: {str(e)}")
                flash(f'Document uploaded but could not be processed: {str(e)}', 'warning')
            
            return redirect(url_for('upload'))
    
    # List user's documents
    documents = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('upload.html', documents=documents)

@app.route('/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    
    # Delete the file
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        app.logger.error(f"Error deleting file: {str(e)}")
    
    # Delete from database
    db.session.delete(doc)
    db.session.commit()
    
    flash('Document deleted successfully', 'success')
    return redirect(url_for('upload'))

@app.route('/reports')
@login_required
def reports():
    user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.creation_date.desc()).all()
    return render_template('reports.html', reports=user_reports)

@app.route('/api/generate-report', methods=['POST'])
@login_required
def create_report():
    data = request.json
    chat_id = data.get('chat_id') or session.get('active_chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No chat selected for report generation'}), 400
    
    # Get chat history
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    chat_messages = ChatMessage.query.filter_by(chat_id=chat.id).order_by(ChatMessage.timestamp).all()
    
    # Get user's processed documents
    documents = Document.query.filter_by(user_id=current_user.id, is_processed=True).all()
    
    # Generate report
    report_title = f"ESA Report - {datetime.now().strftime('%Y-%m-%d')}"
    report_content = generate_esa_report(chat_messages, documents)
    
    # Save report to database
    new_report = Report(
        title=report_title,
        content=report_content,
        user_id=current_user.id,
        chat_id=chat.id
    )
    db.session.add(new_report)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'report_id': new_report.id,
        'title': new_report.title
    })

@app.route('/reports/<int:report_id>')
@login_required
def view_report(report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return render_template('reports.html', selected_report=report)

@app.route('/reports/<int:report_id>/download')
@login_required
def download_report(report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    
    # Create PDF (using simple text for now)
    pdf_content = f"ESA REPORT\n\nTitle: {report.title}\nDate: {report.creation_date.strftime('%Y-%m-%d')}\n\n{report.content}"
    
    # Create in-memory file
    buffer = io.BytesIO()
    buffer.write(pdf_content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{report.title.replace(' ', '_')}.txt",
        mimetype='text/plain'
    )

@app.route('/reports/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_report(report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    
    # Delete from database
    db.session.delete(report)
    db.session.commit()
    
    flash('Report deleted successfully', 'success')
    return redirect(url_for('reports'))
