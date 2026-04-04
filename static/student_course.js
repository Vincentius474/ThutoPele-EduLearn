// student_course.js - Student course view functionality

let courseId = null;
let userId = null;
let currentQuiz = null;
let quizTimer = null;
let timeLeft = 0;

document.addEventListener('DOMContentLoaded', function() {
    const courseData = document.getElementById('course-data');
    if (courseData) {
        try {
            const data = JSON.parse(courseData.textContent);
            courseId = data.course_id;
            userId = data.user_id;
        } catch (e) {
            console.error('Error parsing course data:', e);
        }
    }
    
    // Initialize message form
    const messageForm = document.getElementById('sendMessageForm');
    if (messageForm) {
        messageForm.addEventListener('submit', sendMessage);
    }
});

// ==================== VIDEO FUNCTIONS ====================

function playVideo(videoUrl) {
    if (videoUrl) {
        document.getElementById('videoPlayer').src = videoUrl;
        new bootstrap.Modal(document.getElementById('videoModal')).show();
    } else {
        showError('Video URL not available');
    }
}

// ==================== MATERIAL FUNCTIONS ====================

async function markMaterialComplete(materialId) {
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/progress/${materialId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showSuccess('Material marked as complete!');
            setTimeout(() => location.reload(), 1500);
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to mark material as complete');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred');
    }
}

// ==================== ASSIGNMENT FUNCTIONS ====================

function openAssignmentModal(assignmentId) {
    document.getElementById('assignmentId').value = assignmentId;
    document.getElementById('assignmentText').value = '';
    document.getElementById('assignmentFile').value = '';
    new bootstrap.Modal(document.getElementById('assignmentModal')).show();
}

async function submitAssignment() {
    const assignmentId = document.getElementById('assignmentId').value;
    const text = document.getElementById('assignmentText').value;
    const file = document.getElementById('assignmentFile').files[0];
    
    const formData = new FormData();
    formData.append('assignment_id', assignmentId);
    if (text) formData.append('text', text);
    if (file) formData.append('file', file);
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/assignments/${assignmentId}/submit`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('assignmentModal')).hide();
            showSuccess('Assignment submitted successfully!');
            setTimeout(() => location.reload(), 1500);
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to submit assignment');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred');
    }
}

// ==================== QUIZ FUNCTIONS ====================

async function startQuiz(quizId) {
    try {
        const response = await fetch(`/api/v1/courses/quizzes/${quizId}`);
        const quiz = await response.json();
        
        currentQuiz = quiz;
        timeLeft = quiz.time_limit * 60; // Convert to seconds
        
        // Build quiz interface
        let questionsHtml = '';
        quiz.questions.forEach((q, idx) => {
            questionsHtml += `
                <div class="card mb-3">
                    <div class="card-body">
                        <h6 class="fw-bold mb-3">Question ${idx + 1}: ${q.question}</h6>
                        <div class="ms-3">
                            ${q.question_type === 'multiple_choice' ? `
                                ${q.options.map((opt, optIdx) => `
                                    <div class="form-check mb-2">
                                        <input class="form-check-input" type="radio" name="q_${q.id}" value="${opt}">
                                        <label class="form-check-label">${opt}</label>
                                    </div>
                                `).join('')}
                            ` : q.question_type === 'true_false' ? `
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="radio" name="q_${q.id}" value="True">
                                    <label class="form-check-label">True</label>
                                </div>
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="radio" name="q_${q.id}" value="False">
                                    <label class="form-check-label">False</label>
                                </div>
                            ` : `
                                <textarea class="form-control" name="q_${q.id}" rows="3" placeholder="Type your answer here..."></textarea>
                            `}
                        </div>
                    </div>
                </div>
            `;
        });
        
        document.getElementById('quizModalTitle').textContent = quiz.title;
        document.getElementById('quizModalBody').innerHTML = questionsHtml;
        document.getElementById('quizTimer').textContent = formatTime(timeLeft);
        
        // Start timer
        if (quizTimer) clearInterval(quizTimer);
        quizTimer = setInterval(updateTimer, 1000);
        
        new bootstrap.Modal(document.getElementById('quizModal')).show();
        
    } catch (error) {
        console.error('Error loading quiz:', error);
        showError('Failed to load quiz');
    }
}

function updateTimer() {
    if (timeLeft <= 0) {
        clearInterval(quizTimer);
        submitQuiz();
    } else {
        timeLeft--;
        document.getElementById('quizTimer').textContent = formatTime(timeLeft);
    }
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `Time Left: ${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

async function submitQuiz() {
    clearInterval(quizTimer);
    
    // Collect answers
    const answers = [];
    currentQuiz.questions.forEach(q => {
        const selected = document.querySelector(`input[name="q_${q.id}"]:checked, textarea[name="q_${q.id}"]`);
        if (selected) {
            answers.push({
                question_id: q.id,
                answer: selected.value
            });
        }
    });
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/quizzes/${currentQuiz.id}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ answers: answers })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('quizModal')).hide();
            showSuccess(`Quiz submitted! Your score: ${result.score}%`);
            setTimeout(() => location.reload(), 2000);
        } else {
            showError(result.detail || 'Failed to submit quiz');
        }
    } catch (error) {
        console.error('Error submitting quiz:', error);
        showError('An error occurred');
    }
}

// ==================== MESSAGE FUNCTIONS ====================

async function sendMessage(e) {
    e.preventDefault();
    
    const subject = document.getElementById('messageSubject').value;
    const content = document.getElementById('messageContent').value;
    
    if (!subject || !content) {
        showError('Please enter both subject and message');
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subject: subject,
                content: content
            })
        });
        
        if (response.ok) {
            document.getElementById('messageSubject').value = '';
            document.getElementById('messageContent').value = '';
            showSuccess('Message sent successfully!');
            setTimeout(() => location.reload(), 1500);
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showError('An error occurred');
    }
}

// ==================== HELPER FUNCTIONS ====================

function showSuccess(message) {
    document.getElementById('successMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('successModal')).show();
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('errorModal')).show();
}