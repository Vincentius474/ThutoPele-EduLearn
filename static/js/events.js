let currentFilter = 'all';
let currentUser = null;
let calendar = null;
let allEvents = [];

document.addEventListener('DOMContentLoaded', function() {
    console.log('Events page loaded');
    
    checkRequiredLibraries();
    
    const userData = document.getElementById('user-data');
    if (userData) {
        try {
            currentUser = JSON.parse(userData.textContent);
            console.log('Current user:', currentUser);
        } catch (e) {
            console.error('Error parsing user data:', e);
        }
    }
    
    loadEvents();
    loadFeaturedEvent();
    
    initFilters();

    const isVirtualCheckbox = document.getElementById('isVirtual');
    if (isVirtualCheckbox) {
        isVirtualCheckbox.addEventListener('change', function() {
            const meetingLinkField = document.getElementById('meetingLinkField');
            if (meetingLinkField) {
                meetingLinkField.style.display = this.checked ? 'block' : 'none';
            }
        });
    }

    const isFreeCheckbox = document.getElementById('isFree');
    if (isFreeCheckbox) {
        isFreeCheckbox.addEventListener('change', function() {
            const priceField = document.getElementById('priceField');
            if (priceField) {
                priceField.style.display = this.checked ? 'none' : 'block';
            }
            if (this.checked && document.getElementById('price')) {
                document.getElementById('price').value = 0;
            }
        });
    }

    const createEventForm = document.getElementById('createEventForm');
    if (createEventForm) {
        createEventForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createEvent();
        });
    }

    const gridViewBtn = document.getElementById('gridViewBtn');
    const calendarViewBtn = document.getElementById('calendarViewBtn');
    
    if (gridViewBtn) {
        gridViewBtn.addEventListener('click', showGridView);
    }
    if (calendarViewBtn) {
        calendarViewBtn.addEventListener('click', showCalendarView);
    }

    const createEventModal = document.getElementById('createEventModal');
    if (createEventModal) {
        createEventModal.addEventListener('hidden.bs.modal', function() {
            resetCreateEventForm();
        });
    }
});

function checkRequiredLibraries() {
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap JS not loaded - modals will not work');
        showLibraryError('Bootstrap');
    }
    
    if (typeof FullCalendar === 'undefined') {
        console.warn('FullCalendar not loaded - calendar view will be disabled');
        const calendarViewBtn = document.getElementById('calendarViewBtn');
        if (calendarViewBtn) {
            calendarViewBtn.disabled = true;
            calendarViewBtn.title = 'Calendar view requires FullCalendar library';
        }
    }
}

