document.addEventListener('DOMContentLoaded', function() {
    loadEvents();
});

// Load all events from the API
async function loadEvents() {
    const eventsContainer = document.getElementById('events-container');
    const loadingElement = document.getElementById('loading');
    const noEventsElement = document.getElementById('no-events');
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/events`);
        const events = await response.json();
        
        // Hide loading spinner
        loadingElement.classList.add('d-none');
        
        if (events.length === 0) {
            // Show "no events" message
            noEventsElement.classList.remove('d-none');
            return;
        }
        
        // Clear existing content
        eventsContainer.innerHTML = '';
        
        // Add event cards
        events.forEach(event => {
            const card = createEventCard(event);
            eventsContainer.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading events:', error);
        loadingElement.classList.add('d-none');
        
        // Show error message
        eventsContainer.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle"></i> Error loading events. Please try again later.
                </div>
            </div>
        `;
    }
}

// Create a card element for an event
function createEventCard(event) {
    const col = document.createElement('div');
    col.className = 'col-md-4 mb-4';
    
    // Format date
    const eventDate = new Date(event.date);
    const formattedDate = eventDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    col.innerHTML = `
        <div class="card event-card h-100">
            <div class="card-body">
                <h5 class="card-title">${event.topic}</h5>
                <p class="card-text">${event.description}</p>
                <p class="card-text"><small class="text-muted">${formattedDate}</small></p>
            </div>
            <div class="card-footer">
                <a href="create_post.html?id=${event.id}" class="btn btn-primary">
                    <i class="fas fa-pencil-alt"></i> Generate Post
                </a>
            </div>
        </div>
    `;
    
    return col;
}