document.addEventListener('DOMContentLoaded', function() {
    // Initialize all auth functionality
    initPasswordToggles();
    initPasswordValidation();
    initSignInForm();
    initRegisterForm();
    initSocialLogin();
    initForgotPassword();
});

// ==================== PASSWORD TOGGLES ====================
function initPasswordToggles() {
    document.getElementById('toggleSigninPassword')?.addEventListener('click', function() {
        togglePassword('signinPassword', this);
    });
    document.getElementById('toggleRegisterPassword')?.addEventListener('click', function() {
        togglePassword('registerPassword', this);
    });
}

function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    const icon = button.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// ==================== PASSWORD VALIDATION ====================
function initPasswordValidation() {
    const registerPassword = document.getElementById('registerPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    const passwordMatch = document.getElementById('passwordMatch');
    
    if (!registerPassword || !confirmPassword) return;
    
    function validatePasswordMatch() {
        if (confirmPassword.value) {
            if (registerPassword.value === confirmPassword.value) {
                passwordMatch.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Passwords match</span>';
                confirmPassword.classList.remove('is-invalid');
                confirmPassword.classList.add('is-valid');
            } else {
                passwordMatch.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-circle"></i> Passwords do not match</span>';
                confirmPassword.classList.remove('is-valid');
                confirmPassword.classList.add('is-invalid');
            }
        } else {
            passwordMatch.innerHTML = '';
        }
    }
    
    registerPassword.addEventListener('input', validatePasswordMatch);
    confirmPassword.addEventListener('input', validatePasswordMatch);
}

// ==================== SIGN IN FORM ====================
function initSignInForm() {
    const signinForm = document.getElementById('signinForm');
    if (!signinForm) return;
    
    signinForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('signinEmail').value;
        const password = document.getElementById('signinPassword').value;
        const btn = document.getElementById('signinBtn');
        const spinner = document.getElementById('signinSpinner');
        const btnText = document.getElementById('signinText');
        
        setButtonLoading(btn, spinner, btnText, 'Signing in...');
        
        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);
            
            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                const sessionResponse = await fetch('/api/v1/auth/set-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        access_token: data.access_token,
                        refresh_token: data.refresh_token
                    })
                });
                
                if (sessionResponse.ok) {
                    window.location.href = '/dashboard';
                } else {
                    showError('Failed to set session');
                }
            } else {
                showError(data.detail || 'Invalid credentials');
            }
        } catch (error) {
            console.error('Sign in error:', error);
            showError('An error occurred. Please try again.');
        } finally {
            // Reset button state
            setButtonNormal(btn, spinner, btnText, 'Sign In');
        }
    });
}

// ==================== REGISTER FORM ====================
function initRegisterForm() {
    const registerForm = document.getElementById('registerForm');
    if (!registerForm) return;
    
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fullName = document.getElementById('registerFullName').value;
        const email = document.getElementById('registerEmail').value;
        const username = document.getElementById('registerUsername').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPwd = document.getElementById('confirmPassword').value;

        if (password !== confirmPwd) {
            showError('Passwords do not match');
            return;
        }

        if (password.length < 8) {
            showError('Password must be at least 8 characters long');
            return;
        }
        
        const btn = document.getElementById('registerBtn');
        const spinner = document.getElementById('registerSpinner');
        const btnText = document.getElementById('registerText');

        setButtonLoading(btn, spinner, btnText, 'Creating account...');
        
        try {
            const response = await fetch('/api/v1/auth/register/student', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    username: username,
                    full_name: fullName
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showSuccess('Account created successfully! You can now sign in.');
                document.getElementById('signin-tab').click();
                document.getElementById('registerForm').reset();
                document.getElementById('confirmPassword').classList.remove('is-valid', 'is-invalid');
                document.getElementById('passwordMatch').innerHTML = '';
            } else {
                showError(data.detail || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            showError('An error occurred. Please try again.');
        } finally {
            setButtonNormal(btn, spinner, btnText, 'Create Account');
        }
    });
}

// ==================== SOCIAL LOGIN ====================
function initSocialLogin() {
    function socialLogin(provider) {
        window.location.href = `/api/v1/auth/login/${provider}`;
    }
    
    document.getElementById('githubLoginBtn')?.addEventListener('click', () => socialLogin('github'));
    document.getElementById('googleLoginBtn')?.addEventListener('click', () => socialLogin('google'));
    document.getElementById('githubRegisterBtn')?.addEventListener('click', () => socialLogin('github'));
    document.getElementById('googleRegisterBtn')?.addEventListener('click', () => socialLogin('google'));
}