function showLibraryError(library) {
    const eventsGrid = document.getElementById('eventsGrid');
    if (eventsGrid) {
        eventsGrid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-exclamation-triangle fa-4x text-danger mb-3"></i>
                <h5>Configuration Error</h5>
                <p class="text-muted">${library} library is not loaded. Please check your internet connection and refresh the page.</p>
            </div>
        `;
    }
}

function initFilters() {
    const filterButtons = document.querySelectorAll('[data-filter]');
    if (filterButtons.length === 0) return;
    
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            button.classList.add('active');
            
            currentFilter = button.dataset.filter;
            filterEvents();
        });
    });
}

function showGridView() {
    const gridViewBtn = document.getElementById('gridViewBtn');
    const calendarViewBtn = document.getElementById('calendarViewBtn');
    const eventsGrid = document.getElementById('eventsGrid');
    const calendarView = document.getElementById('calendarView');
    const filterSection = document.getElementById('filterSection');
    const calendarLegend = document.getElementById('calendarLegend');
    
    if (gridViewBtn) gridViewBtn.classList.add('active');
    if (calendarViewBtn) calendarViewBtn.classList.remove('active');
    if (eventsGrid) eventsGrid.style.display = 'flex';
    if (calendarView) calendarView.style.display = 'none';
    if (filterSection) filterSection.style.display = 'block';
    if (calendarLegend) calendarLegend.style.display = 'none';
}

async function showCalendarView() {
    const gridViewBtn = document.getElementById('gridViewBtn');
    const calendarViewBtn = document.getElementById('calendarViewBtn');
    const eventsGrid = document.getElementById('eventsGrid');
    const calendarView = document.getElementById('calendarView');
    const filterSection = document.getElementById('filterSection');
    const calendarLegend = document.getElementById('calendarLegend');
    
    if (calendarViewBtn) calendarViewBtn.classList.add('active');
    if (gridViewBtn) gridViewBtn.classList.remove('active');
    if (eventsGrid) eventsGrid.style.display = 'none';
    if (calendarView) calendarView.style.display = 'block';
    if (filterSection) filterSection.style.display = 'none';
    if (calendarLegend) calendarLegend.style.display = 'block';
    
    // Check if FullCalendar is available
    if (typeof FullCalendar === 'undefined') {
        if (calendarView) {
            calendarView.innerHTML = `
                <div class="alert alert-warning text-center">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Calendar view is unavailable. Please refresh the page or try again later.
                </div>
            `;
        }
        return;
    }
    
    // Initialize calendar if not already done
    if (!calendar) {
        if (allEvents.length > 0) {
            initCalendar();
        } else {
            // Wait for events to load if they haven't yet
            if (allEvents.length === 0) {
                await loadEvents();
            }
            if (allEvents.length > 0) {
                initCalendar();
            } else {
                if (calendarView) {
                    calendarView.innerHTML = `
                        <div class="alert alert-info text-center">
                            <i class="fas fa-info-circle me-2"></i>
                            No events to display in calendar.
                        </div>
                    `;
                }
            }
        }
    } else {
        // Refresh calendar events
        calendar.refetchEvents();
    }
}

function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        console.error('Calendar element not found');
        return;
    }
    
    function getEventColor(eventType) {
        const colors = {
            'webinar': '#0d6efd',
            'workshop': '#198754',
            'hackathon': '#dc3545',
            'meetup': '#0dcaf0',
            'other': '#6c757d'
        };
        return colors[eventType] || '#0d6efd';
    }
    
    try {
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            events: allEvents.map(event => ({
                id: event.id,
                title: escapeHtml(event.title),
                start: event.start_date,
                end: event.end_date || event.start_date,
                backgroundColor: getEventColor(event.event_type),
                borderColor: getEventColor(event.event_type),
                textColor: '#ffffff',
                extendedProps: {
                    description: event.description,
                    time: event.start_time ? `${event.start_time} - ${event.end_time || 'TBD'}` : 'TBD',
                    location: event.is_virtual ? 'Virtual Event' : (event.location || 'TBD'),
                    spots_left: event.spots_left,
                    event_type: event.event_type,
                    is_free: event.is_free,
                    price: event.price,
                    id: event.id
                }
            })),
            eventClick: function(info) {
                showEventDetails(info.event);
            },
            dateClick: function(info) {
                console.log('Date clicked:', info.dateStr);
            },
            height: 'auto',
            firstDay: 1,
            locale: 'en',
            eventTimeFormat: {
                hour: '2-digit',
                minute: '2-digit',
                meridiem: 'short'
            },
            loading: function(isLoading) {
                if (isLoading) {
                    console.log('Calendar is loading events...');
                }
            }
        });
        
        calendar.render();
        console.log('Calendar initialized successfully');
    } catch (error) {
        console.error('Error initializing calendar:', error);
        const calendarView = document.getElementById('calendarView');
        if (calendarView) {
            calendarView.innerHTML = `
                <div class="alert alert-danger text-center">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Failed to initialize calendar: ${escapeHtml(error.message)}
                </div>
            `;
        }
    }
}

function showEventDetails(event) {
    if (typeof bootstrap === 'undefined') {
        alert('Modal system unavailable. Please refresh the page.');
        return;
    }
    
    const modalElement = document.getElementById('eventDetailsModal');
    if (!modalElement) {
        console.error('Event details modal element not found');
        alert('Event details view is unavailable');
        return;
    }
    
    const props = event.extendedProps;
    const startDate = new Date(event.start);
    const date = !isNaN(startDate.getTime()) ? startDate.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }) : 'Date TBD';
    
    const modalBody = document.getElementById('eventDetailsBody');
    if (!modalBody) return;
    
    modalBody.innerHTML = `
        <div class="text-center mb-3">
            <span class="badge bg-${getCategoryColor(props.event_type)}">${capitalize(escapeHtml(props.event_type))}</span>
            ${props.is_free ? 
                '<span class="badge bg-success ms-2">Free</span>' : 
                `<span class="badge bg-warning ms-2">R${props.price || 0}</span>`}
        </div>
        <h6 class="fw-bold">${escapeHtml(date)}</h6>
        <p><i class="fas fa-clock me-2 text-primary"></i>${escapeHtml(props.time)}</p>
        <p><i class="fas ${props.location === 'Virtual Event' ? 'fa-globe' : 'fa-map-marker-alt'} me-2 text-primary"></i>${escapeHtml(props.location)}</p>
        <p class="text-muted">${escapeHtml(props.description) || 'No description available'}</p>
        <div class="alert alert-info">
            <i class="fas fa-users me-2"></i>
            ${props.spots_left !== null && props.spots_left !== undefined ? 
                props.spots_left + ' spots available' : 'Unlimited spots'}
        </div>
    `;
    
    const titleElement = document.getElementById('eventDetailsTitle');
    if (titleElement) {
        titleElement.textContent = escapeHtml(event.title);
    }
    
    const registerBtn = document.getElementById('registerFromDetailsBtn');
    if (registerBtn) {
        registerBtn.onclick = () => registerForEvent(props.id || event.id);
    }
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

async function loadEvents() {
    try {
        console.log('Loading events from API...');
        const response = await fetch('/api/v1/events?limit=50&upcoming_only=false');
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Events API response:', data);
        
        // Store events globally
        if (data && data.events && Array.isArray(data.events)) {
            allEvents = data.events;
            console.log(`Found ${allEvents.length} events`);
            if (allEvents.length > 0) {
                displayEvents(allEvents);
            } else {
                displayNoEvents();
            }
        } else if (Array.isArray(data)) {
            allEvents = data;
            console.log(`Found ${allEvents.length} events (array format)`);
            if (allEvents.length > 0) {
                displayEvents(allEvents);
            } else {
                displayNoEvents();
            }
        } else {
            console.log('Unexpected response format:', data);
            allEvents = [];
            displayNoEvents();
        }
    } catch (error) {
        console.error('Error loading events:', error);
        displayErrorMessage('Failed to load events. Please check your connection and try again.');
    }
}

function displayErrorMessage(message) {
    const grid = document.getElementById('eventsGrid');
    if (grid) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-exclamation-triangle fa-4x text-danger mb-3"></i>
                <h5>Error Loading Events</h5>
                <p class="text-muted">${escapeHtml(message)}</p>
                <button class="btn btn-primary mt-3" onclick="location.reload()">
                    <i class="fas fa-sync-alt me-2"></i>Retry
                </button>
            </div>
        `;
    }
}

