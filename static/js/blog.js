// blog.js - Blog page functionality

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Newsletter form
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Thank you for subscribing! Check your email for confirmation.');
            newsletterForm.reset();
        });
    }
});

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}