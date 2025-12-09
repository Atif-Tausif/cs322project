/**
 * Date formatting utilities
 * Formats ISO date strings to MM/DD/YYYY format and removes seconds
 */

(function() {
    /**
     * Format ISO date string to MM/DD/YYYY
     */
    function formatDate(dateString) {
        if (!dateString) return '';
        
        // Handle ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            // Try to parse manually if Date constructor fails
            const parts = dateString.substring(0, 10).split('-');
            if (parts.length === 3) {
                return `${parts[1]}/${parts[2]}/${parts[0]}`;
            }
            return dateString;
        }
        
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const year = date.getFullYear();
        
        return `${month}/${day}/${year}`;
    }
    
    /**
     * Format datetime string to MM/DD/YYYY HH:MM (no seconds)
     */
    function formatDateTime(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            // Try manual parsing
            const isoMatch = dateString.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
            if (isoMatch) {
                return `${isoMatch[2]}/${isoMatch[3]}/${isoMatch[1]} ${isoMatch[4]}:${isoMatch[5]}`;
            }
            return dateString;
        }
        
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${month}/${day}/${year} ${hours}:${minutes}`;
    }
    
    /**
     * Format all dates on page load
     */
    function formatAllDates() {
        // Find all elements with data-date or data-datetime attributes
        document.querySelectorAll('[data-date]').forEach(function(el) {
            el.textContent = formatDate(el.getAttribute('data-date'));
        });
        
        document.querySelectorAll('[data-datetime]').forEach(function(el) {
            el.textContent = formatDateTime(el.getAttribute('data-datetime'));
        });
        
        // Also format common date patterns in text content
        // Look for ISO date patterns in text nodes and replace them
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            // Skip script and style tags
            const parent = node.parentNode;
            if (parent && (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE')) {
                continue;
            }
            
            // Check for ISO date pattern: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD
            if (node.textContent.match(/\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?/)) {
                textNodes.push(node);
            }
        }
        
        textNodes.forEach(function(textNode) {
            const originalText = textNode.textContent;
            // Replace ISO datetime format
            let newText = originalText.replace(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/g, function(match, year, month, day, hour, minute) {
                return `${month}/${day}/${year} ${hour}:${minute}`;
            });
            // Replace ISO date format
            newText = newText.replace(/(\d{4})-(\d{2})-(\d{2})(?!T)/g, function(match, year, month, day) {
                return `${month}/${day}/${year}`;
            });
            
            if (newText !== originalText) {
                textNode.textContent = newText;
            }
        });
    }
    
    // Run on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', formatAllDates);
    } else {
        formatAllDates();
    }
    
    // Make functions available globally
    window.formatDate = formatDate;
    window.formatDateTime = formatDateTime;
})();
