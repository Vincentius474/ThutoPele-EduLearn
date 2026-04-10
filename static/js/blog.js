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

async function deletePost(postId) {
    if (!confirm('Are you sure you want to delete this post? This action cannot be undone.')) return;
    
    try {
        const response = await fetch(`/api/v1/blog/${postId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Post deleted successfully');
            location.reload();
        } else {
            alert('Failed to delete post');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}