// vpl_playground.js - VPL Playground functionality

let currentLanguage = 'python';
let currentSnippets = [];

// Hardcoded languages
const SUPPORTED_LANGUAGES = [
    {"id": "python", "name": "Python", "version": "3.11", "icon": "fab fa-python"},
    {"id": "javascript", "name": "JavaScript", "version": "ES2022", "icon": "fab fa-js"},
    {"id": "java", "name": "Java", "version": "17", "icon": "fab fa-java"},
    {"id": "cpp", "name": "C++", "version": "17", "icon": "fas fa-code"}
];

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('VPL Playground initializing...');
    loadLanguages();
    loadDefaultCode();
    setupKeyboardShortcuts();
});

// Load supported languages
function loadLanguages() {
    console.log('Loading languages...');
    
    const container = document.getElementById('languageList');
    if (!container) {
        console.error('Language container not found');
        return;
    }
    
    container.innerHTML = '';
    
    SUPPORTED_LANGUAGES.forEach(lang => {
        const langBtn = document.createElement('div');
        langBtn.className = 'language-btn p-3 rounded-3 border text-center';
        langBtn.style.cursor = 'pointer';
        langBtn.style.transition = 'all 0.3s ease';
        langBtn.style.width = '100px';
        langBtn.setAttribute('data-language', lang.id);
        langBtn.innerHTML = `
            <i class="${lang.icon} fa-2x mb-2 d-block"></i>
            <strong>${lang.name}</strong>
            <small class="d-block text-muted">${lang.version}</small>
        `;
        
        langBtn.onclick = (function(langId, langName) {
            return function() { 
                changeLanguage(langId, langName); 
            };
        })(lang.id, lang.name);
        
        container.appendChild(langBtn);
    });
    
    // Set active class on default language
    const defaultBtn = container.querySelector('[data-language="python"]');
    if (defaultBtn) {
        defaultBtn.classList.add('active', 'border-primary', 'bg-primary', 'bg-opacity-10');
    }
    
    console.log('Languages loaded successfully');
}

// Change programming language
function changeLanguage(languageId, languageName) {
    console.log('Changing language to:', languageId);
    currentLanguage = languageId;
    
    // Update active state
    document.querySelectorAll('.language-btn').forEach(btn => {
        btn.classList.remove('active', 'border-primary', 'bg-primary', 'bg-opacity-10');
        if (btn.getAttribute('data-language') === languageId) {
            btn.classList.add('active', 'border-primary', 'bg-primary', 'bg-opacity-10');
        }
    });
    
    // Update language display in save modal
    const snippetLanguage = document.getElementById('snippetLanguage');
    if (snippetLanguage) {
        snippetLanguage.value = languageName;
    }
    
    // Load default code for this language
    loadDefaultCode();
}

// Load default code template
function loadDefaultCode() {
    const editor = document.getElementById('codeEditor');
    if (!editor) return;
    
    const templates = {
        python: 'print("Hello, World!")\n\nname = input("Enter your name: ")\nprint(f"Hello, {name}!")',
        javascript: 'console.log("Hello, World!");\n\nconst name = prompt("Enter your name:");\nconsole.log(`Hello, ${name}!`);',
        java: 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
        cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}'
    };
    
    editor.value = templates[currentLanguage] || templates.python;
}

// Load example code
function loadExample(language, example) {
    if (language !== currentLanguage) {
        // Find and click the language button
        const langBtns = document.querySelectorAll('.language-btn');
        for (let btn of langBtns) {
            if (btn.innerText.toLowerCase().includes(language)) {
                btn.click();
                break;
            }
        }
    }
    
    const examples = {
        hello: {
            python: 'print("Hello, World!")',
            javascript: 'console.log("Hello, World!");',
            java: 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
            cpp: '#include <iostream>\nusing namespace std;\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}'
        },
        fibonacci: {
            python: 'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nn = 10\nprint(f"First {n} Fibonacci numbers:")\nfor i in range(n):\n    print(fibonacci(i), end=" ")',
            javascript: 'function fibonacci(n) {\n    if (n <= 1) return n;\n    return fibonacci(n-1) + fibonacci(n-2);\n}\n\nconst n = 10;\nconsole.log(`First ${n} Fibonacci numbers:`);\nfor (let i = 0; i < n; i++) {\n    process.stdout.write(fibonacci(i) + " ");\n}'
        },
        factorial: {
            python: 'def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)\n\nn = 5\nprint(f"Factorial of {n} is {factorial(n)}")',
            javascript: 'function factorial(n) {\n    if (n <= 1) return 1;\n    return n * factorial(n-1);\n}\n\nconst n = 5;\nconsole.log(`Factorial of ${n} is ${factorial(n)}`);'
        }
    };
    
    const editor = document.getElementById('codeEditor');
    if (editor && examples[example] && examples[example][currentLanguage]) {
        editor.value = examples[example][currentLanguage];
    } else if (editor) {
        editor.value = '// Example not available for this language';
    }
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            runPlaygroundCode();
        } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveCurrentCode();
        }
    });
}

