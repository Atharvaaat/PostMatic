document.addEventListener('DOMContentLoaded', function() {
    // Get event ID from URL query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('id');
    
    if (!eventId) {
        window.location.href = 'index.html';
        return;
    }
    
    // Initialize chat history
    window.chatHistory = [];
    
    // Load event data
    loadEventData(eventId);
    
    // Initialize chat form submission
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', function(event) {
        event.preventDefault();
        handleChatSubmit(eventId);
    });
    
    // Initialize generate post button
    const generateButton = document.getElementById('generate-post');
    generateButton.addEventListener('click', function() {
        generatePost(eventId);
    });
    
    // Initialize copy button
    const copyButton = document.getElementById('copy-post');
    copyButton.addEventListener('click', copyPostToClipboard);
});

async function loadEventData(eventId) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/events/${eventId}`);
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const event = await response.json();
        
        document.getElementById('event-title').textContent = event.metadata.topic;
        document.getElementById('event-description').textContent = event.metadata.description;
        
        const eventDate = new Date(event.metadata.date);
        const formattedDate = eventDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        document.getElementById('event-date').textContent = formattedDate;
        
        checkForExistingPost(eventId);
    } catch (error) {
        console.error('Error loading event data:', error);
        alert('Error loading event data. Please try again.');
        window.location.href = 'index.html';
    }
}

async function checkForExistingPost(eventId) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/events/${eventId}`);
        
        if (!response.ok) {
            return;
        }
        
        const event = await response.json();
        
        if (event.generated_post) {
            updatePostContent(event.generated_post);
            addChatMessage({
                role: 'system',
                content: 'Previous post loaded. You can generate a new one or ask me to make changes.'
            });
        }
    } catch (error) {
        console.error('Error checking for existing post:', error);
    }
}

async function generatePost(eventId) {
    const generateButton = document.getElementById('generate-post');
    const originalText = generateButton.innerHTML;
    
    try {
        // Disable button and show loading state
        generateButton.disabled = true;
        generateButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        
        // Add generating message to chat
        addChatMessage({
            role: 'system',
            content: 'Generating LinkedIn post from your event data...'
        });
        
        // Make API request
        const response = await fetch(`${CONFIG.API_URL}/events/generate-post`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ event_id: eventId })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        // Debug: Log the response from the server
        console.log("Server response:", data);
        
        // Update post content in the preview
        if (data.content) {
            updatePostContent(data.content);
            
            // Add success message to chat
            addChatMessage({
                role: 'assistant',
                content: 'I\'ve created a LinkedIn post based on your event. Ask me to make any specific changes.'
            });
            
            // Update chat history
            window.chatHistory.push({
                role: 'assistant',
                content: 'I\'ve created a LinkedIn post based on your event. Ask me to make any specific changes.'
            });
        } else {
            throw new Error('No content received from server');
        }
    } catch (error) {
        console.error('Error generating post:', error);
        addChatMessage({
            role: 'system',
            content: 'Error generating post. Please try again.'
        });
    } finally {
        // Reset button state
        generateButton.disabled = false;
        generateButton.innerHTML = originalText;
    }
}

async function handleChatSubmit(eventId) {
    const chatInput = document.getElementById('chat-input');
    const userMessage = chatInput.value.trim();
    
    if (!userMessage) return;
    
    addChatMessage({
        role: 'user',
        content: userMessage
    });
    
    window.chatHistory.push({
        role: 'user',
        content: userMessage
    });
    
    chatInput.value = '';
    
    const messageId = Date.now();
    addChatMessage({
        role: 'assistant',
        content: '<i class="fas fa-spinner fa-spin"></i> Thinking...',
        id: messageId
    });
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/events/edit-post`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                event_id: eventId,
                messages: window.chatHistory
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        
        updatePostContent(data.content);
        
        updateChatMessage(messageId, {
            role: 'assistant',
            content: 'I\'ve updated your LinkedIn post based on your feedback.'
        });
        
        window.chatHistory.push({
            role: 'assistant',
            content: 'I\'ve updated your LinkedIn post based on your feedback.'
        });
    } catch (error) {
        console.error('Error editing post:', error);
        updateChatMessage(messageId, {
            role: 'assistant',
            content: 'Sorry, I encountered an error while updating your post. Please try again.'
        });
        
        window.chatHistory.push({
            role: 'assistant',
            content: 'Sorry, I encountered an error while updating your post. Please try again.'
        });
    }
}

function addChatMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    
    if (message.role === 'user') {
        messageElement.className = 'message user-message';
    } else if (message.role === 'assistant') {
        messageElement.className = 'message assistant-message';
    } else if (message.role === 'system') {
        messageElement.className = 'system-message';
    }
    
    messageElement.innerHTML = message.content;
    
    if (message.id) {
        messageElement.id = `message-${message.id}`;
    }
    
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateChatMessage(messageId, message) {
    const messageElement = document.getElementById(`message-${messageId}`);
    
    if (!messageElement) return;
    
    messageElement.innerHTML = message.content;
    
    if (message.role === 'user') {
        messageElement.className = 'message user-message';
    } else if (message.role === 'assistant') {
        messageElement.className = 'message assistant-message';
    } else if (message.role === 'system') {
        messageElement.className = 'system-message';
    }
}

function updatePostContent(content) {
    const postContent = document.getElementById('post-content');
    if (!postContent) {
        console.error('Post content element not found');
        return;
    }
    
    // Clear existing content
    postContent.innerHTML = '';
    
    // Create an editable div with markdown rendering
    const editorDiv = document.createElement('div');
    editorDiv.className = 'markdown-editor';
    editorDiv.contentEditable = true;
    editorDiv.style.whiteSpace = 'pre-wrap';
    editorDiv.style.wordBreak = 'break-word';
    editorDiv.style.minHeight = '200px';
    editorDiv.style.padding = '10px';
    editorDiv.style.border = '1px solid #ced4da';
    editorDiv.style.borderRadius = '4px';
    editorDiv.style.outline = 'none';
    
    // Set the initial content (with markdown rendered)
    editorDiv.innerHTML = marked.parse(content);
    
    // Keep track of original content for comparison
    editorDiv.setAttribute('data-original', content);
    
    // Add event listener to capture changes
    editorDiv.addEventListener('input', function() {
        // Save the current text to localStorage
        try {
            localStorage.setItem('currentPost', editorDiv.innerText);
        } catch (e) {
            console.error('Error saving to localStorage:', e);
        }
    });

    postContent.appendChild(editorDiv);
}

// Add this function to save edited content back to server
async function saveEditedContent(eventId) {
    const editedContent = document.querySelector('.markdown-editor').innerText;
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/events/save-post`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                event_id: eventId,
                content: editedContent
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        return true;
    } catch (error) {
        console.error('Error saving edited content:', error);
        return false;
    }
}

function copyPostToClipboard() {
    const postContent = document.querySelector('.markdown-editor');
    
    navigator.clipboard.writeText(postContent.innerText)
        .then(() => {
            const copyButton = document.getElementById('copy-post');
            const originalText = copyButton.innerHTML;
            
            copyButton.innerHTML = '<i class="fas fa-check"></i> Copied!';
            
            setTimeout(() => {
                copyButton.innerHTML = originalText;
            }, 2000);
        })
        .catch(error => {
            console.error('Error copying to clipboard:', error);
            alert('Error copying to clipboard. Please try manually selecting and copying the text.');
        });
}