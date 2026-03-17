// events.js - Events page functionality

let currentFilter = 'all';
let currentUser = null;
let calendar = null;
let allEvents = [];

// Initialize when DOM is loaded
// document.addEventListener('DOMContentLoaded', function() {
//     console.log('Events page loaded');
    
//     // Get current user data from data attribute
//     const userData = document.getElementById('user-data');
//     if (userData) {
//         try {
//             currentUser = JSON.parse(userData.textContent);
//             console.log('Current user:', currentUser);
//         } catch (e) {
//             console.error('Error parsing user data:', e);
//         }
//     }
    
//     loadEvents();
//     loadFeaturedEvent();
    
//     // Initialize filter buttons
//     initFilters();
    
//     // Initialize virtual event checkbox toggle
//     const isVirtualCheckbox = document.getElementById('isVirtual');
//     if (isVirtualCheckbox) {
//         isVirtualCheckbox.addEventListener('change', function() {
//             document.getElementById('meetingLinkField').style.display = this.checked ? 'block' : 'none';
//         });
//     }
// });

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Events page loaded');
    
    // Get current user data from data attribute
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
    
    // Initialize filter buttons
    initFilters();
    
    // Initialize virtual event checkbox toggle
    const isVirtualCheckbox = document.getElementById('isVirtual');
    if (isVirtualCheckbox) {
        isVirtualCheckbox.addEventListener('change', function() {
            document.getElementById('meetingLinkField').style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Add form submit handler for create event form
    const createEventForm = document.getElementById('createEventForm');
    if (createEventForm) {
        createEventForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createEvent();
        });
    }
    
    // Add click handler for create event button in modal
    const createEventBtn = document.querySelector('#createEventModal .btn-primary');
    if (createEventBtn) {
        createEventBtn.addEventListener('click', function(e) {
            e.preventDefault();
            createEvent();
        });
    }
});

// Initialize filter buttons
function initFilters() {
    document.querySelectorAll('[data-filter]').forEach(button => {
        button.addEventListener('click', () => {
            // Update active state
            document.querySelectorAll('[data-filter]').forEach(btn => {
                btn.classList.remove('active');
            });
            button.classList.add('active');
            
            currentFilter = button.dataset.filter;
            filterEvents();
        });
    });
}

// Show grid view
function showGridView() {
    document.getElementById('gridViewBtn').classList.add('active');
    document.getElementById('calendarViewBtn').classList.remove('active');
    document.getElementById('eventsGrid').style.display = 'flex';
    document.getElementById('calendarView').style.display = 'none';
    document.getElementById('filterSection').style.display = 'block';
    document.getElementById('calendarLegend').style.display = 'none';
}

// Show calendar view
function showCalendarView() {
    document.getElementById('calendarViewBtn').classList.add('active');
    document.getElementById('gridViewBtn').classList.remove('active');
    document.getElementById('eventsGrid').style.display = 'none';
    document.getElementById('calendarView').style.display = 'block';
    document.getElementById('filterSection').style.display = 'none';
    document.getElementById('calendarLegend').style.display = 'block';
    
    // Initialize calendar if not already done
    if (!calendar && allEvents.length > 0) {
        initCalendar();
    }
}

// Initialize FullCalendar
function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    
    // Get category color
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
    
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: allEvents.map(event => ({
            id: event.id,
            title: event.title,
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
                price: event.price
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
        }
    });
    
    calendar.render();
}

// Show event details modal
function showEventDetails(event) {
    const props = event.extendedProps;
    const date = new Date(event.start).toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    const modalBody = document.getElementById('eventDetailsBody');
    modalBody.innerHTML = `
        <div class="text-center mb-3">
            <span class="badge bg-${getCategoryColor(props.event_type)}">${capitalize(props.event_type)}</span>
            ${props.is_free ? 
                '<span class="badge bg-success ms-2">Free</span>' : 
                `<span class="badge bg-warning ms-2">$${props.price}</span>`}
        </div>
        <h6 class="fw-bold">${date}</h6>
        <p><i class="fas fa-clock me-2 text-primary"></i>${props.time}</p>
        <p><i class="fas ${props.location === 'Virtual Event' ? 'fa-globe' : 'fa-map-marker-alt'} me-2 text-primary"></i>${props.location}</p>
        <p class="text-muted">${props.description || 'No description available'}</p>
        <div class="alert alert-info">
            <i class="fas fa-users me-2"></i>
            ${props.spots_left !== null ? props.spots_left + ' spots available' : 'Unlimited spots'}
        </div>
    `;
    
    document.getElementById('eventDetailsTitle').textContent = event.title;
    
    // Set up register button
    const registerBtn = document.getElementById('registerFromDetailsBtn');
    registerBtn.onclick = () => registerForEvent(event.id);
    
    new bootstrap.Modal(document.getElementById('eventDetailsModal')).show();
}

