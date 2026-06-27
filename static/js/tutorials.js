let currentFilters = {
    category: 'all',
    difficulty: null,
    topic: null,
    search: ''
};

let currentPage = 0;
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

    const urlParams = new URLSearchParams(window.location.search);
    currentFilters.category = urlParams.get('category') || 'all';
    currentFilters.difficulty = urlParams.get('difficulty');
    currentFilters.topic = urlParams.get('topic');
    currentFilters.search = urlParams.get('search') || '';

    updateActiveTab(currentFilters.category);
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = currentFilters.search;
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchTutorials();
            }
        });
    }

    const searchButton = document.querySelector('.input-group .btn-primary');
    if (searchButton) {
        searchButton.addEventListener('click', function(e) {
            e.preventDefault();
            searchTutorials();
        });
    }
    
    loadTutorials();
    loadFeaturedTutorial();
    loadTutorialStats();
});

function filterTutorials(category) {
    currentFilters.category = category;
    currentPage = 0;

    const url = new URL(window.location);
    if (category && category !== 'all') {
        url.searchParams.set('category', category);
    } else {
        url.searchParams.delete('category');
    }
    window.history.pushState({}, '', url);
    updateActiveTab();
    loadTutorials();
}

function searchTutorials() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        const searchTerm = searchInput.value.trim();
        currentFilters.search = searchTerm;
        currentFilters.category = 'all'; // Reset category when searching
        currentPage = 0;
        
        // Update URL params
        const url = new URL(window.location);
        if (searchTerm) {
            url.searchParams.set('search', searchTerm);
        } else {
            url.searchParams.delete('search');
        }
        url.searchParams.delete('category'); // Remove category filter
        window.history.pushState({}, '', url);
        
        // Update active tab to "All"
        updateActiveTab('all');
        
        loadTutorials();
    }
}

