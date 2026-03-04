// ============================================
// MOBILE BURGER MENU
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (mobileMenuBtn && sidebar && sidebarOverlay) {
        // Toggle sidebar
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');
            document.body.classList.toggle('sidebar-open');
        });
        
        // Close sidebar when clicking overlay
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
            document.body.classList.remove('sidebar-open');
        });
        
        // Close sidebar when clicking nav link on mobile
        const navLinks = sidebar.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('active');
                    sidebarOverlay.classList.remove('active');
                    document.body.classList.remove('sidebar-open');
                }
            });
        });
    }
});

// ============================================
// AUTO-DISMISS TOASTS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    });
});

// Animation for slideOut
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(style);

// ============================================
// LIVE UPDATES (Auto-refresh content)
// ============================================

// Auto-refresh dashboard stats every 30 seconds
if (window.location.pathname === '/dashboard/') {
    setInterval(function() {
        fetch(window.location.href, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update stat cards
            const statCards = document.querySelectorAll('.stat-value');
            const newStatCards = doc.querySelectorAll('.stat-value');
            statCards.forEach((card, index) => {
                if (newStatCards[index]) {
                    card.textContent = newStatCards[index].textContent;
                }
            });
        })
        .catch(err => console.log('Auto-refresh error:', err));
    }, 30000);
}

// Auto-refresh task list every 10 seconds
if (window.location.pathname === '/my-tasks/' || window.location.pathname.includes('/projects/')) {
    setInterval(function() {
        fetch(window.location.href, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update task table
            const taskTable = document.querySelector('.task-table tbody');
            const newTaskTable = doc.querySelector('.task-table tbody');
            if (taskTable && newTaskTable) {
                taskTable.innerHTML = newTaskTable.innerHTML;
            }
            
            // Update task list
            const taskList = document.querySelector('.task-list');
            const newTaskList = doc.querySelector('.task-list');
            if (taskList && newTaskList) {
                taskList.innerHTML = newTaskList.innerHTML;
            }
        })
        .catch(err => console.log('Auto-refresh error:', err));
    }, 10000);
}

// Auto-refresh comments on task detail page
if (window.location.pathname.includes('/tasks/') && window.location.pathname.includes('/detail')) {
    setInterval(function() {
        fetch(window.location.href, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            const comments = document.querySelector('.comments-list');
            const newComments = doc.querySelector('.comments-list');
            if (comments && newComments) {
                comments.innerHTML = newComments.innerHTML;
            }
        })
        .catch(err => console.log('Comments refresh error:', err));
    }, 5000);
}

// ============================================
// SMOOTH SCROLL
// ============================================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ============================================
// FORM VALIDATION
// ============================================

document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.style.borderColor = '#ef4444';
                field.focus();
            } else {
                field.style.borderColor = '';
            }
        });
        
        if (!isValid) {
            e.preventDefault();
        }
    });
});

// ============================================
// RESPONSIVE TABLE (Swipe on mobile)
// ============================================

if (window.innerWidth <= 768) {
    const tables = document.querySelectorAll('.task-table');
    tables.forEach(table => {
        table.style.overflowX = 'auto';
        table.style.webkitOverflowScrolling = 'touch';
    });
}

console.log('TaskFlow initialized ✓');