// ==================== FORGOT PASSWORD ====================
function initForgotPassword() {
    const forgotForm = document.getElementById('forgotPasswordForm');
    if (!forgotForm) return;
    
    forgotForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('resetEmail').value;
        const submitBtn = forgotForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sending...';
        
        try {
            const response = await fetch('/api/v1/auth/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email })
            });
            
            if (response.ok) {
                bootstrap.Modal.getInstance(document.getElementById('forgotPasswordModal')).hide();
                showSuccess('Password reset link sent to your email!');
                forgotForm.reset();
            } else {
                const data = await response.json();
                showError(data.detail || 'Failed to send reset link');
            }
        } catch (error) {
            console.error('Forgot password error:', error);
            showError('An error occurred. Please try again.');
        } finally {
            // Reset button
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

// ==================== HELPER FUNCTIONS ====================

function setButtonLoading(btn, spinner, btnText, text) {
    btn.disabled = true;
    spinner.classList.remove('d-none');
    btnText.textContent = text;
}

function setButtonNormal(btn, spinner, btnText, text) {
    btn.disabled = false;
    spinner.classList.add('d-none');
    btnText.textContent = text;
}

function showSuccess(message) {
    const modalEl = document.getElementById('successModal');
    if (!modalEl) return;
    
    document.getElementById('successMessage').textContent = message;
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    
    // Auto hide after 3 seconds
    setTimeout(() => modal.hide(), 3000);
}

function showError(message) {
    const modalEl = document.getElementById('errorModal');
    if (!modalEl) return;
    
    document.getElementById('errorMessage').textContent = message;
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    setTimeout(() => modal.hide(), 3000);
}

// Session Refresh Module
const SessionManager = {
    refreshInterval: null,
    refreshThreshold: 5 * 60 * 1000,
    checkInterval: 60 * 1000,
    
    init() {
        this.setupTokenRefresh();
        this.setupActivityTracking();
    },
    
    setupTokenRefresh() {
        setInterval(() => this.checkAndRefreshToken(), this.checkInterval);
        ['click', 'mousemove', 'keypress'].forEach(event => {
            document.addEventListener(event, () => this.debouncedRefresh());
        });
    },
    
    debouncedRefresh: _.debounce(function() {
        SessionManager.checkAndRefreshToken();
    }, 5000),
    
    async checkAndRefreshToken() {
        const token = this.getToken();
        if (!token) return;
        
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const expiryTime = payload.exp * 1000; 
            const now = Date.now();
            const timeUntilExpiry = expiryTime - now;
            if (timeUntilExpiry < this.refreshThreshold && timeUntilExpiry > 0) {
                await this.refreshToken();
            }
        } catch (error) {
            console.error('Error checking token expiry:', error);
        }
    },
    
    async refreshToken() {
        try {
            const refreshToken = this.getRefreshToken();
            if (!refreshToken) return;
            
            const response = await fetch('/api/v1/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    refresh_token: refreshToken
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.setToken(data.access_token, data.refresh_token);
                console.log('Token refreshed successfully');
            } else {
                window.location.href = '/login?session=expired';
            }
        } catch (error) {
            console.error('Error refreshing token:', error);
        }
    },
    
    getToken() {
        return document.cookie.replace(/(?:(?:^|.*;\s*)access_token\s*=\s*([^;]*).*$)|^.*$/, "$1");
    },
    getRefreshToken() {
        return document.cookie.replace(/(?:(?:^|.*;\s*)refresh_token\s*=\s*([^;]*).*$)|^.*$/, "$1");
    },
    
    setToken(accessToken, refreshToken) {
        const secure = window.location.protocol === 'https:';
        
        document.cookie = `access_token=${accessToken}; path=/; max-age=${60*60*24*7}; ${secure ? 'secure;' : ''} samesite=lax`;
        
        if (refreshToken) {
            document.cookie = `refresh_token=${refreshToken}; path=/; max-age=${60*60*24*30}; ${secure ? 'secure;' : ''} samesite=lax`;
        }
    },
    
    setupActivityTracking() {
        let activityTimer;
        const resetActivityTimer = () => {
            clearTimeout(activityTimer);
            activityTimer = setTimeout(() => {
                this.checkAndRefreshToken();
            }, 10 * 60 * 1000); // Check after 10 minutes of inactivity
        };
        
        ['click', 'mousemove', 'keypress', 'scroll'].forEach(event => {
            document.addEventListener(event, resetActivityTimer);
        });
        
        resetActivityTimer();
    }
};

// Initialize session manager
SessionManager.init();
