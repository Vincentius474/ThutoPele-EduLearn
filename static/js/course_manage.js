// course_manage.js - Course Management Functionality

let questionCount = 0;
let courseId = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get course ID from data attribute
    const courseData = document.getElementById('course-data');
    if (courseData) {
        try {
            const data = JSON.parse(courseData.textContent);
            courseId = data.course_id;
            console.log('Course ID:', courseId);
        } catch (e) {
            console.error('Error parsing course data:', e);
        }
    }
    
    // Initialize material type toggle
    const materialType = document.getElementById('materialType');
    if (materialType) {
        materialType.addEventListener('change', function() {
            if (this.value === 'file') {
                document.getElementById('urlField').style.display = 'none';
                document.getElementById('fileField').style.display = 'block';
            } else {
                document.getElementById('urlField').style.display = 'block';
                document.getElementById('fileField').style.display = 'none';
            }
        });
    }
});

// ==================== MODAL FUNCTIONS ====================

function showAddMaterialModal() {
    new bootstrap.Modal(document.getElementById('materialModal')).show();
}

function showCreateQuizModal() {
    questionCount = 0;
    document.getElementById('questionsList').innerHTML = '';
    addQuestion(); // Add first question
    new bootstrap.Modal(document.getElementById('quizModal')).show();
}

function showCreateAssignmentModal() {
    new bootstrap.Modal(document.getElementById('assignmentModal')).show();
}

function showCreateAnnouncementModal() {
    new bootstrap.Modal(document.getElementById('announcementModal')).show();
}

// ==================== QUIZ FUNCTIONS ====================

function addQuestion() {
    const questionHtml = `
        <div class="card mb-3" id="question_${questionCount}">
            <div class="card-body">
                <div class="d-flex justify-content-between mb-2">
                    <h6 class="fw-bold">Question ${questionCount + 1}</h6>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeQuestion(${questionCount})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="mb-2">
                    <input type="text" class="form-control" id="q_${questionCount}_text" placeholder="Question">
                </div>
                <div class="row mb-2">
                    <div class="col-md-6">
                        <select class="form-select" id="q_${questionCount}_type">
                            <option value="multiple_choice">Multiple Choice</option>
                            <option value="true_false">True/False</option>
                            <option value="short_answer">Short Answer</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <input type="number" class="form-control" id="q_${questionCount}_points" placeholder="Points" value="1">
                    </div>
                </div>
                <div id="q_${questionCount}_options">
                    <div class="input-group mb-2">
                        <input type="text" class="form-control" placeholder="Option A">
                        <div class="input-group-text">
                            <input type="radio" name="q_${questionCount}_correct" value="0">
                        </div>
                    </div>
                    <div class="input-group mb-2">
                        <input type="text" class="form-control" placeholder="Option B">
                        <div class="input-group-text">
                            <input type="radio" name="q_${questionCount}_correct" value="1">
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="addOption(${questionCount})">
                        <i class="fas fa-plus"></i> Add Option
                    </button>
                </div>
            </div>
        </div>
    `;
    document.getElementById('questionsList').insertAdjacentHTML('beforeend', questionHtml);
    questionCount++;
}

function removeQuestion(index) {
    const questionEl = document.getElementById(`question_${index}`);
    if (questionEl) {
        questionEl.remove();
    }
}

function addOption(questionIndex) {
    const optionsDiv = document.getElementById(`q_${questionIndex}_options`);
    const optionCount = optionsDiv.children.length - 1; // Subtract the add button
    
    const optionHtml = `
        <div class="input-group mb-2">
            <input type="text" class="form-control" placeholder="Option ${String.fromCharCode(65 + optionCount)}">
            <div class="input-group-text">
                <input type="radio" name="q_${questionIndex}_correct" value="${optionCount}">
            </div>
        </div>
    `;
    optionsDiv.insertBefore(document.createRange().createContextualFragment(optionHtml), optionsDiv.lastChild);
}

// ==================== SAVE FUNCTIONS ====================

