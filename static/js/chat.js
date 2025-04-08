document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');
    const chatContainer = document.getElementById('chatContainer');
    const newChatBtn = document.getElementById('newChatBtn');
    const generateReportBtn = document.getElementById('generateReportBtn');

    // Function to add a message to the chat
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'assistant-message'}`;
        messageDiv.innerHTML = content;
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Function to add typing indicator
    function addTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typingIndicator';
        indicator.innerHTML = 'AI is typing<span></span><span></span><span></span>';
        chatMessages.appendChild(indicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Function to remove typing indicator
    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input
        messageInput.value = '';
        
        // Show typing indicator
        addTypingIndicator();
        
        // Send message to server
        fetch('/api/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            removeTypingIndicator();
            
            if (data.success) {
                // Add AI response to chat
                addMessage(data.message);
            } else {
                // Show error
                addMessage('Sorry, I encountered an error. Please try again.');
            }
        })
        .catch(error => {
            // Remove typing indicator
            removeTypingIndicator();
            
            // Show error
            addMessage('Sorry, there was a network error. Please try again.');
            console.error('Error:', error);
        });
    });

    // Handle new chat button
    newChatBtn.addEventListener('click', function() {
        if (confirm('Start a new chat? This will clear the current conversation.')) {
            fetch('/api/chat/new', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear chat messages
                    chatMessages.innerHTML = '';
                    
                    // Add welcome message
                    addMessage("Hello! I'm your AI assistant for generating ESA reports. I can help gather information about your mental health condition and how an emotional support animal helps you. What would you like to discuss today?");
                } else {
                    alert('Failed to create new chat.');
                }
            })
            .catch(error => {
                alert('Error creating new chat. Please try again.');
                console.error('Error:', error);
            });
        }
    });

    // Handle generate report button
    generateReportBtn.addEventListener('click', function() {
        // First check if there are any messages in the chat
        if (chatMessages.childElementCount <= 1) {
            alert('Please have a conversation before generating a report.');
            return;
        }

        if (confirm('Generate an ESA report based on this conversation?')) {
            generateReportBtn.disabled = true;
            generateReportBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Generating...';
            
            fetch('/api/generate-report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                generateReportBtn.disabled = false;
                generateReportBtn.innerHTML = '<i class="fas fa-file-medical me-1"></i> Generate ESA Report';
                
                if (data.success) {
                    alert('Report generated successfully!');
                    // Redirect to the report page
                    window.location.href = `/reports/${data.report_id}`;
                } else {
                    alert('Failed to generate report: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                generateReportBtn.disabled = false;
                generateReportBtn.innerHTML = '<i class="fas fa-file-medical me-1"></i> Generate ESA Report';
                
                alert('Error generating report. Please try again.');
                console.error('Error:', error);
            });
        }
    });

    // Auto-scroll to bottom of chat on page load
    chatContainer.scrollTop = chatContainer.scrollHeight;
});
