// blog.js - Blog page functionality

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Blog page loaded');
    
    // Newsletter form
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Thank you for subscribing! Check your email for confirmation.');
            newsletterForm.reset();
        });
    }
    
    // Also attach delete handlers to buttons directly
    const deleteButtons = document.querySelectorAll('.delete-post-btn');
    console.log('Found delete buttons:', deleteButtons.length);
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const postId = this.getAttribute('data-id');
            if (postId) {
                deletePostFunction(postId);
            }
        });
    });
});

// Define the delete function
async function deletePostFunction(postId) {
    console.log('deletePostFunction called with ID:', postId);
    
    if (!confirm('Are you sure you want to delete this post? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/blog/${postId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            alert('Post deleted successfully!');
            window.location.href = '/blog';
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to delete post');
        }
    } catch (error) {
        console.error('Error deleting post:', error);
        alert('An error occurred');
    }
}

// Expose to global scope
window.deletePost = deletePostFunction;

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