function displayNoEvents() {
    const grid = document.getElementById('eventsGrid');
    if (!grid) return;
    
    grid.innerHTML = `
        <div class="col-12 text-center py-5">
            <i class="fas fa-calendar-times fa-4x text-muted mb-3"></i>
            <h5>No events found</h5>
            <p class="text-muted">Check back later for upcoming events!</p>
            ${currentUser && (currentUser.is_admin || currentUser.is_instructor) ? 
                `<button class="btn btn-primary mt-3" onclick="showCreateEventModal()">
                    <i class="fas fa-plus-circle me-2"></i>Create First Event
                </button>` : ''}
        </div>
    `;
}

async function loadFeaturedEvent() {
    try {
        console.log('Loading featured event...');
        const response = await fetch('/api/v1/events/featured');
        console.log('Featured response status:', response.status);
        
        if (!response.ok) {
            if (response.status === 404) {
                console.log('No featured event found');
                const container = document.getElementById('featuredEvent');
                if (container) {
                    container.innerHTML = '';
                }
                return;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const event = await response.json();
        console.log('Featured event:', event);
        
        if (event && event.id) {
            displayFeaturedEvent(event);
        } else {
            console.log('No featured event found');
            const container = document.getElementById('featuredEvent');
            if (container) {
                container.innerHTML = '';
            }
        }
    } catch (error) {
        console.error('Error loading featured event:', error);
        // Don't show error for featured event - it's optional
        const container = document.getElementById('featuredEvent');
        if (container) {
            container.innerHTML = '';
        }
    }
}

function displayFeaturedEvent(event) {
    const container = document.getElementById('featuredEvent');
    if (!container) return;
    
    let date = 'Date TBD';
    if (event.start_date) {
        const dateObj = new Date(event.start_date);
        if (!isNaN(dateObj.getTime())) {
            date = dateObj.toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            });
        }
    }
    
    container.innerHTML = `
        <div class="card border-0 shadow-lg">
            <div class="card-body p-5">
                <div class="row align-items-center">
                    <div class="col-lg-8">
                        <span class="badge bg-danger mb-3">FEATURED EVENT</span>
                        <h2 class="display-6 fw-bold mb-3">${escapeHtml(event.title)}</h2>
                        <p class="lead text-muted mb-4">${escapeHtml(event.description || '')}</p>
                        <div class="d-flex flex-wrap gap-4 mb-4">
                            <div>
                                <i class="fas fa-calendar text-primary me-2"></i>
                                <span>${escapeHtml(date)}</span>
                            </div>
                            <div>
                                <i class="fas fa-clock text-primary me-2"></i>
                                <span>${escapeHtml(event.start_time || 'TBD')} - ${escapeHtml(event.end_time || 'TBD')}</span>
                            </div>
                            <div>
                                <i class="fas fa-users text-primary me-2"></i>
                                <span>${event.spots_left !== null && event.spots_left !== undefined ? 
                                    event.spots_left + ' spots left' : 'Unlimited spots'}</span>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-lg" onclick="registerForEvent('${event.id}')">
                            <i class="fas fa-ticket-alt me-2"></i>Register Now
                        </button>
                    </div>
                    <div class="col-lg-4 text-center d-none d-lg-block">
                        <i class="fas fa-chalkboard-teacher fa-6x text-primary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function displayEvents(events) {
    console.log('displayEvents called with', events.length, 'events');
    const grid = document.getElementById('eventsGrid');
    
    if (!grid) {
        console.error('eventsGrid element not found!');
        return;
    }
    
    if (!events || events.length === 0) {
        displayNoEvents();
        return;
    }
    
    let html = '';
    events.forEach(event => {
        const category = event.event_type;
        let date = 'Date TBD';
        if (event.start_date) {
            const dateObj = new Date(event.start_date);
            if (!isNaN(dateObj.getTime())) {
                date = dateObj.toLocaleDateString('en-US', {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric'
                });
            }
        }
        
        const priceDisplay = event.is_free ? 
            '<small class="text-success"><i class="fas fa-circle me-1"></i>Free</small>' :
            `<small class="text-warning"><i class="fas fa-tag me-1"></i>R${event.price || 0}</small>`;
        
        const spotsDisplay = event.spots_left !== null && event.spots_left !== undefined ? 
            `<small class="text-muted">${event.spots_left} spots available</small>` :
            '<small class="text-muted">Unlimited spots</small>';
        
        const locationIcon = event.is_virtual ? 'fa-globe' : 'fa-map-marker-alt';
        const location = event.is_virtual ? 'Virtual Event' : (event.location || 'TBD');
        
        const progressWidth = getProgressWidth(event.spots_left, event.max_attendees);
        const progressColor = getProgressColor(event.spots_left, event.max_attendees);
        
        html += `
            <div class="col-md-6 col-lg-4 event-item" data-category="${category}">
                <div class="card h-100 border-0 shadow-sm event-card">
                    <div class="card-body p-4">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <span class="badge bg-${getCategoryColor(category)}">${capitalize(escapeHtml(category))}</span>
                            ${priceDisplay}
                        </div>
                        <h5 class="card-title fw-bold mb-2">${escapeHtml(event.title)}</h5>
                        <p class="card-text text-muted small mb-3">${escapeHtml(event.description ? event.description.substring(0, 100) : '')}${event.description && event.description.length > 100 ? '...' : ''}</p>
                        <div class="event-details mb-3">
                            <div class="d-flex mb-2">
                                <i class="fas fa-calendar-alt text-primary me-2" style="width: 20px;"></i>
                                <small>${escapeHtml(date)}</small>
                            </div>
                            <div class="d-flex mb-2">
                                <i class="fas fa-clock text-primary me-2" style="width: 20px;"></i>
                                <small>${escapeHtml(event.start_time || 'TBD')} - ${escapeHtml(event.end_time || 'TBD')}</small>
                            </div>
                            <div class="d-flex mb-2">
                                <i class="fas ${locationIcon} text-primary me-2" style="width: 20px;"></i>
                                <small>${escapeHtml(location)}</small>
                            </div>
                        </div>
                        ${event.max_attendees ? `
                        <div class="progress mb-2" style="height: 5px;">
                            <div class="progress-bar bg-${progressColor}" 
                                 style="width: ${progressWidth}%;"></div>
                        </div>
                        ` : ''}
                        <div class="d-flex justify-content-between align-items-center">
                            ${spotsDisplay}
                            <button class="btn btn-sm btn-outline-primary" onclick="registerForEvent('${event.id}')">
                                <i class="fas fa-ticket-alt me-1"></i>${event.is_free ? 'Register' : 'Book Now'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
    
    filterEvents();
}

function filterEvents() {
    const items = document.querySelectorAll('.event-item');
    
    items.forEach(item => {
        if (currentFilter === 'all' || item.dataset.category === currentFilter) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

async function registerForEvent(eventId) {
    if (!eventId) {
        alert('Invalid event ID');
        return;
    }
    
    if (!currentUser) {
        const confirmLogin = confirm('Please login to register for events. Would you like to go to the login page?');
        if (confirmLogin) {
            window.location.href = '/login';
        }
        return;
    }

    const registerButtons = document.querySelectorAll(`[onclick="registerForEvent('${eventId}')"]`);
    registerButtons.forEach(btn => {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
    });
    
    try {
        const response = await fetch(`/api/v1/events/${eventId}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Successfully registered for event!');
            setTimeout(() => location.reload(), 1500);
        } else {
            alert(data.detail || 'Failed to register. Please try again.');
            registerButtons.forEach(btn => {
                btn.disabled = false;
                const isFree = btn.textContent.includes('Register');
                btn.innerHTML = `<i class="fas fa-ticket-alt me-1"></i>${isFree ? 'Register' : 'Book Now'}`;
            });
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('An error occurred. Please check your connection and try again.');
        registerButtons.forEach(btn => {
            btn.disabled = false;
            const isFree = btn.textContent.includes('Register');
            btn.innerHTML = `<i class="fas fa-ticket-alt me-1"></i>${isFree ? 'Register' : 'Book Now'}`;
        });
    }
}

function showCreateEventModal() {
    if (!currentUser || (!currentUser.is_admin && !currentUser.is_instructor)) {
        alert('Only instructors and admins can create events');
        return;
    }
    
    const modal = document.getElementById('createEventModal');
    if (modal) {
        resetCreateEventForm();
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    } else {
        alert('Event creation form is unavailable');
    }
}

function resetCreateEventForm() {
    const form = document.getElementById('createEventForm');
    if (form) {
        form.reset();
    }
    
    const meetingLinkField = document.getElementById('meetingLinkField');
    if (meetingLinkField) {
        meetingLinkField.style.display = 'none';
    }

    const priceField = document.getElementById('priceField');
    const isFreeCheckbox = document.getElementById('isFree');
    if (priceField && isFreeCheckbox && isFreeCheckbox.checked) {
        priceField.style.display = 'none';
    }
}

async function createEvent() {
    console.log('Create event function called');
    
    if (!currentUser || (!currentUser.is_admin && !currentUser.is_instructor)) {
        alert('You are not authorized to create events');
        return;
    }

    const titleInput = document.getElementById('eventTitle');
    const typeInput = document.getElementById('eventType');
    const startDateInput = document.getElementById('startDate');
    
    if (!titleInput || !typeInput || !startDateInput) {
        console.error('Form inputs not found');
        alert('Form inputs not found. Please refresh the page.');
        return;
    }
    
    const eventData = {
        title: titleInput.value.trim(),
        description: document.getElementById('eventDescription')?.value.trim() || '',
        event_type: typeInput.value,
        start_date: startDateInput.value,
        end_date: document.getElementById('endDate')?.value || null,
        start_time: document.getElementById('startTime')?.value || null,
        end_time: document.getElementById('endTime')?.value || null,
        location: document.getElementById('location')?.value.trim() || '',
        is_virtual: document.getElementById('isVirtual')?.checked || false,
        meeting_link: document.getElementById('meetingLink')?.value.trim() || '',
        price: parseFloat(document.getElementById('price')?.value) || 0,
        is_free: document.getElementById('isFree')?.checked || true,
        max_attendees: parseInt(document.getElementById('maxAttendees')?.value) || null,
        organizer_name: document.getElementById('organizerName')?.value.trim() || currentUser?.full_name || 'Instructor',
        is_published: document.getElementById('isPublished')?.checked || true,
        is_featured: document.getElementById('isFeatured')?.checked || false
    };
    
    if (!eventData.title) {
        alert('Please enter an event title');
        return;
    }
    if (!eventData.event_type) {
        alert('Please select an event type');
        return;
    }
    if (!eventData.start_date) {
        alert('Please select a start date');
        return;
    }
    
    if (eventData.is_virtual && !eventData.meeting_link) {
        alert('Please provide a meeting link for the virtual event');
        return;
    }
    
    if (eventData.end_date && eventData.end_date < eventData.start_date) {
        alert('End date cannot be before start date');
        return;
    }
    
    console.log('Creating event with data:', eventData);
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('createEventModal'));
    const btn = document.querySelector('#createEventModal .btn-primary');
    const spinner = document.getElementById('createSpinner');
    const btnText = btn ? btn.querySelector('span:last-child') : null;
    
    if (btn) {
        btn.disabled = true;
        if (btnText) btnText.textContent = 'Creating...';
    }
    if (spinner) spinner.classList.remove('d-none');
    
    try {
        const response = await fetch('/api/v1/events', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(eventData)
        });
        
        const responseData = await response.json();
        console.log('Create event response:', responseData);
        
        if (response.ok) {
            if (modal) modal.hide();
            alert('Event created successfully!');
            setTimeout(() => location.reload(), 1500);
        } else {
            alert(responseData.detail || 'Failed to create event. Please check your input and try again.');
        }
    } catch (error) {
        console.error('Error creating event:', error);
        alert('An error occurred while creating the event. Please check your connection and try again.');
    } finally {
        if (btn) {
            btn.disabled = false;
            if (btnText) btnText.textContent = 'Create Event';
        }
        if (spinner) spinner.classList.add('d-none');
    }
}

function getCategoryColor(category) {
    const colors = {
        'webinar': 'primary',
        'workshop': 'success',
        'hackathon': 'danger',
        'meetup': 'info',
        'other': 'secondary'
    };
    return colors[category] || 'primary';
}

function getProgressColor(spotsLeft, maxAttendees) {
    if (!maxAttendees || spotsLeft === null || spotsLeft === undefined) return 'success';
    const percentage = ((maxAttendees - spotsLeft) / maxAttendees) * 100;
    if (percentage >= 100) return 'danger';
    if (percentage >= 80) return 'danger';
    if (percentage >= 50) return 'warning';
    return 'success';
}

function getProgressWidth(spotsLeft, maxAttendees) {
    if (!maxAttendees || spotsLeft === null || spotsLeft === undefined) return 0;
    const percentage = ((maxAttendees - spotsLeft) / maxAttendees) * 100;
    return Math.min(percentage, 100);
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

window.showGridView = showGridView;
window.showCalendarView = showCalendarView;
window.showCreateEventModal = showCreateEventModal;
window.createEvent = createEvent;
window.registerForEvent = registerForEvent;