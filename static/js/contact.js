// contact.js - Contact form functionality (simplified version)

console.log('contact.js loaded successfully');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
    
    const contactForm = document.getElementById('contactForm');
    console.log('Contact form element:', contactForm);
    
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            console.log('Form submitted');
            e.preventDefault();
            
            // Get form data
            const formData = {
                name: document.getElementById('name')?.value || '',
                email: document.getElementById('email')?.value || '',
                subject: document.getElementById('subject')?.value || '',
                message: document.getElementById('message')?.value || ''
            };
            
            console.log('Form data:', formData);
            
            // Simple validation
            if (!formData.name || !formData.email || !formData.subject || !formData.message) {
                alert('Please fill in all fields');
                return;
            }
            
            // Get button elements
            const submitBtn = document.getElementById('submitBtn');
            const spinner = document.getElementById('submitSpinner');
            const submitText = document.getElementById('submitText');
            
            if (!submitBtn || !spinner || !submitText) {
                console.error('Button elements not found');
                alert('Form error - please refresh the page');
                return;
            }
            
            const originalText = submitText.innerHTML;
            
            // Show loading
            submitBtn.disabled = true;
            spinner.classList.remove('d-none');
            submitText.innerHTML = 'Sending...';
            
            // Hide previous alerts
            const successAlert = document.getElementById('successAlert');
            const errorAlert = document.getElementById('errorAlert');
            if (successAlert) successAlert.classList.add('d-none');
            if (errorAlert) errorAlert.classList.add('d-none');
            
            // Simulate API call with timeout
            setTimeout(() => {
                // Show success message (for testing)
                if (successAlert) {
                    document.getElementById('successMessage').textContent = 'Test: Form would submit successfully!';
                    successAlert.classList.remove('d-none');
                }
                
                // Reset button
                submitBtn.disabled = false;
                spinner.classList.add('d-none');
                submitText.innerHTML = originalText;
                
                // Reset form
                document.getElementById('contactForm').reset();
                
                console.log('Form test complete');
            }, 2000);
        });
    } else {
        console.error('Contact form not found in the DOM');
    }
});