async function saveMaterial() {
    const formData = new FormData();
    formData.append('title', document.getElementById('materialTitle').value);
    formData.append('description', document.getElementById('materialDescription').value);
    formData.append('material_type', document.getElementById('materialType').value);
    
    const file = document.getElementById('materialFile').files[0];
    if (file) {
        formData.append('file', file);
    } else {
        formData.append('content_url', document.getElementById('materialUrl').value);
    }
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/materials`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to add material');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

async function saveQuiz() {
    const questions = [];
    for (let i = 0; i < questionCount; i++) {
        const questionEl = document.getElementById(`question_${i}`);
        if (questionEl) {
            const questionText = document.getElementById(`q_${i}_text`)?.value;
            if (questionText) {
                questions.push({
                    question: questionText,
                    question_type: document.getElementById(`q_${i}_type`)?.value || 'multiple_choice',
                    points: parseInt(document.getElementById(`q_${i}_points`)?.value) || 1,
                    options: getQuestionOptions(i),
                    correct_answer: getCorrectAnswer(i)
                });
            }
        }
    }
    
    if (questions.length === 0) {
        alert('Please add at least one question');
        return;
    }
    
    const quizData = {
        title: document.getElementById('quizTitle').value,
        description: document.getElementById('quizDescription').value,
        time_limit: parseInt(document.getElementById('quizTimeLimit').value) || 30,
        passing_score: parseInt(document.getElementById('quizPassingScore').value) || 70,
        questions: questions
    };
    
    console.log('Saving quiz:', quizData);
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/quizzes`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(quizData)
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to create quiz');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

function getQuestionOptions(questionIndex) {
    const optionsDiv = document.getElementById(`q_${questionIndex}_options`);
    if (!optionsDiv) return [];
    
    const inputs = optionsDiv.querySelectorAll('.input-group input[type="text"]');
    const options = [];
    inputs.forEach(input => {
        if (input.value.trim()) {
            options.push(input.value.trim());
        }
    });
    return options;
}

function getCorrectAnswer(questionIndex) {
    const selectedRadio = document.querySelector(`input[name="q_${questionIndex}_correct"]:checked`);
    if (selectedRadio) {
        const optionIndex = parseInt(selectedRadio.value);
        const options = getQuestionOptions(questionIndex);
        return options[optionIndex] || '';
    }
    return '';
}

async function saveAssignment() {
    const assignmentData = {
        title: document.getElementById('assignmentTitle').value,
        description: document.getElementById('assignmentDescription').value,
        due_date: document.getElementById('assignmentDueDate').value,
        total_points: parseInt(document.getElementById('assignmentPoints').value) || 100,
        submission_type: document.getElementById('assignmentSubmissionType').value
    };
    
    if (!assignmentData.title || !assignmentData.description) {
        alert('Title and description are required');
        return;
    }
    
    console.log('Saving assignment:', assignmentData);
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/assignments`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(assignmentData)
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to create assignment');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

async function sendAnnouncement() {
    const announcementData = {
        title: document.getElementById('announcementTitle').value,
        content: document.getElementById('announcementContent').value,
        is_important: document.getElementById('markImportant').checked,
        send_email: document.getElementById('sendEmail').checked
    };
    
    if (!announcementData.title || !announcementData.content) {
        alert('Title and content are required');
        return;
    }
    
    console.log('Sending announcement:', announcementData);
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/announcements`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(announcementData)
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to send announcement');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

// ==================== DELETE FUNCTIONS ====================

async function deleteMaterial(materialId) {
    if (!confirm('Delete this material?')) return;
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/materials/${materialId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            alert('Failed to delete material');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

async function deleteAnnouncement(announcementId) {
    if (!confirm('Delete this announcement?')) return;
    
    try {
        const response = await fetch(`/api/v1/courses/${courseId}/announcements/${announcementId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            alert('Failed to delete announcement');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

// ==================== HELPER FUNCTIONS ====================

function messageStudent(studentId) {
    alert('Messaging feature coming soon!');
}

function editMaterial(materialId) {
    alert('Edit material feature coming soon!');
}

function editQuiz(quizId) {
    alert('Edit quiz feature coming soon!');
}

function viewQuizResults(quizId) {
    alert('View quiz results feature coming soon!');
}

function editAssignment(assignmentId) {
    alert('Edit assignment feature coming soon!');
}

function gradeAssignment(assignmentId) {
    alert('Grade assignment feature coming soon!');
}