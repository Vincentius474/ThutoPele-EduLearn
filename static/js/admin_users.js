// admin_users.js - User Management Functionality

// ==================== TABLE FILTERING ====================

function filterTable() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const role = document.getElementById('roleFilter').value;
    const status = document.getElementById('statusFilter').value;
    
    const rows = document.querySelectorAll('#usersTableBody tr');
    
    rows.forEach(row => {
        let show = true;
        
        if (search) {
            const text = row.textContent.toLowerCase();
            show = text.includes(search);
        }
        
        if (show && role) {
            const roleSelect = row.querySelector('.role-select');
            if (roleSelect) {
                const roleValue = roleSelect.value;
                show = roleValue === role;
            }
        }
        
        if (show && status) {
            const statusCheck = row.querySelector('.status-toggle');
            if (statusCheck) {
                const isActive = statusCheck.checked;
                show = (status === 'active' && isActive) || (status === 'inactive' && !isActive);
            }
        }
        
        row.style.display = show ? '' : 'none';
    });
}

// ==================== USER ROLE MANAGEMENT ====================

async function updateUserRole(userId, role) {
    console.log('Updating user role:', userId, role);
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/role`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: role })
        });
        
        const data = await response.json();
        console.log('Response:', data);
        
        if (response.ok) {
            showToast(data.message || 'User role updated successfully', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.detail || 'Failed to update user role', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('An error occurred', 'error');
    }
}

// ==================== USER STATUS MANAGEMENT ====================

async function toggleUserStatus(userId, isActive) {
    console.log('Toggling user status:', userId, isActive);
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: isActive })
        });
        
        const data = await response.json();
        console.log('Response:', data);
        
        if (response.ok) {
            showToast(data.message || 'User status updated successfully', 'success');
        } else {
            showToast(data.detail || 'Failed to update user status', 'error');
            // Revert the toggle
            const toggle = document.querySelector(`.status-toggle[data-user-id="${userId}"]`);
            if (toggle) toggle.checked = !isActive;
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('An error occurred', 'error');
        // Revert the toggle
        const toggle = document.querySelector(`.status-toggle[data-user-id="${userId}"]`);
        if (toggle) toggle.checked = !isActive;
    }
}

// ==================== USER EDITING ====================

async function editUser(userId) {
    console.log('Editing user:', userId);
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch user details');
        }
        
        const user = await response.json();
        console.log('User data:', user);
        
        // Populate modal fields
        document.getElementById('editUserId').value = user.id;
        document.getElementById('editFullName').value = user.full_name || '';
        document.getElementById('editUsername').value = user.username || '';
        document.getElementById('editEmail').value = user.email || '';
        document.getElementById('editBio').value = user.bio || '';
        document.getElementById('editAvatarUrl').value = user.avatar_url || '';
        document.getElementById('editExpertise').value = user.expertise || '';
        document.getElementById('editExperience').value = user.experience || '';
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error fetching user:', error);
        showToast('Failed to load user details', 'error');
    }
}

async function saveUserEdit() {
    const userId = document.getElementById('editUserId').value;
    const formData = {
        full_name: document.getElementById('editFullName').value,
        username: document.getElementById('editUsername').value,
        bio: document.getElementById('editBio').value,
        avatar_url: document.getElementById('editAvatarUrl').value,
        expertise: document.getElementById('editExpertise').value,
        experience: document.getElementById('editExperience').value
    };
    
    console.log('Saving user data:', formData);
    
    // Validate required fields
    if (!formData.full_name || !formData.username) {
        showToast('Full name and username are required', 'error');
        return;
    }
    
    const saveBtn = document.querySelector('#editUserModal .btn-primary');
    const spinner = document.getElementById('editUserSpinner');
    const btnText = saveBtn.querySelector('span:last-child');
    
    // Show loading state
    saveBtn.disabled = true;
    spinner.classList.remove('d-none');
    btnText.textContent = 'Saving...';
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        console.log('Save response:', data);
        
        if (response.ok) {
            showToast(data.message || 'User updated successfully', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
            modal.hide();
            
            // Reload the page to show updated data
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.detail || 'Failed to update user', 'error');
        }
    } catch (error) {
        console.error('Error updating user:', error);
        showToast('An error occurred', 'error');
    } finally {
        // Reset button state
        saveBtn.disabled = false;
        spinner.classList.add('d-none');
        btnText.textContent = 'Save Changes';
    }
}

// ==================== USER DELETION ====================

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('User deleted successfully', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to delete user', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('An error occurred', 'error');
    }
}

// ==================== EXPORT FUNCTIONALITY ====================

function exportUsers() {
    window.location.href = '/api/v1/admin/users/export';
}

// ==================== TOAST NOTIFICATION ====================

function showToast(message, type) {
    // Remove existing toast
    const existingToast = document.querySelector('.admin-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `admin-toast alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed top-0 end-0 m-3 shadow`;
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.style.animation = 'slideIn 0.3s ease';
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close ms-3" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        if (toast) {
            toast.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 3000);
}

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin users page loaded');
    
    // Add event listeners for filters
    const searchInput = document.getElementById('searchInput');
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    if (searchInput) searchInput.addEventListener('input', filterTable);
    if (roleFilter) roleFilter.addEventListener('change', filterTable);
    if (statusFilter) statusFilter.addEventListener('change', filterTable);
    
    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes fadeOut {
            to {
                opacity: 0;
                transform: translateX(100%);
            }
        }
        .status-toggle {
            cursor: pointer;
        }
        .role-select {
            cursor: pointer;
        }
    `;
    document.head.appendChild(style);
});