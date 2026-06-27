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

function showNotification(message, type) {
    alert(message);
}