// vpl_assignment.js - VPL Assignment functionality

let assignmentId = null;
let currentLanguage = null;
let codeEditor = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get assignment data from data attribute
    const assignmentData = document.getElementById('assignment-data');
    if (assignmentData) {
        try {
            const data = JSON.parse(assignmentData.textContent);
            assignmentId = data.assignment_id;
            currentLanguage = data.language;
            console.log('Assignment ID:', assignmentId, 'Language:', currentLanguage);
        } catch (e) {
            console.error('Error parsing assignment data:', e);
        }
    }
    
    // Initialize code editor
    initCodeEditor();
    
    // Set up keyboard shortcuts
    setupKeyboardShortcuts();
});

// Initialize code editor
function initCodeEditor() {
    const textarea = document.getElementById('codeEditor');
    if (textarea) {
        // Add line numbers (simple version)
        textarea.addEventListener('keydown', handleTabKey);
        
        // Optional: You can integrate a proper code editor like CodeMirror or Monaco here
        console.log('Code editor initialized');
    }
}

// Handle tab key in textarea
function handleTabKey(e) {
    if (e.key === 'Tab') {
        e.preventDefault();
        const textarea = e.target;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        
        // Insert 4 spaces at cursor position
        textarea.value = textarea.value.substring(0, start) + '    ' + textarea.value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + 4;
    }
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+Enter or Cmd+Enter to run code
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            runCode();
        }
        // Ctrl+S or Cmd+S to submit
        else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            submitCode();
        }
    });
}

// Run code in VPL sandbox
async function runCode() {
    const code = getCode();
    const language = currentLanguage;
    
    if (!code.trim()) {
        showError('Please enter some code to run');
        return;
    }
    
    // Show loading state
    const runButton = document.getElementById('runButton');
    const originalText = runButton?.innerHTML;
    if (runButton) {
        runButton.disabled = true;
        runButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Running...';
    }
    
    clearOutput();
    showOutput('Running code...', 'info');
    
    try {
        const response = await fetch('/api/v1/vpl/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                language: language
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayRunResult(result);
        } else {
            showError(result.detail || 'Failed to run code');
        }
    } catch (error) {
        console.error('Error running code:', error);
        showError('Network error. Please try again.');
    } finally {
        // Reset button state
        if (runButton) {
            runButton.disabled = false;
            runButton.innerHTML = originalText;
        }
    }
}

