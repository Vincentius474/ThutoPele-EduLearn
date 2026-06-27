// course_manage.js - Course Management Functionality

let questionCount = 0;
let currentEditQuizId = null;
let currentEditAssignmentId = null;
let currentEditAnnouncementId = null;
let courseId = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
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
    addQuestion();
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
    const optionCount = optionsDiv.children.length - 1; 
    
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

function removeEditQuestion(index) {
    const questionEl = document.getElementById(`edit_question_${index}`);
    if (questionEl) {
        questionEl.remove();
    }
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

async function deleteQuiz(quizId) {
    if (!confirm('Are you sure you want to delete this quiz? This action cannot be undone.')) return;
    
    try {
        const response = await fetch(`/api/v1/courses/quizzes/${quizId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Quiz deleted successfully');
            window.location.reload();
        } else {
            alert('Failed to delete quiz');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

async function deleteAssignment(assignmentId) {
    if (!confirm('Are you sure you want to delete this assignment? This action cannot be undone.')) return;
    
    try {
        const response = await fetch(`/api/v1/courses/assignments/${assignmentId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Assignment deleted successfully');
            window.location.reload();
        } else {
            alert('Failed to delete assignment');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

async function deleteAnnouncement(announcementId) {
    if (!confirm('Delete this announcement?')) return;
    
    try {
        const response = await fetch(`/api/v1/courses/announcements/${announcementId}`, {
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

// ==================== EDIT QUIZ FUNCTIONS ====================

async function editQuiz(quizId) {
    try {
        const response = await fetch(`/api/v1/courses/quizzes/${quizId}/edit`);
        const quiz = await response.json();
        
        currentEditQuizId = quiz.id;
        document.getElementById('editQuizId').value = quiz.id;
        document.getElementById('editQuizTitle').value = quiz.title;
        document.getElementById('editQuizDescription').value = quiz.description || '';
        document.getElementById('editQuizTimeLimit').value = quiz.time_limit || 30;
        document.getElementById('editQuizPassingScore').value = quiz.passing_score || 70;
        
        // Populate questions
        const questionsList = document.getElementById('editQuestionsList');
        questionsList.innerHTML = '';
        
        if (quiz.questions && quiz.questions.length > 0) {
            quiz.questions.forEach((q, idx) => {
                questionsList.innerHTML += `
                    <div class="card mb-2" id="edit_question_${idx}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <strong>Question ${idx + 1}:</strong>
                                <button class="btn btn-sm btn-outline-danger" onclick="removeEditQuestion(${idx})">Remove</button>
                            </div>
                            <p>${escapeHtml(q.question)}</p>
                            <small>Type: ${q.question_type} | Points: ${q.points}</small>
                        </div>
                    </div>
                `;
            });
        }
        
        new bootstrap.Modal(document.getElementById('editQuizModal')).show();
    } catch (error) {
        console.error('Error loading quiz:', error);
        alert('Failed to load quiz for editing');
    }
}

async function saveQuizEdit() {
    const quizId = document.getElementById('editQuizId').value;
    const quizData = {
        title: document.getElementById('editQuizTitle').value,
        description: document.getElementById('editQuizDescription').value,
        time_limit: parseInt(document.getElementById('editQuizTimeLimit').value),
        passing_score: parseInt(document.getElementById('editQuizPassingScore').value)
    };
    
    try {
        const response = await fetch(`/api/v1/courses/quizzes/${quizId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(quizData)
        });
        
        if (response.ok) {
            alert('Quiz updated successfully');
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to update quiz');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

// ==================== EDIT ASSIGNMENT FUNCTIONS ====================

async function editAssignment(assignmentId) {
    try {
        const response = await fetch(`/api/v1/courses/assignments/${assignmentId}/edit`);
        const assignment = await response.json();
        
        currentEditAssignmentId = assignment.id;
        document.getElementById('editAssignmentId').value = assignment.id;
        document.getElementById('editAssignmentTitle').value = assignment.title;
        document.getElementById('editAssignmentDescription').value = assignment.description || '';
        document.getElementById('editAssignmentDueDate').value = assignment.due_date ? assignment.due_date.slice(0, 10) : '';
        document.getElementById('editAssignmentPoints').value = assignment.total_points || 100;
        document.getElementById('editAssignmentSubmissionType').value = assignment.submission_type || 'file';
        
        new bootstrap.Modal(document.getElementById('editAssignmentModal')).show();
    } catch (error) {
        console.error('Error loading assignment:', error);
        alert('Failed to load assignment for editing');
    }
}

async function saveAssignmentEdit() {
    const assignmentId = document.getElementById('editAssignmentId').value;
    const assignmentData = {
        title: document.getElementById('editAssignmentTitle').value,
        description: document.getElementById('editAssignmentDescription').value,
        due_date: document.getElementById('editAssignmentDueDate').value,
        total_points: parseInt(document.getElementById('editAssignmentPoints').value),
        submission_type: document.getElementById('editAssignmentSubmissionType').value
    };
    
    try {
        const response = await fetch(`/api/v1/courses/assignments/${assignmentId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(assignmentData)
        });
        
        if (response.ok) {
            alert('Assignment updated successfully');
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to update assignment');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

// ==================== EDIT ANNOUNCEMENT FUNCTIONS ====================

async function editAnnouncement(announcementId) {
    const announcementCard = document.querySelector(`#announcement-${announcementId}`);
    if (announcementCard) {
        const titleElement = announcementCard.querySelector('.announcement-title');
        const contentElement = announcementCard.querySelector('.announcement-content');
        
        const title = titleElement ? titleElement.textContent : '';
        const content = contentElement ? contentElement.textContent : '';
        
        currentEditAnnouncementId = announcementId;
        document.getElementById('editAnnouncementId').value = announcementId;
        document.getElementById('editAnnouncementTitle').value = title;
        document.getElementById('editAnnouncementContent').value = content;
        document.getElementById('editMarkImportant').checked = false;
        
        new bootstrap.Modal(document.getElementById('editAnnouncementModal')).show();
    } else {
        alert('Announcement not found');
    }
}

async function saveAnnouncementEdit() {
    const announcementId = document.getElementById('editAnnouncementId').value;
    const announcementData = {
        title: document.getElementById('editAnnouncementTitle').value,
        content: document.getElementById('editAnnouncementContent').value,
        is_important: document.getElementById('editMarkImportant').checked
    };
    
    try {
        const response = await fetch(`/api/v1/courses/announcements/${announcementId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(announcementData)
        });
        
        if (response.ok) {
            alert('Announcement updated successfully');
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to update announcement');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
}

// ==================== OTHER FUNCTIONS ====================

async function viewQuizResults(quizId) {
    try {
        const response = await fetch(`/api/v1/courses/quizzes/${quizId}`);
        const quiz = await response.json();
        
        const submissionsResponse = await fetch(`/api/v1/courses/quizzes/${quizId}/submissions`);
        const submissions = submissionsResponse.ok ? await submissionsResponse.json() : [];

        const modalHtml = `
            <div class="modal fade" id="quizResultsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">Quiz Results: ${escapeHtml(quiz.title)}</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-4">
                                <div class="col-md-4">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h3>${quiz.questions?.length || 0}</h3>
                                            <small>Total Questions</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h3>${submissions.length}</h3>
                                            <small>Total Submissions</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h3>${quiz.passing_score || 70}%</h3>
                                            <small>Passing Score</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <h6 class="fw-bold mb-3">Student Submissions</h6>
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Student</th>
                                            <th>Submitted</th>
                                            <th>Score</th>
                                            <th>Status</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${submissions.length > 0 ? submissions.map(sub => `
                                            <tr>
                                                <td>
                                                    <div class="d-flex align-items-center">
                                                        <img src="${sub.users?.avatar_url || 'https://ui-avatars.com/api/?name=' + (sub.users?.full_name || 'Student')}" 
                                                             class="rounded-circle me-2" width="30" height="30">
                                                        ${sub.users?.full_name || 'Unknown'}
                                                    </div>
                                                </td>
                                                <td>${new Date(sub.submitted_at).toLocaleDateString()}</td>
                                                <td>
                                                    <span class="badge ${sub.score >= (quiz.passing_score || 70) ? 'bg-success' : 'bg-danger'}">
                                                        ${sub.score || 0}%
                                                    </span>
                                                </td>
                                                <td>
                                                    ${sub.score >= (quiz.passing_score || 70) ? 
                                                        '<span class="badge bg-success">Passed</span>' : 
                                                        '<span class="badge bg-danger">Failed</span>'}
                                                </td>
                                                <td>
                                                    <button class="btn btn-sm btn-outline-info" onclick="viewStudentQuizDetails('${sub.id}', '${quiz.id}')">
                                                        View Details
                                                    </button>
                                                </td>
                                             </div>
                                        `).join('') : `
                                            <tr>
                                                <td colspan="5" class="text-center py-4">
                                                    <i class="fas fa-users fa-3x text-muted mb-3"></i>
                                                    <p>No submissions yet</p>
                                                </td>
                                            </div>
                                        `}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button class="btn btn-primary" onclick="exportQuizResults('${quizId}')">
                                <i class="fas fa-download me-2"></i>Export Results
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('quizResultsModal');
        if (existingModal) {
            existingModal.remove();
        }

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        new bootstrap.Modal(document.getElementById('quizResultsModal')).show();
        
    } catch (error) {
        console.error('Error loading quiz results:', error);
        alert('Failed to load quiz results');
    }
}

async function viewStudentQuizDetails(submissionId, quizId) {
    try {
        const response = await fetch(`/api/v1/courses/submissions/${submissionId}`);
        const submission = await response.json();
        
        const quizResponse = await fetch(`/api/v1/courses/quizzes/${quizId}`);
        const quiz = await quizResponse.json();
        
        const modalHtml = `
            <div class="modal fade" id="studentQuizDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title">Student Quiz Details</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <strong>Student:</strong> ${submission.users?.full_name || 'Unknown'}
                            </div>
                            <div class="mb-3">
                                <strong>Submitted:</strong> ${new Date(submission.submitted_at).toLocaleString()}
                            </div>
                            <div class="mb-3">
                                <strong>Score:</strong> ${submission.score || 0}%
                            </div>
                            <h6 class="fw-bold mt-4">Answers</h6>
                            ${submission.answers?.map((answer, idx) => `
                                <div class="card mb-2">
                                    <div class="card-body">
                                        <strong>Q${idx + 1}:</strong> ${quiz.questions?.[idx]?.question || 'Question'}<br>
                                        <strong>Student Answer:</strong> ${answer.student_answer}<br>
                                        <strong>Correct Answer:</strong> ${quiz.questions?.[idx]?.correct_answer || 'N/A'}<br>
                                        <span class="badge ${answer.is_correct ? 'bg-success' : 'bg-danger'}">
                                            ${answer.is_correct ? 'Correct' : 'Incorrect'}
                                        </span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('studentQuizDetailModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        new bootstrap.Modal(document.getElementById('studentQuizDetailModal')).show();
        
    } catch (error) {
        console.error('Error loading student quiz details:', error);
        alert('Failed to load student details');
    }
}

async function exportQuizResults(quizId) {
    try {
        const response = await fetch(`/api/v1/courses/quizzes/${quizId}/submissions/export`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `quiz_results_${quizId}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to export results');
        }
    } catch (error) {
        console.error('Error exporting results:', error);
        alert('An error occurred');
    }
}

// ==================== GRADE ASSIGNMENT ====================

async function gradeAssignment(assignmentId) {
    try {
        const assignmentResponse = await fetch(`/api/v1/courses/assignments/${assignmentId}/edit`);
        const assignment = await assignmentResponse.json();
        const submissionsResponse = await fetch(`/api/v1/courses/assignments/${assignmentId}/submissions`);
        const submissions = await submissionsResponse.json();
        
        const modalHtml = `
            <div class="modal fade" id="gradeAssignmentModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-success text-white">
                            <h5 class="modal-title">Grade Assignment: ${escapeHtml(assignment.title)}</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h3>${submissions.length}</h3>
                                            <small>Submissions</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h3>${assignment.total_points || 100}</h3>
                                            <small>Total Points</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <h6 class="fw-bold mb-3">Student Submissions</h6>
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Student</th>
                                            <th>Submitted</th>
                                            <th>Score</th>
                                            <th>Status</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${submissions.length > 0 ? submissions.map(sub => `
                                            <tr>
                                                <td>
                                                    <div class="d-flex align-items-center">
                                                        <img src="${sub.users?.avatar_url || 'https://ui-avatars.com/api/?name=' + (sub.users?.full_name || 'Student')}" 
                                                             class="rounded-circle me-2" width="30" height="30">
                                                        ${sub.users?.full_name || 'Unknown'}
                                                    </div>
                                                </td>
                                                <td>${new Date(sub.submitted_at).toLocaleDateString()}</td>
                                                <td>
                                                    <span class="badge ${sub.score >= (assignment.total_points * 0.6) ? 'bg-success' : 'bg-warning'}">
                                                        ${sub.score || 0}/${assignment.total_points || 100}
                                                    </span>
                                                </td>
                                                <td>
                                                    ${sub.score ? 
                                                        '<span class="badge bg-success">Graded</span>' : 
                                                        '<span class="badge bg-warning">Pending</span>'}
                                                </td>
                                                <td>
                                                    <button class="btn btn-sm btn-outline-primary" onclick="openGradeModal('${sub.id}', '${sub.users?.full_name || 'Student'}', ${sub.score || 0}, '${sub.feedback || ''}')">
                                                        ${sub.score ? 'Update Grade' : 'Grade'}
                                                    </button>
                                                </td>
                                             </div>
                                        `).join('') : `
                                            <tr>
                                                <td colspan="5" class="text-center py-4">
                                                    <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                                                    <p>No submissions yet</p>
                                                </td>
                                            </div>
                                        `}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('gradeAssignmentModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        new bootstrap.Modal(document.getElementById('gradeAssignmentModal')).show();
        
    } catch (error) {
        console.error('Error loading assignment for grading:', error);
        alert('Failed to load assignment for grading');
    }
}

let currentGradingSubmissionId = null;

function openGradeModal(submissionId, studentName, currentScore, currentFeedback) {
    currentGradingSubmissionId = submissionId;
    
    const modalHtml = `
        <div class="modal fade" id="gradeModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">Grade Submission: ${escapeHtml(studentName)}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="gradeForm">
                            <div class="mb-3">
                                <label class="form-label">Score</label>
                                <input type="number" class="form-control" id="gradeScore" value="${currentScore}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Feedback</label>
                                <textarea class="form-control" id="gradeFeedback" rows="4">${escapeHtml(currentFeedback)}</textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="submitGrade()">Submit Grade</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const existingModal = document.getElementById('gradeModal');
    if (existingModal) existingModal.remove();
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('gradeModal')).show();
}

async function submitGrade() {
    const score = document.getElementById('gradeScore').value;
    const feedback = document.getElementById('gradeFeedback').value;
    
    if (!score) {
        alert('Please enter a score');
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/courses/submissions/${currentGradingSubmissionId}/grade`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                score: parseInt(score),
                feedback: feedback
            })
        });
        
        if (response.ok) {
            alert('Grade submitted successfully!');
            bootstrap.Modal.getInstance(document.getElementById('gradeModal')).hide();
            // Refresh the assignment grading modal
            const assignmentId = document.querySelector('#gradeAssignmentModal .btn-primary')?.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
            if (assignmentId) {
                gradeAssignment(assignmentId);
            } else {
                location.reload();
            }
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to submit grade');
        }
    } catch (error) {
        console.error('Error submitting grade:', error);
        alert('An error occurred');
    }
}

// ==================== EDIT MATERIAL ====================

async function editMaterial(materialId) {
    try {
        console.log('Fetching material with ID:', materialId);
        const response = await fetch(`/api/v1/courses/materials/${materialId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const material = await response.json();
        console.log('Material data:', material);

        const modalHtml = `
            <div class="modal fade" id="editMaterialModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">Edit Material</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editMaterialForm">
                                <input type="hidden" id="editMaterialId" value="${material.id}">
                                <div class="mb-3">
                                    <label class="form-label">Title</label>
                                    <input type="text" class="form-control" id="editMaterialTitle" value="${escapeHtml(material.title || '')}" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Description</label>
                                    <textarea class="form-control" id="editMaterialDescription" rows="3">${escapeHtml(material.description || '')}</textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Type</label>
                                    <select class="form-select" id="editMaterialType">
                                        <option value="video" ${material.material_type === 'video' ? 'selected' : ''}>Video</option>
                                        <option value="document" ${material.material_type === 'document' ? 'selected' : ''}>Document</option>
                                        <option value="link" ${material.material_type === 'link' ? 'selected' : ''}>Link</option>
                                        <option value="file" ${material.material_type === 'file' ? 'selected' : ''}>File</option>
                                    </select>
                                </div>
                                <div class="mb-3" id="editUrlField">
                                    <label class="form-label">URL / Content</label>
                                    <input type="text" class="form-control" id="editMaterialUrl" value="${escapeHtml(material.content_url || '')}">
                                </div>
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="editMaterialPublished" ${material.is_published ? 'checked' : ''}>
                                    <label class="form-check-label">Published</label>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="saveMaterialEdit()">Save Changes</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('editMaterialModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('editMaterialModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading material:', error);
        alert('Failed to load material for editing. Please try again.');
    }
}

async function saveMaterialEdit() {
    const materialId = document.getElementById('editMaterialId').value;
    const materialData = {
        title: document.getElementById('editMaterialTitle').value,
        description: document.getElementById('editMaterialDescription').value,
        material_type: document.getElementById('editMaterialType').value,
        content_url: document.getElementById('editMaterialUrl').value,
        is_published: document.getElementById('editMaterialPublished').checked
    };
    
    console.log('Updating material:', materialData);
    
    try {
        const response = await fetch(`/api/v1/courses/materials/${materialId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(materialData)
        });
        
        if (response.ok) {
            alert('Material updated successfully!');
            bootstrap.Modal.getInstance(document.getElementById('editMaterialModal')).hide();
            // Refresh the page to show updated data
            window.location.reload();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to update material');
        }
    } catch (error) {
        console.error('Error updating material:', error);
        alert('An error occurred while updating the material');
    }
}

// ==================== MESSAGE STUDENT ====================

async function messageStudent(studentId) {
    try {
        // Get student details
        const response = await fetch(`/api/v1/users/${studentId}`);
        const student = await response.json();
        
        const modalHtml = `
            <div class="modal fade" id="messageStudentModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">Message Student: ${escapeHtml(student.full_name)}</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="messageForm">
                                <input type="hidden" id="messageStudentId" value="${studentId}">
                                <div class="mb-3">
                                    <label class="form-label">Subject</label>
                                    <input type="text" class="form-control" id="messageSubject" placeholder="Enter subject" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Message</label>
                                    <textarea class="form-control" id="messageContent" rows="5" placeholder="Type your message here..." required></textarea>
                                </div>
                                <div class="form-check mb-3">
                                    <input type="checkbox" class="form-check-input" id="sendEmailCopy">
                                    <label class="form-check-label">Send email copy to student</label>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="sendStudentMessage()">Send Message</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('messageStudentModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        new bootstrap.Modal(document.getElementById('messageStudentModal')).show();
        
    } catch (error) {
        console.error('Error loading student:', error);
        alert('Failed to load student information');
    }
}

async function sendStudentMessage() {
    const studentId = document.getElementById('messageStudentId').value;
    const subject = document.getElementById('messageSubject').value;
    const content = document.getElementById('messageContent').value;
    const sendEmail = document.getElementById('sendEmailCopy').checked;
    
    if (!subject || !content) {
        alert('Please enter both subject and message');
        return;
    }
    
    try {
        const response = await fetch('/api/v1/instructor/send-message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                student_id: studentId,
                subject: subject,
                content: content,
                send_email: sendEmail
            })
        });
        
        if (response.ok) {
            alert('Message sent successfully!');
            bootstrap.Modal.getInstance(document.getElementById('messageStudentModal')).hide();
            document.getElementById('messageForm').reset();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('An error occurred');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}