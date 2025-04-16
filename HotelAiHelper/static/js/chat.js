// Hotel Concierge Chat Interface

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const resetButton = document.getElementById('reset-chat');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    
    // Event Listeners
    chatForm.addEventListener('submit', sendMessage);
    resetButton.addEventListener('click', resetChat);
    
    // Add click handlers to suggestion chips
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            userInput.value = chip.textContent;
            sendMessage(new Event('submit'));
        });
    });
    
    // Auto-scroll to bottom of chat when new messages are added
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Add a message to the chat
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'assistant-message');
        
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        
        // Handle markdown-like formatting for bulletpoints and links
        let formattedContent = content;
        
        // Convert URLs to clickable links
        formattedContent = formattedContent.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Convert * list items to HTML list
        if (formattedContent.includes('\n* ')) {
            const parts = formattedContent.split('\n* ');
            const mainText = parts[0];
            const listItems = parts.slice(1);
            
            formattedContent = mainText + '<ul>';
            listItems.forEach(item => {
                formattedContent += `<li>${item}</li>`;
            });
            formattedContent += '</ul>';
        }
        
        messageContent.innerHTML = formattedContent;
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Display typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('message', 'assistant-message', 'typing-indicator-container');
        typingDiv.innerHTML = `
            <div class="message-content typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        typingDiv.id = 'typing-indicator';
        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }
    
    // Remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Send user message to server
    function sendMessage(event) {
        event.preventDefault();
        
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input
        userInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send message to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove typing indicator
            removeTypingIndicator();
            
            // Add AI response to chat
            addMessage(data.response);
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage('Sorry, I encountered an error while processing your request. Please try again.');
        });
    }
    
    // Reset the chat
    function resetChat() {
        // Confirm before resetting
        if (confirm('Are you sure you want to reset the chat? This will clear your conversation history.')) {
            // Clear chat UI
            while (chatMessages.children.length > 1) {
                chatMessages.removeChild(chatMessages.lastChild);
            }
            
            // Reset chat on server
            fetch('/api/reset-chat', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                console.log('Chat reset:', data);
            })
            .catch(error => {
                console.error('Error resetting chat:', error);
            });
        }
    }
    
    // Initialize by scrolling to bottom
    scrollToBottom();
});