// Run code in playground
async function runPlaygroundCode() {
    const editor = document.getElementById('codeEditor');
    const stdinInput = document.getElementById('stdinInput');
    
    const code = editor ? editor.value : '';
    const stdin = stdinInput ? stdinInput.value : '';
    
    if (!code.trim()) {
        alert('Please enter some code to run');
        return;
    }
    
    const runButton = document.getElementById('runButton');
    const originalText = runButton ? runButton.innerHTML : '';
    
    if (runButton) {
        runButton.disabled = true;
        runButton.innerHTML = 'Running...';
    }
    
    clearOutput();
    showOutputMessage('Running code...', 'info');
    
    try {
        const response = await fetch('/api/v1/vpl/playground/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: code,
                language: currentLanguage,
                stdin: stdin
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayResult(result);
        } else {
            showOutputMessage(result.detail || 'Failed to run code', 'error');
        }
    } catch (error) {
        console.error('Error running code:', error);
        showOutputMessage('Network error. Please try again.', 'error');
    } finally {
        if (runButton) {
            runButton.disabled = false;
            runButton.innerHTML = originalText;
        }
    }
}

// Display result
function displayResult(result) {
    const outputArea = document.getElementById('outputArea');
    if (!outputArea) return;
    
    let html = '';
    
    if (result.error) {
        html += '<div class="alert alert-danger mb-2"><strong>Error:</strong> ' + escapeHtml(result.error) + '</div>';
    }
    
    if (result.output) {
        html += '<div class="mb-2"><strong>Output:</strong><pre class="bg-dark text-light p-3 rounded mt-2">' + escapeHtml(result.output) + '</pre></div>';
    }
    
    if (result.execution_time) {
        html += '<div class="small text-muted mt-2"><i class="fas fa-clock"></i> Execution time: ' + result.execution_time + 'ms</div>';
    }
    
    outputArea.innerHTML = html;
}

// Show output message
function showOutputMessage(message, type) {
    const outputArea = document.getElementById('outputArea');
    if (!outputArea) return;
    
    if (type === 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-info mb-2';
        alertDiv.innerHTML = message;
        outputArea.appendChild(alertDiv);
    } else {
        outputArea.innerHTML = '<div class="alert alert-danger mb-2">' + message + '</div>';
    }
}

// Clear output area
function clearOutput() {
    const outputArea = document.getElementById('outputArea');
    if (outputArea) {
        outputArea.innerHTML = '';
    }
}

// Reset editor to default
function resetEditor() {
    if (confirm('Reset to default code? Any unsaved changes will be lost.')) {
        loadDefaultCode();
        clearOutput();
    }
}

// Save current code as snippet
function saveCurrentCode() {
    const editor = document.getElementById('codeEditor');
    const code = editor ? editor.value : '';
    
    if (!code.trim()) {
        alert('No code to save');
        return;
    }
    
    const titleInput = document.getElementById('snippetTitle');
    if (titleInput) {
        titleInput.value = 'Untitled';
    }
    
    const snippetLanguage = document.getElementById('snippetLanguage');
    if (snippetLanguage) {
        const activeLang = document.querySelector('.language-btn.active strong');
        snippetLanguage.value = activeLang ? activeLang.innerText : 'Python';
    }
    
    const saveModal = new bootstrap.Modal(document.getElementById('saveSnippetModal'));
    if (saveModal) {
        saveModal.show();
    }
}

