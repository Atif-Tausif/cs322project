/**
 * Chat Widget JavaScript
 * Handles AI customer service chat functionality
 */

$(document).ready(function() {
    const chatToggle = $('#chatToggle');
    const chatWidget = $('#chatWidget');
    const chatClose = $('#chatClose');
    const chatInput = $('#chatInput');
    const chatSend = $('#chatSend');
    const chatBody = $('#chatBody');
    
    // Toggle chat widget
    chatToggle.on('click', function() {
        chatWidget.toggleClass('active');
        if (chatWidget.hasClass('active')) {
            chatInput.focus();
        }
    });
    
    // Close chat widget
    chatClose.on('click', function() {
        chatWidget.removeClass('active');
    });
    
    // Send message on button click
    chatSend.on('click', function() {
        sendMessage();
    });
    
    // Send message on Enter key
    chatInput.on('keypress', function(e) {
        if (e.which === 13) {
            sendMessage();
        }
    });
    
    /**
     * Send chat message to AI
     */
    function sendMessage() {
        const message = chatInput.val().trim();
        
        if (message === '') {
            return;
        }
        
        // Display user message
        appendMessage(message, 'user');
        
        // Clear input
        chatInput.val('');
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send to backend
        $.ajax({
            url: '/api/v1/chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ message: message }),
            success: function(response) {
                removeTypingIndicator();
                if (response.success) {
                    appendMessage(response.reply, 'bot');
                    
                    // If response is from knowledge base, show rating option
                    if (response.source === 'knowledge_base') {
                        appendRatingWidget(response.entry_id);
                    }
                } else {
                    appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
                }
            },
            error: function() {
                removeTypingIndicator();
                appendMessage('Sorry, I\'m having trouble connecting. Please try again later.', 'bot');
            }
        });
    }
    
    /**
     * Append message to chat body
     */
    function appendMessage(text, sender) {
        const messageDiv = $('<div>')
            .addClass('chat-message')
            .addClass(sender);
        
        const contentDiv = $('<div>')
            .addClass('message-content')
            .text(text);
        
        messageDiv.append(contentDiv);
        chatBody.append(messageDiv);
        
        // Scroll to bottom
        chatBody.scrollTop(chatBody[0].scrollHeight);
    }
    
    /**
     * Show typing indicator
     */
    function showTypingIndicator() {
        const typingDiv = $('<div>')
            .addClass('chat-message bot typing-indicator')
            .html('<div class="message-content"><i class="fas fa-circle"></i> <i class="fas fa-circle"></i> <i class="fas fa-circle"></i></div>');
        
        chatBody.append(typingDiv);
        chatBody.scrollTop(chatBody[0].scrollHeight);
    }
    
    /**
     * Remove typing indicator
     */
    function removeTypingIndicator() {
        $('.typing-indicator').remove();
    }
    
    /**
     * Append rating widget for knowledge base answers
     */
    function appendRatingWidget(entryId) {
        const ratingDiv = $('<div>')
            .addClass('chat-message bot')
            .html(`
                <div class="message-content">
                    <small class="text-muted">Was this answer helpful?</small>
                    <div class="rating-widget mt-2" data-entry-id="${entryId}">
                        <button class="btn btn-sm btn-success rate-btn" data-rating="5">
                            <i class="fas fa-thumbs-up"></i> Yes
                        </button>
                        <button class="btn btn-sm btn-warning rate-btn" data-rating="3">
                            <i class="fas fa-meh"></i> Somewhat
                        </button>
                        <button class="btn btn-sm btn-danger rate-btn" data-rating="0">
                            <i class="fas fa-thumbs-down"></i> No
                        </button>
                    </div>
                </div>
            `);
        
        chatBody.append(ratingDiv);
        chatBody.scrollTop(chatBody[0].scrollHeight);
        
        // Handle rating clicks
        ratingDiv.find('.rate-btn').on('click', function() {
            const rating = $(this).data('rating');
            rateKnowledgeEntry(entryId, rating);
            ratingDiv.find('.rating-widget').html('<small class="text-success">Thank you for your feedback!</small>');
        });
    }
    
    /**
     * Rate a knowledge base entry
     */
    function rateKnowledgeEntry(entryId, rating) {
        $.ajax({
            url: '/api/v1/knowledge/rate',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                entry_id: entryId,
                rating: rating
            }),
            success: function(response) {
                console.log('Rating submitted successfully');
            },
            error: function() {
                console.error('Failed to submit rating');
            }
        });
    }
});

/* Typing indicator animation */
const style = document.createElement('style');
style.textContent = `
    .typing-indicator .fa-circle {
        animation: typing 1.4s infinite;
        font-size: 0.5rem;
        opacity: 0.4;
    }
    .typing-indicator .fa-circle:nth-child(2) {
        animation-delay: 0.2s;
    }
    .typing-indicator .fa-circle:nth-child(3) {
        animation-delay: 0.4s;
    }
    @keyframes typing {
        0%, 60%, 100% { opacity: 0.4; }
        30% { opacity: 1; }
    }
`;
document.head.appendChild(style);