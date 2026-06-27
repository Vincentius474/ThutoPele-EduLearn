let currentCategory = 'all';
let currentUser = null;

document.addEventListener('DOMContentLoaded', function() {
    const userData = document.getElementById('user-data');
    if (userData) {
        try {
            currentUser = JSON.parse(userData.textContent);
        } catch (e) {
            console.error('Error parsing user data:', e);
        }
    }
    
    loadResources();
    loadPopularResources();
});

function filterResources(category) {
    currentCategory = category;
    document.querySelectorAll('[data-category]').forEach(el => {
        if (el.dataset.category === category) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
    
    loadResources();
}

async function loadResources() {
    const url = currentCategory === 'all' 
        ? '/api/v1/resources' 
        : `/api/v1/resources?category=${currentCategory}`;
    
    try {
        const response = await fetch(url);
        const resources = await response.json();
        displayResources(resources);
    } catch (error) {
        console.error('Error loading resources:', error);
    }
}

function displayResources(resources) {
    const grid = document.getElementById('resourcesGrid');
    
    if (!resources || resources.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-folder-open fa-4x text-muted mb-3"></i>
                <h5>No resources found</h5>
                <p class="text-muted">Check back later for new resources!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    resources.forEach(resource => {
        const icon = getResourceIcon(resource.file_type, resource.category);
        const size = formatFileSize(resource.file_size);
        
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 border-0 shadow-sm hover-lift">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="resource-icon bg-primary bg-opacity-10 p-3 rounded-3 me-3">
                                <i class="fas ${icon} fa-2x text-primary"></i>
                            </div>
                            <div>
                                <span class="badge bg-success">Free</span>
                                <span class="badge bg-primary ms-2">${getCategoryLabel(resource.category)}</span>
                            </div>
                        </div>
                        <h5 class="card-title fw-bold">${escapeHtml(resource.title)}</h5>
                        <p class="card-text text-muted small">${escapeHtml(resource.description) || 'No description'}</p>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <small class="text-muted"><i class="fas fa-download me-1"></i>${resource.download_count || 0} downloads</small>
                            <small class="text-muted"><i class="fas ${getFileIcon(resource.file_type)} me-1"></i>${size}</small>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-primary flex-grow-1" onclick="downloadResource('${resource.id}')">
                                <i class="fas fa-download me-2"></i>Download
                            </button>
                            ${currentUser && (currentUser.is_admin || currentUser.is_instructor) ? `
                                <button class="btn btn-outline-danger" onclick="deleteResource('${resource.id}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
}

async function loadPopularResources() {
    try {
        const response = await fetch('/api/v1/resources/popular?limit=4');
        const resources = await response.json();
        displayPopularResources(resources);
    } catch (error) {
        console.error('Error loading popular resources:', error);
    }
}

function displayPopularResources(resources) {
    const container = document.getElementById('popularResources');
    
    if (!resources || resources.length === 0) {
        container.innerHTML = '<div class="col-12 text-center">No popular resources yet</div>';
        return;
    }
    
    let html = '';
    resources.forEach(resource => {
        const icon = getResourceIcon(resource.file_type, resource.category);
        
        html += `
            <div class="col-md-3 col-6">
                <div class="card border-0 shadow-sm text-center h-100" onclick="downloadResource('${resource.id}')" style="cursor: pointer;">
                    <div class="card-body p-3">
                        <i class="fas ${icon} fa-2x text-primary mb-2"></i>
                        <h6 class="small fw-bold">${escapeHtml(resource.title)}</h6>
                        <small class="text-muted">${resource.download_count || 0} downloads</small>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function downloadResource(resourceId) {
    try {
        const response = await fetch(`/api/v1/resources/${resourceId}/download`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            window.open(data.file_url, '_blank');
            setTimeout(() => loadResources(), 500);
        }
    } catch (error) {
        console.error('Error downloading resource:', error);
    }
}

function showUploadModal() {
    document.getElementById('uploadForm').reset();
    new bootstrap.Modal(document.getElementById('uploadModal')).show();
}

async function uploadResource() {
    const title = document.getElementById('resourceTitle').value;
    const description = document.getElementById('resourceDescription').value;
    const category = document.getElementById('resourceCategory').value;
    const file = document.getElementById('resourceFile').files[0];
    
    if (!title || !category || !file) {
        showError('Please fill in all required fields');
        return;
    }
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('category', category);
    formData.append('file', file);
    
    const btn = document.querySelector('#uploadModal .btn-primary');
    const spinner = document.getElementById('uploadSpinner');
    const btnText = btn.querySelector('span:last-child');
    
    btn.disabled = true;
    spinner.classList.remove('d-none');
    btnText.textContent = 'Uploading...';
    
    try {
        const response = await fetch('/api/v1/resources', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
            showSuccess('Resource uploaded successfully!');
            loadResources();
            loadPopularResources();
        } else {
            const error = await response.json();
            showError(error.detail || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showError('An error occurred');
    } finally {
        btn.disabled = false;
        spinner.classList.add('d-none');
        btnText.textContent = 'Upload';
    }
}

async function deleteResource(resourceId) {
    if (!confirm('Are you sure you want to delete this resource?')) return;
    
    try {
        const response = await fetch(`/api/v1/resources/${resourceId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showSuccess('Resource deleted successfully');
            loadResources();
            loadPopularResources();
        } else {
            showError('Failed to delete resource');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showError('An error occurred');
    }
}

function getResourceIcon(fileType, category) {
    if (fileType?.includes('pdf')) return 'fa-file-pdf';
    if (fileType?.includes('word')) return 'fa-file-word';
    if (fileType?.includes('excel')) return 'fa-file-excel';
    if (fileType?.includes('powerpoint')) return 'fa-file-powerpoint';
    if (fileType?.includes('image')) return 'fa-file-image';
    if (fileType?.includes('zip')) return 'fa-file-archive';
    if (fileType?.includes('text')) return 'fa-file-alt';
    
    const categoryIcons = {
        'ebook': 'fa-book',
        'cheatsheet': 'fa-file-alt',
        'template': 'fa-puzzle-piece',
        'tool': 'fa-tools',
        'other': 'fa-folder'
    };
    return categoryIcons[category] || 'fa-file';
}

function getFileIcon(fileType) {
    if (fileType?.includes('pdf')) return 'fa-file-pdf';
    if (fileType?.includes('image')) return 'fa-file-image';
    if (fileType?.includes('zip')) return 'fa-file-archive';
    if (fileType?.includes('text')) return 'fa-file-alt';
    return 'fa-file';
}

function getCategoryLabel(category) {
    const labels = {
        'ebook': 'Ebook',
        'cheatsheet': 'Cheatsheet',
        'template': 'Template',
        'tool': 'Tool',
        'other': 'Other'
    };
    return labels[category] || category;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    document.getElementById('successMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('successModal')).show();
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('errorModal')).show();
}

window.filterResources = filterResources;
window.showUploadModal = showUploadModal;
window.uploadResource = uploadResource;
window.downloadResource = downloadResource;
window.deleteResource = deleteResource;