// blog_detail.js - Blog detail page functionality

document.addEventListener('DOMContentLoaded', function() {
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', handleCommentSubmit);
    }
});

async function handleCommentSubmit(e) {
    e.preventDefault();
    
    const content = document.getElementById('commentContent').value;
    if (!content.trim()) {
        showNotification('Please enter a comment', 'error');
        return;
    }
    
    const postId = e.target.dataset.postId;
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Posting...';
    
    try {
        const response = await fetch(`/api/v1/blog/${postId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Comment submitted for approval!', 'success');
            document.getElementById('commentContent').value = '';
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification(data.detail || 'Failed to post comment', 'error');
        }
    } catch (error) {
        console.error('Error posting comment:', error);
        showNotification('An error occurred', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function showNotification(message, type) {
    // You can implement a toast notification here
    // For now, using alert
    alert(message);
}