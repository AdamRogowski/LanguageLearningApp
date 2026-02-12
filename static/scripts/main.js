/**
 * Dropdown functionality
 * Handles dropdown menus throughout the application
 */
function initializeDropdowns() {
    const dropdownBtns = document.querySelectorAll('.dropdown-btn');
    
    dropdownBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const menuId = this.dataset.menu;
            const menu = document.getElementById(menuId);
            
            // Hide all other menus
            document.querySelectorAll('.dropdown-menu').forEach(m => {
                if (m !== menu) m.style.display = 'none';
            });
            
            // Toggle this menu
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        });

        // Prevent drag on dropdown buttons
        btn.addEventListener('mousedown', function(e) {
            e.stopPropagation();
        });
    });
    
    // Close menus when clicking outside
    document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown-menu').forEach(m => m.style.display = 'none');
    });
}

/**
 * Word item navigation
 * Makes word items clickable for navigation
 */
function initializeWordNavigation() {
    const wordItems = document.querySelectorAll('.word-item');
    
    wordItems.forEach(item => {
        item.addEventListener('click', function() {
            const url = this.dataset.url;
            if (url) {
                window.location.href = url;
            }
        });
    });
}

/**
 * Practice URL update
 * Updates practice form action based on reverse checkbox
 */
function updatePracticeUrl(normalUrl, reverseUrl) {
    const checkbox = document.getElementById('reverse-practice');
    const form = document.getElementById('practice-form');
    
    if (!checkbox || !form) return;
    
    if (checkbox.checked) {
        form.action = reverseUrl;
    } else {
        form.action = normalUrl;
    }
}

/**
 * Auto-focus first input
 * Focuses the first input field on page load
 */
function autoFocusFirstInput() {
    const firstInput = document.querySelector('input[type="text"], textarea');
    if (firstInput && !firstInput.value) {
        firstInput.focus();
    }
}

/**
 * Initialize all common functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeDropdowns();
    initializeWordNavigation();
});

// Export functions for use in templates
window.LLApp = window.LLApp || {};
window.LLApp.initializeDropdowns = initializeDropdowns;
window.LLApp.initializeWordNavigation = initializeWordNavigation;
window.LLApp.updatePracticeUrl = updatePracticeUrl;
window.LLApp.autoFocusFirstInput = autoFocusFirstInput;