// Save snippet to database
async function saveSnippet() {
    const titleInput = document.getElementById('snippetTitle');
    const editor = document.getElementById('codeEditor');
    
    const title = titleInput ? titleInput.value : '';
    const code = editor ? editor.value : '';
    
    if (!title.trim()) {
        alert('Please enter a title');
        return;
    }
    
    try {
        const response = await fetch('/api/v1/vpl/playground/snippets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                code: code,
                language: currentLanguage
            })
        });
        
        if (response.ok) {
            const saveModal = bootstrap.Modal.getInstance(document.getElementById('saveSnippetModal'));
            if (saveModal) saveModal.hide();
            alert('Snippet saved successfully!');
            loadSnippets();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to save snippet');
        }
    } catch (error) {
        console.error('Error saving snippet:', error);
        alert('An error occurred');
    }
}

// Load user's snippets
async function loadSnippets() {
    try {
        const response = await fetch('/api/v1/vpl/playground/snippets');
        const snippets = await response.json();
        currentSnippets = snippets;
        
        const container = document.getElementById('snippetsList');
        if (!container) return;
        
        if (!snippets || snippets.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No saved snippets yet.</p>
                    <button class="btn btn-primary btn-sm" onclick="saveCurrentCode()">
                        <i class="fas fa-plus me-2"></i>Create Your First Snippet
                    </button>
                </div>
            `;
        } else {
            container.innerHTML = snippets.map(snippet => `
                <div class="snippet-card p-3 mb-2 border rounded">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1" onclick="loadSnippet('${snippet.id}')" style="cursor: pointer;">
                            <h6 class="fw-bold mb-1">${escapeHtml(snippet.title)}</h6>
                            <small class="text-muted">
                                <i class="fas fa-code me-1"></i>${snippet.language}
                                <i class="fas fa-clock ms-2 me-1"></i>${snippet.updated_at ? snippet.updated_at.slice(0, 10) : 'Recently'}
                            </small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteSnippet('${snippet.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading snippets:', error);
    }
}

// Load a saved snippet
async function loadSnippet(snippetId) {
    try {
        const response = await fetch(`/api/v1/vpl/playground/snippets/${snippetId}`);
        const snippet = await response.json();
        
        // Change language if needed
        if (snippet.language !== currentLanguage) {
            const langBtns = document.querySelectorAll('.language-btn');
            for (let btn of langBtns) {
                if (btn.innerText.toLowerCase().includes(snippet.language)) {
                    btn.click();
                    break;
                }
            }
        }
        
        const editor = document.getElementById('codeEditor');
        if (editor) {
            editor.value = snippet.code;
        }
        
        const snippetsModal = document.getElementById('snippetsModal');
        if (snippetsModal) {
            const modal = bootstrap.Modal.getInstance(snippetsModal);
            if (modal) modal.hide();
        }
        
        showOutputMessage(`Loaded snippet: ${snippet.title}`, 'info');
    } catch (error) {
        console.error('Error loading snippet:', error);
        alert('Failed to load snippet');
    }
}

// Delete a snippet
async function deleteSnippet(snippetId) {
    if (!confirm('Delete this snippet?')) return;
    
    try {
        const response = await fetch(`/api/v1/vpl/playground/snippets/${snippetId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadSnippets();
            alert('Snippet deleted successfully');
        } else {
            alert('Failed to delete snippet');
        }
    } catch (error) {
        console.error('Error deleting snippet:', error);
        alert('An error occurred');
    }
}

// Show snippets modal
function showSnippetsModal() {
    loadSnippets();
    const snippetsModal = document.getElementById('snippetsModal');
    if (snippetsModal) {
        new bootstrap.Modal(snippetsModal).show();
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Make all functions globally available
window.runPlaygroundCode = runPlaygroundCode;
window.clearOutput = clearOutput;
window.resetEditor = resetEditor;
window.saveCurrentCode = saveCurrentCode;
window.loadExample = loadExample;
window.showSnippetsModal = showSnippetsModal;
window.changeLanguage = changeLanguage;
window.saveSnippet = saveSnippet;
window.loadSnippet = loadSnippet;
window.deleteSnippet = deleteSnippet;