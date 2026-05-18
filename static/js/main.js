(function() {
    'use strict';

    const ready = (callback) => {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    };

    ready(() => {
        initMobileMenu();
        initToasts();
    });

    function initMobileMenu() {
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');

        if (!mobileMenuBtn || !sidebar || !sidebarOverlay) {
            return;
        }

        const openSidebar = () => {
            sidebar.classList.add('open');
            sidebarOverlay.classList.add('active');
            document.body.classList.add('sidebar-open');
            mobileMenuBtn.setAttribute('aria-expanded', 'true');
            sidebarOverlay.setAttribute('aria-hidden', 'false');
        };

        const closeSidebar = () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
            document.body.classList.remove('sidebar-open');
            mobileMenuBtn.setAttribute('aria-expanded', 'false');
            sidebarOverlay.setAttribute('aria-hidden', 'true');
        };

        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
        });

        sidebarOverlay.addEventListener('click', closeSidebar);

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeSidebar();
            }
        });

        sidebar.querySelectorAll('.nav-link').forEach((link) => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    closeSidebar();
                }
            });
        });

        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                closeSidebar();
            }
        });
    }

    function initToasts() {
        window.setTimeout(() => {
            document.querySelectorAll('.toast').forEach((toast) => {
                window.setTimeout(() => {
                    toast.style.animation = 'slideOut 0.3s ease forwards';
                    window.setTimeout(() => toast.remove(), 300);
                }, 4000);
            });
        }, 100);
    }
})();
