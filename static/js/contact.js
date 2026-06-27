console.log('contact.js loaded successfully');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
    
    const contactForm = document.getElementById('contactForm');
    console.log('Contact form element:', contactForm);
    
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            console.log('Form submitted - event fired');
            e.preventDefault();
            
            const name = document.getElementById('name')?.value || '';
            const email = document.getElementById('email')?.value || '';
            const subject = document.getElementById('subject')?.value || '';
            const message = document.getElementById('message')?.value || '';
            
            const formData = { name, email, subject, message };
            console.log('Form data:', formData);
 
            if (!name || !email || !subject || !message) {
                alert('Please fill in all fields');
                return;
            }

            const submitBtn = document.getElementById('submitBtn');
            const spinner = document.getElementById('submitSpinner');
            const submitText = document.getElementById('submitText');
            
            if (!submitBtn || !spinner || !submitText) {
                console.error('Button elements not found');
                alert('Form error - please refresh the page');
                return;
            }
            
            const originalText = submitText.innerHTML;
            
            submitBtn.disabled = true;
            spinner.classList.remove('d-none');
            submitText.innerHTML = 'Sending...';
            
            const successAlert = document.getElementById('successAlert');
            const errorAlert = document.getElementById('errorAlert');
            if (successAlert) successAlert.classList.add('d-none');
            if (errorAlert) errorAlert.classList.add('d-none');

            const apiUrl = '/api/v1/contact';
            console.log('Fetching URL:', apiUrl);
            
            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            })
            .then(response => {
                console.log('Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);
                
                if (data.success) {
                    if (successAlert) {
                        document.getElementById('successMessage').textContent = data.message || 'Thank you for your message!';
                        successAlert.classList.remove('d-none');
                    }
                    document.getElementById('contactForm').reset();
                } else {
                    if (errorAlert) {
                        document.getElementById('errorMessage').textContent = data.detail || 'An error occurred';
                        errorAlert.classList.remove('d-none');
                    }
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                if (errorAlert) {
                    document.getElementById('errorMessage').textContent = 'Network error. Please try again.';
                    errorAlert.classList.remove('d-none');
                }
            })
            .finally(() => {
                // Reset button
                submitBtn.disabled = false;
                spinner.classList.add('d-none');
                submitText.innerHTML = originalText;
            });
        });
    } else {
        console.error('Contact form not found in the DOM');
    }
});