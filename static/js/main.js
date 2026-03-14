// ============================================
// MOBILE MENU - ФИНАЛЬНОЕ РАБОЧЕЕ РЕШЕНИЕ
// Замените ВЕСЬ static/js/main.js на этот код
// ============================================

(function() {
    'use strict';

    console.log('🚀 TaskFlow loading...');

    // Ждём полной загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMobileMenu);
    } else {
        initMobileMenu();
    }

    function initMobileMenu() {
        console.log('🔧 Initializing mobile menu...');

        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');

        console.log('Elements check:');
        console.log('  Button:', mobileMenuBtn ? '✅' : '❌', mobileMenuBtn);
        console.log('  Sidebar:', sidebar ? '✅' : '❌', sidebar);
        console.log('  Overlay:', sidebarOverlay ? '✅' : '❌', sidebarOverlay);

        if (!mobileMenuBtn || !sidebar || !sidebarOverlay) {
            console.error('❌ Mobile menu elements missing!');
            return;
        }

        console.log('✅ All elements found!');

        // Функция открытия/закрытия
        function toggleSidebar() {
            const isOpen = sidebar.classList.contains('open');
            console.log('🍔 Toggle sidebar - current:', isOpen ? 'OPEN' : 'CLOSED');

            if (isOpen) {
                closeSidebar();
            } else {
                openSidebar();
            }
        }

        function openSidebar() {
            console.log('→ Opening sidebar');
            sidebar.classList.add('open');
            sidebarOverlay.classList.add('active');
            document.body.classList.add('sidebar-open');
        }

        function closeSidebar() {
            console.log('→ Closing sidebar');
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
            document.body.classList.remove('sidebar-open');
        }

        // Event listeners
        mobileMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🍔 Burger button CLICKED!');
            toggleSidebar();
        }, false);

        // Также слушаем touchstart для мобильных
        mobileMenuBtn.addEventListener('touchstart', function(e) {
            e.preventDefault();
            console.log('👆 Burger button TOUCHED!');
            toggleSidebar();
        }, { passive: false });

        // Закрытие по клику на overlay
        sidebarOverlay.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('📱 Overlay clicked');
            closeSidebar();
        });

        sidebarOverlay.addEventListener('touchstart', function(e) {
            e.preventDefault();
            console.log('👆 Overlay touched');
            closeSidebar();
        }, { passive: false });

        // Закрытие по клику на ссылку
        const navLinks = sidebar.querySelectorAll('.nav-link');
        console.log('📋 Found', navLinks.length, 'nav links');

        navLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    console.log('🔗 Nav link clicked on mobile');
                    closeSidebar();
                }
            });
        });

        console.log('✅ Mobile menu initialized successfully!');

        // Тест (можно удалить потом)
        console.log('🧪 Test: Sidebar classes:', sidebar.className);
        console.log('🧪 Test: Sidebar left position:', getComputedStyle(sidebar).left);
    }

    // Auto-dismiss toasts
    setTimeout(function() {
        const toasts = document.querySelectorAll('.toast');
        toasts.forEach(function(toast) {
            setTimeout(function() {
                toast.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(function() {
                    toast.remove();
                }, 300);
            }, 4000);
        });
    }, 100);

    console.log('✅ TaskFlow loaded successfully!');
})();