// Load events from API
async function loadEvents() {
    try {
        console.log('Loading events from API...');
        const response = await fetch('/api/v1/events?limit=50&upcoming_only=false');
        console.log('Response status:', response.status);
        
        const data = await response.json();
        console.log('Events API response:', data);
        
        // Store events globally
        if (data && data.events) {
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
            displayNoEvents();
        }
    } catch (error) {
        console.error('Error loading events:', error);
        displayNoEvents();
    }
}

// Display message when no events are found
function displayNoEvents() {
    const grid = document.getElementById('eventsGrid');
    if (grid) {
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
}

// Load featured event
async function loadFeaturedEvent() {
    try {
        console.log('Loading featured event...');
        const response = await fetch('/api/v1/events/featured');
        console.log('Featured response status:', response.status);
        
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
    }
}

// Display featured event
function displayFeaturedEvent(event) {
    const container = document.getElementById('featuredEvent');
    if (!container) return;
    
    const date = new Date(event.start_date).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    });
    
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
                                <span>${date}</span>
                            </div>
                            <div>
                                <i class="fas fa-clock text-primary me-2"></i>
                                <span>${event.start_time || 'TBD'} - ${event.end_time || 'TBD'}</span>
                            </div>
                            <div>
                                <i class="fas fa-users text-primary me-2"></i>
                                <span>${event.spots_left !== null ? event.spots_left + ' spots left' : 'Unlimited spots'}</span>
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