// Submit code assignment
async function submitCode() {
    const code = getCode();
    const language = currentLanguage;
    
    if (!code.trim()) {
        showError('Please enter some code before submitting');
        return;
    }
    
    if (!confirm('Are you sure you want to submit this assignment? You can only submit once.')) {
        return;
    }
    
    // Show loading state
    const submitButton = document.getElementById('submitButton');
    const originalText = submitButton?.innerHTML;
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
    }
    
    clearOutput();
    showOutput('Submitting assignment...', 'info');
    
    try {
        const response = await fetch(`/api/v1/vpl/assignments/${assignmentId}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                language: language
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displaySubmissionResult(result);
        } else {
            showError(result.detail || 'Failed to submit assignment');
        }
    } catch (error) {
        console.error('Error submitting code:', error);
        showError('Network error. Please try again.');
    } finally {
        // Reset button state
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }
    }
}

// Get code from editor
function getCode() {
    const textarea = document.getElementById('codeEditor');
    return textarea ? textarea.value : '';
}

// Set code in editor
function setCode(code) {
    const textarea = document.getElementById('codeEditor');
    if (textarea) {
        textarea.value = code;
    }
}

// Clear output area
function clearOutput() {
    const outputArea = document.getElementById('outputArea');
    if (outputArea) {
        outputArea.innerHTML = '';
    }
}

// Show output message
function showOutput(message, type = 'info') {
    const outputArea = document.getElementById('outputArea');
    if (outputArea) {
        const alertClass = type === 'error' ? 'alert-danger' : 
                          type === 'success' ? 'alert-success' : 
                          type === 'warning' ? 'alert-warning' : 'alert-info';
        
        const outputDiv = document.createElement('div');
        outputDiv.className = `alert ${alertClass} mb-2`;
        outputDiv.innerHTML = message;
        outputArea.appendChild(outputDiv);
    }
}

// Display run result
function displayRunResult(result) {
    if (result.error) {
        showOutput(`<strong>Error:</strong> ${escapeHtml(result.error)}`, 'error');
        return;
    }
    
    let output = '';
    
    if (result.output) {
        output += `<div class="mb-3">
            <strong>Output:</strong>
            <pre class="bg-dark text-light p-3 rounded mt-2">${escapeHtml(result.output)}</pre>
        </div>`;
    }
    
    if (result.execution_time) {
        output += `<div class="small text-muted mt-2">
            <i class="fas fa-clock"></i> Execution time: ${result.execution_time}ms
        </div>`;
    }
    
    showOutput(output, 'success');
}

// Display submission result
function displaySubmissionResult(result) {
    let output = '';
    
    // Score display
    const scoreColor = result.score >= 70 ? 'success' : result.score >= 50 ? 'warning' : 'danger';
    output += `
        <div class="alert alert-${scoreColor} text-center mb-4">
            <h4 class="mb-2">Score: ${result.score}%</h4>
            <p class="mb-0">Passed ${result.passed_tests} out of ${result.total_tests} tests</p>
        </div>
    `;
    
    // Test results
    if (result.test_results && result.test_results.length > 0) {
        output += '<h6 class="fw-bold mb-3">Test Results:</h6>';
        
        result.test_results.forEach((test, idx) => {
            const testClass = test.passed ? 'success' : 'danger';
            const icon = test.passed ? 'fa-check-circle' : 'fa-times-circle';
            
            output += `
                <div class="card mb-3 border-${testClass}">
                    <div class="card-header bg-${testClass} bg-opacity-10">
                        <i class="fas ${icon} text-${testClass} me-2"></i>
                        <strong>Test ${idx + 1}</strong>
                        <span class="badge bg-${testClass} float-end">${test.passed ? 'PASSED' : 'FAILED'}</span>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <strong>Input:</strong>
                            <pre class="bg-light p-2 rounded mt-1">${escapeHtml(test.test_input || '(no input)')}</pre>
                        </div>
                        <div class="mb-2">
                            <strong>Expected Output:</strong>
                            <pre class="bg-light p-2 rounded mt-1">${escapeHtml(test.expected_output)}</pre>
                        </div>
                        <div class="mb-2">
                            <strong>Your Output:</strong>
                            <pre class="bg-light p-2 rounded mt-1">${escapeHtml(test.actual_output || '(no output)')}</pre>
                        </div>
                        ${test.execution_time ? `<small class="text-muted"><i class="fas fa-clock"></i> ${test.execution_time}ms</small>` : ''}
                    </div>
                </div>
            `;
        });
    }
    
    showOutput(output, 'success');
}

// Load saved submission (if any)
async function loadSavedSubmission() {
    try {
        const response = await fetch(`/api/v1/vpl/assignments/${assignmentId}/submission`);
        if (response.ok) {
            const data = await response.json();
            if (data.code) {
                setCode(data.code);
                showOutput('Previous submission loaded. You can resubmit if allowed.', 'info');
            }
        }
    } catch (error) {
        console.error('Error loading saved submission:', error);
    }
}

// Reset code to starter code
async function resetCode() {
    if (!confirm('Reset code to starter template? Any unsaved changes will be lost.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/vpl/assignments/${assignmentId}/starter-code`);
        if (response.ok) {
            const data = await response.json();
            setCode(data.starter_code || '');
            showOutput('Code reset to starter template.', 'info');
        } else {
            showError('Failed to load starter code');
        }
    } catch (error) {
        console.error('Error resetting code:', error);
        showError('Failed to reset code');
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show error message
function showError(message) {
    showOutput(`<strong>Error:</strong> ${escapeHtml(message)}`, 'error');
}

// Show success message
function showSuccess(message) {
    showOutput(`<strong>Success:</strong> ${escapeHtml(message)}`, 'success');
}

// Make functions globally available for onclick handlers
window.runCode = runCode;
window.submitCode = submitCode;
window.resetCode = resetCode;