function updateActiveTab(category) {
    document.querySelectorAll('[data-category]').forEach(el => {
        const elCategory = el.dataset.category;
        if (elCategory === category) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
}

async function loadTutorials(page = 0) {
    currentPage = page;

    let url = `/api/v1/tutorials?limit=12&offset=${page * 12}`;
    if (!currentFilters.search && currentFilters.category && currentFilters.category !== 'all') {
        url += `&category=${encodeURIComponent(currentFilters.category)}`;
    }
    if (currentFilters.difficulty) {
        url += `&difficulty=${encodeURIComponent(currentFilters.difficulty)}`;
    }
    if (currentFilters.topic) {
        url += `&topic=${encodeURIComponent(currentFilters.topic)}`;
    }
    if (currentFilters.search) {
        url += `&search=${encodeURIComponent(currentFilters.search)}`;
    }
    
    console.log('Fetching tutorials with URL:', url);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        console.log('Received tutorials:', data);
        
        const tutorials = Array.isArray(data) ? data : (data.tutorials || []);
        const total = Array.isArray(data) ? tutorials.length : (data.total || tutorials.length);
        
        displayTutorials(tutorials);
        updatePagination(total, page);
    } catch (error) {
        console.error('Error loading tutorials:', error);
        displayTutorials([]);
    }
}

function displayTutorials(tutorials) {
    const grid = document.getElementById('tutorialsGrid');
    
    if (!grid) return;
    
    if (!tutorials || tutorials.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-book-open fa-4x text-muted mb-3"></i>
                <h5>No tutorials found</h5>
                <p class="text-muted">Check back later for new tutorials!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    tutorials.forEach(tutorial => {
        const thumbnail = tutorial.thumbnail_url || 'https://images.unsplash.com/photo-1526379095098-400a3a1c9e9b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80';
        const difficultyClass = {
            'beginner': 'success',
            'intermediate': 'warning',
            'advanced': 'danger'
        }[tutorial.difficulty] || 'primary';
        
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 border-0 shadow-sm hover-lift">
                    <div class="position-relative">
                        <img src="${escapeHtml(thumbnail)}" class="card-img-top" alt="${escapeHtml(tutorial.title)}" style="height: 180px; object-fit: cover;" loading="lazy">
                        <span class="position-absolute top-0 end-0 m-3 badge bg-success">Free</span>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <span class="badge bg-primary">${escapeHtml(tutorial.topic || 'General')}</span>
                            <small class="text-muted"><i class="fas fa-clock me-1"></i>${tutorial.duration || '?'} min</small>
                        </div>
                        <h5 class="card-title fw-bold">${escapeHtml(tutorial.title)}</h5>
                        <p class="card-text text-muted small">${escapeHtml(tutorial.description || '').substring(0, 100)}${tutorial.description && tutorial.description.length > 100 ? '...' : ''}</p>
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas fa-signal text-${difficultyClass} me-2"></i>
                            <small class="text-muted">${tutorial.difficulty ? tutorial.difficulty.charAt(0).toUpperCase() + tutorial.difficulty.slice(1) : 'Beginner'}</small>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted"><i class="fas fa-users me-1"></i>${tutorial.view_count || 0} views</small>
                            <a href="/tutorials/${tutorial.id}" class="btn btn-sm btn-outline-primary">Start</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
}

async function loadFeaturedTutorial() {
    try {
        const response = await fetch('/api/v1/tutorials/featured');
        const tutorial = await response.json();
        
        if (tutorial && tutorial.id) {
            displayFeaturedTutorial(tutorial);
        }
    } catch (error) {
        console.error('Error loading featured tutorial:', error);
    }
}

function displayFeaturedTutorial(tutorial) {
    const container = document.getElementById('featuredTutorial');
    if (!container) return;
    
    container.innerHTML = `
        <div class="card bg-primary text-white border-0">
            <div class="card-body p-5">
                <div class="row align-items-center">
                    <div class="col-lg-8">
                        <h2 class="display-6 fw-bold mb-3">${escapeHtml(tutorial.title)}</h2>
                        <p class="lead mb-4">${escapeHtml(tutorial.description || '')}</p>
                        <div class="d-flex flex-wrap gap-3 mb-3">
                            <span><i class="fas fa-clock me-2"></i>${tutorial.duration || '?'} min</span>
                            <span><i class="fas fa-signal me-2"></i>${tutorial.difficulty ? tutorial.difficulty.charAt(0).toUpperCase() + tutorial.difficulty.slice(1) : 'Beginner'}</span>
                            <span><i class="fas fa-video me-2"></i>${tutorial.video_url ? 'Video' : 'Tutorial'}</span>
                        </div>
                        <a href="/tutorials/${tutorial.id}" class="btn btn-light btn-lg">
                            <i class="fas fa-play-circle me-2"></i>Start Learning
                        </a>
                    </div>
                    <div class="col-lg-4 text-center d-none d-lg-block">
                        <i class="fas fa-code fa-6x opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadTutorialStats() {
    try {
        const response = await fetch('/api/v1/tutorials/stats');
        const stats = await response.json();
        displayTutorialStats(stats);
    } catch (error) {
        console.error('Error loading tutorial stats:', error);
    }
}

function displayTutorialStats(stats) {
    const container = document.getElementById('tutorialStats');
    if (!container) return;
    
    container.innerHTML = `
        <div class="col-12">
            <h3 class="fw-bold mb-4">Tutorials by Difficulty</h3>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card border-0 shadow-sm bg-success bg-opacity-10 h-100">
                <div class="card-body text-center p-4">
                    <i class="fas fa-seedling fa-3x text-success mb-3"></i>
                    <h4 class="fw-bold">Beginner</h4>
                    <p class="text-muted">${stats.beginner || 0} tutorials</p>
                    <button class="btn btn-outline-success" onclick="filterByDifficulty('beginner')">Browse</button>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card border-0 shadow-sm bg-warning bg-opacity-10 h-100">
                <div class="card-body text-center p-4">
                    <i class="fas fa-tree fa-3x text-warning mb-3"></i>
                    <h4 class="fw-bold">Intermediate</h4>
                    <p class="text-muted">${stats.intermediate || 0} tutorials</p>
                    <button class="btn btn-outline-warning" onclick="filterByDifficulty('intermediate')">Browse</button>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card border-0 shadow-sm bg-danger bg-opacity-10 h-100">
                <div class="card-body text-center p-4">
                    <i class="fas fa-crown fa-3x text-danger mb-3"></i>
                    <h4 class="fw-bold">Advanced</h4>
                    <p class="text-muted">${stats.advanced || 0} tutorials</p>
                    <button class="btn btn-outline-danger" onclick="filterByDifficulty('advanced')">Browse</button>
                </div>
            </div>
        </div>
    `;
}

function filterByDifficulty(difficulty) {
    currentFilters.difficulty = difficulty;
    currentFilters.category = 'all';
    currentPage = 0;

    const url = new URL(window.location);
    url.searchParams.set('difficulty', difficulty);
    url.searchParams.delete('category');
    window.history.pushState({}, '', url);

    updateActiveTab();
    loadTutorials();
}

function updatePagination(total, currentPage) {
    const container = document.getElementById('pagination');
    if (!container) return;
    
    const totalPages = Math.ceil(total / 12);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<nav aria-label="Tutorial pagination"><ul class="pagination justify-content-center">';
    
    // Previous button
    html += `
        <li class="page-item ${currentPage === 0 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadTutorials(${currentPage - 1}); return false;" aria-label="Previous">
                <span aria-hidden="true"><i class="fas fa-chevron-left"></i></span>
            </a>
        </li>
    `;
    
    // Page numbers
    for (let i = 0; i < totalPages; i++) {
        if (i === 0 || i === totalPages - 1 || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="loadTutorials(${i}); return false;">${i + 1}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages - 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadTutorials(${currentPage + 1}); return false;" aria-label="Next">
                <span aria-hidden="true"><i class="fas fa-chevron-right"></i></span>
            </a>
        </li>
    `;
    
    html += '</ul></nav>';
    container.innerHTML = html;
}

function showUploadModal() {
    const modal = document.getElementById('uploadModal');
    if (modal) {
        document.getElementById('uploadForm')?.reset();
        new bootstrap.Modal(modal).show();
    }
}

async function uploadTutorial() {
    const title = document.getElementById('tutorialTitle')?.value;
    const description = document.getElementById('tutorialDescription')?.value;
    const category = document.getElementById('tutorialCategory')?.value;
    const difficulty = document.getElementById('tutorialDifficulty')?.value;
    const topic = document.getElementById('tutorialTopic')?.value;
    const duration = document.getElementById('tutorialDuration')?.value;
    const file = document.getElementById('tutorialFile')?.files[0];
    const videoUrl = document.getElementById('tutorialVideoUrl')?.value;
    const thumbnail = document.getElementById('tutorialThumbnail')?.files[0];
    
    if (!title || !category || !difficulty || !topic) {
        showError('Please fill in all required fields');
        return;
    }
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description || '');
    formData.append('category', category);
    formData.append('difficulty', difficulty);
    formData.append('topic', topic);
    formData.append('duration', duration || '30');
    
    if (file) {
        formData.append('file', file);
    }
    if (videoUrl) {
        formData.append('video_url', videoUrl);
    }
    if (thumbnail) {
        formData.append('thumbnail', thumbnail);
    }
    
    const btn = document.querySelector('#uploadModal .btn-primary');
    const spinner = document.getElementById('uploadSpinner');
    const btnText = btn?.querySelector('span:last-child');
    
    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');
    if (btnText) btnText.textContent = 'Uploading...';
    
    try {
        const response = await fetch('/api/v1/tutorials', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
            if (modal) modal.hide();
            showSuccess('Tutorial uploaded successfully!');
            loadTutorials();
            loadFeaturedTutorial();
            loadTutorialStats();
        } else {
            const error = await response.json();
            showError(error.detail || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showError('An error occurred');
    } finally {
        if (btn) btn.disabled = false;
        if (spinner) spinner.classList.add('d-none');
        if (btnText) btnText.textContent = 'Upload';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    const successModal = document.getElementById('successModal');
    const successMessage = document.getElementById('successMessage');
    if (successMessage) successMessage.textContent = message;
    if (successModal) new bootstrap.Modal(successModal).show();
}

function showError(message) {
    const errorModal = document.getElementById('errorModal');
    const errorMessage = document.getElementById('errorMessage');
    if (errorMessage) errorMessage.textContent = message;
    if (errorModal) new bootstrap.Modal(errorModal).show();
}

window.filterTutorials = filterTutorials;
window.searchTutorials = searchTutorials;
window.showUploadModal = showUploadModal;
window.uploadTutorial = uploadTutorial;
window.filterByDifficulty = filterByDifficulty;