// Display events in grid
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
        const date = new Date(event.start_date).toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric'
        });
        
        const priceDisplay = event.is_free ? 
            '<small class="text-success"><i class="fas fa-circle me-1"></i>Free</small>' :
            `<small class="text-warning"><i class="fas fa-tag me-1"></i>$${event.price}</small>`;
        
        const spotsDisplay = event.spots_left !== null ? 
            `<small class="text-muted">${event.spots_left} spots available</small>` :
            '<small class="text-muted">Unlimited spots</small>';
        
        const locationIcon = event.is_virtual ? 'fa-globe' : 'fa-map-marker-alt';
        const location = event.is_virtual ? 'Virtual Event' : (event.location || 'TBD');
        
        html += `
            <div class="col-md-6 col-lg-4 event-item" data-category="${category}">
                <div class="card h-100 border-0 shadow-sm event-card" onclick="showEventDetailsFromCard('${event.id}')">
                    <div class="card-body p-4">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <span class="badge bg-${getCategoryColor(category)}">${capitalize(category)}</span>
                            ${priceDisplay}
                        </div>
                        <h5 class="card-title fw-bold mb-2">${escapeHtml(event.title)}</h5>
                        <p class="card-text text-muted small mb-3">${escapeHtml(event.description ? event.description.substring(0, 100) : '')}...</p>
                        <div class="event-details mb-3">
                            <div class="d-flex mb-2">
                                <i class="fas fa-calendar-alt text-primary me-2" style="width: 20px;"></i>
                                <small>${date}</small>
                            </div>
                            <div class="d-flex mb-2">
                                <i class="fas fa-clock text-primary me-2" style="width: 20px;"></i>
                                <small>${event.start_time || 'TBD'} - ${event.end_time || 'TBD'}</small>
                            </div>
                            <div class="d-flex mb-2">
                                <i class="fas ${locationIcon} text-primary me-2" style="width: 20px;"></i>
                                <small>${escapeHtml(location)}</small>
                            </div>
                        </div>
                        <div class="progress mb-2" style="height: 5px;">
                            <div class="progress-bar bg-${getProgressColor(event.spots_left, event.max_attendees)}" 
                                 style="width: ${getProgressWidth(event.spots_left, event.max_attendees)}%;"></div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            ${spotsDisplay}
                            <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); registerForEvent('${event.id}')">
                                ${event.is_free ? 'Register' : 'Book Now'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
    
    // Apply current filter
    filterEvents();
}

// Show event details from card
function showEventDetailsFromCard(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    if (event) {
        // Create a fake FullCalendar event object
        const fakeEvent = {
            id: event.id,
            title: event.title,
            start: event.start_date,
            end: event.end_date,
            extendedProps: {
                description: event.description,
                time: event.start_time ? `${event.start_time} - ${event.end_time || 'TBD'}` : 'TBD',
                location: event.is_virtual ? 'Virtual Event' : (event.location || 'TBD'),
                spots_left: event.spots_left,
                event_type: event.event_type,
                is_free: event.is_free,
                price: event.price
            }
        };
        showEventDetails(fakeEvent);
    }
}

// Filter events by category
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

// Register for event
async function registerForEvent(eventId) {
    if (!currentUser) {
        alert('Please login to register for events');
        window.location.href = '/login';
        return;
    }
    
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
            alert(data.detail || 'Failed to register');
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('An error occurred');
    }
}

// Show create event modal (for admins/instructors)
function showCreateEventModal() {
    if (!currentUser || (!currentUser.is_admin && !currentUser.is_instructor)) {
        alert('Only instructors and admins can create events');
        return;
    }
    
    const modal = document.getElementById('createEventModal');
    if (modal) {
        new bootstrap.Modal(modal).show();
    }
}

// Create new event (for admins/instructors)
async function createEvent() {
    console.log('Create event function called');
    
    // Get form data with error checking
    const titleInput = document.getElementById('eventTitle');
    const typeInput = document.getElementById('eventType');
    const startDateInput = document.getElementById('startDate');
    
    if (!titleInput || !typeInput || !startDateInput) {
        console.error('Form inputs not found');
        alert('Form inputs not found. Please refresh the page.');
        return;
    }
    
    const eventData = {
        title: titleInput.value,
        description: document.getElementById('eventDescription')?.value || '',
        event_type: typeInput.value,
        start_date: startDateInput.value,
        end_date: document.getElementById('endDate')?.value || null,
        start_time: document.getElementById('startTime')?.value || null,
        end_time: document.getElementById('endTime')?.value || null,
        location: document.getElementById('location')?.value || '',
        is_virtual: document.getElementById('isVirtual')?.checked || false,
        meeting_link: document.getElementById('meetingLink')?.value || '',
        price: parseFloat(document.getElementById('price')?.value) || 0,
        is_free: document.getElementById('isFree')?.checked || true,
        max_attendees: parseInt(document.getElementById('maxAttendees')?.value) || null,
        organizer_name: document.getElementById('organizerName')?.value || currentUser?.full_name || 'Instructor',
        is_published: document.getElementById('isPublished')?.checked || true,
        is_featured: document.getElementById('isFeatured')?.checked || false
    };
    
    // Validate required fields
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
    
    console.log('Creating event with data:', eventData);
    
    // Show loading state
    const btn = document.querySelector('#createEventModal .btn-primary');
    const spinner = document.getElementById('createSpinner');
    const btnText = btn ? btn.querySelector('span:last-child') : null;
    
    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');
    if (btnText) btnText.textContent = 'Creating...';
    
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
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createEventModal'));
            if (modal) modal.hide();
            
            // Show success message
            alert('Event created successfully!');
            
            // Reset form
            document.getElementById('createEventForm')?.reset();
            
            // Reload events
            setTimeout(() => location.reload(), 1500);
        } else {
            alert(responseData.detail || 'Failed to create event');
        }
    } catch (error) {
        console.error('Error creating event:', error);
        alert('An error occurred while creating the event. Please try again.');
    } finally {
        // Reset button state
        if (btn) btn.disabled = false;
        if (spinner) spinner.classList.add('d-none');
        if (btnText) btnText.textContent = 'Create Event';
    }
}

// Helper functions
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
    if (!maxAttendees) return 'success';
    const percentage = ((maxAttendees - spotsLeft) / maxAttendees) * 100;
    if (percentage >= 80) return 'danger';
    if (percentage >= 50) return 'warning';
    return 'success';
}

function getProgressWidth(spotsLeft, maxAttendees) {
    if (!maxAttendees) return 0;
    return ((maxAttendees - spotsLeft) / maxAttendees) * 100;
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available for onclick handlers
window.showGridView = showGridView;
window.showCalendarView = showCalendarView;
window.showCreateEventModal = showCreateEventModal;
window.createEvent = createEvent;
window.registerForEvent = registerForEvent;
window.showEventDetailsFromCard = showEventDetailsFromCard;