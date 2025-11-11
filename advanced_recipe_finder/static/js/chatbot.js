// Chatbot functionality using Gemini API

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const clearChatBtn = document.getElementById('clearChatBtn');
    
    if (chatForm) {
        // Load chat history
        loadChatHistory();
        
        // Handle form submission
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            sendMessage();
        });
        
        // Handle clear chat button
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', clearChatHistory);
        }
        
        // Auto-resize textarea and handle enter key
        if (chatInput) {
            chatInput.addEventListener('input', autoResizeTextarea);
            
            // Handle Enter key
            chatInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault(); // Prevent default to avoid new line
                    if (chatInput.value.trim()) {
                        sendMessage();
                    }
                }
            });
        }
    }
});

// Auto-resize textarea
function autoResizeTextarea() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
}

// Send message to chatbot
async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    
    // Show typing indicator
    const typingIndicator = addTypingIndicator();
    
    try {
        // Send message to server
        const response = await fetch('/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        // Remove typing indicator
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        if (response.ok) {
            const data = await response.json();
            
            // Add bot response to chat
            addMessageToChat('bot', data.response);
            
            // Scroll to bottom
            scrollChatToBottom();
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        
        // Remove typing indicator
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        // Show error message
        addMessageToChat('bot', 'Sorry, I encountered an error. Please try again later.');
        scrollChatToBottom();
    }
}

// Add message to chat
function addMessageToChat(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const messageEl = document.createElement('div');
    messageEl.className = `message-wrapper ${sender}-wrapper`;
    
    const avatar = sender === 'user' ? 
        '<i class="fas fa-user-circle"></i>' : 
        '<i class="fas fa-robot"></i>';
    
    messageEl.innerHTML = `
        <div class="chat-message ${sender}-message">
            <div class="message-content">
                <div class="message-sender">
                    ${avatar}
                    <span class="sender-name">${sender === 'user' ? 'You' : 'Recipe Assistant'}</span>
                </div>
                <div class="message-text">${formatMessage(message)}</div>
                <div class="message-time">${getCurrentTime()}</div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageEl);
    
    // Trigger animation after a small delay
    setTimeout(() => {
        messageEl.querySelector('.chat-message').classList.add('message-shown');
    }, 50);
    
    scrollChatToBottom();
    
    // Save to chat history
    saveToChatHistory(sender, message);
}

// Add typing indicator
function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return null;
    
    const typingEl = document.createElement('div');
    typingEl.className = 'chat-message bot-message typing-indicator';
    typingEl.innerHTML = `
        <div class="message-content">
            <div class="message-sender"><i class="fas fa-robot me-2"></i> Recipe Assistant</div>
            <div class="message-text">
                <span class="typing-dots">
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                </span>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingEl);
    scrollChatToBottom();
    
    return typingEl;
}

// Format message (convert URLs to links, etc.)
function formatMessage(message) {
    // Convert URLs to links
    message = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    
    // Convert line breaks to HTML
    message = message.replace(/\n/g, '<br>');
    
    return message;
}

// Get current time in HH:MM format
function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Scroll chat to bottom
function scrollChatToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Save message to chat history
function saveToChatHistory(sender, message) {
    // This is just client-side storage; server handles permanent storage
    let chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    chatHistory.push({
        sender: sender,
        message: message,
        timestamp: new Date().toISOString()
    });
    
    // Keep only the last 50 messages
    if (chatHistory.length > 50) {
        chatHistory = chatHistory.slice(-50);
    }
    
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

// Load chat history
function loadChatHistory() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    
    // Clear existing messages (except welcome message if it exists)
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    chatMessages.innerHTML = '';
    
    if (welcomeMessage) {
        chatMessages.appendChild(welcomeMessage);
    }
    
    // Add messages from history
    chatHistory.forEach(msg => {
        addMessageToChat(msg.sender, msg.message);
    });
    
    scrollChatToBottom();
}

// Clear chat history
function clearChatHistory() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        localStorage.removeItem('chatHistory');
        
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            // Clear all messages except welcome message
            const welcomeMessage = chatMessages.querySelector('.welcome-message');
            chatMessages.innerHTML = '';
            
            if (welcomeMessage) {
                chatMessages.appendChild(welcomeMessage);
            }
            
            scrollChatToBottom();
        }
        
        showToast('Chat history cleared', 'info');
    }
}

// Initialize quick questions
function initQuickQuestions() {
    const quickQuestions = document.querySelectorAll('.quick-question');
    quickQuestions.forEach(question => {
        question.addEventListener('click', function() {
            const chatInput = document.getElementById('chatInput');
            if (chatInput) {
                chatInput.value = this.textContent;
                chatInput.focus();
                autoResizeTextarea.call(chatInput);
            }
        });
    });
}

// Initialize quick questions
initQuickQuestions();