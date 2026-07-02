// static/js/limit_recent_actions.js
document.addEventListener("DOMContentLoaded", function () {
    // Locate the Django Admin Recent Actions wrapper panel
    const recentBox = document.querySelector('.timeline') || document.querySelector('#content-related');
    
    if (recentBox) {
        // Find all individual log entries inside the panel
        const entries = recentBox.children;
        
        // If there are more than 5 elements, hide the rest
        if (entries.length > 5) {
            for (let i = 5; i < entries.length; i++) {
                entries[i].style.display = 'none';
            }
            
            // Create a clean user-friendly toggle wrapper block
            const toggleContainer = document.createElement('div');
            toggleContainer.className = 'text-center my-3';
            
            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'btn btn-xs btn-outline-secondary px-3';
            toggleBtn.innerHTML = '<i class="fas fa-chevron-down mr-1"></i> View More Actions';
            
            toggleContainer.appendChild(toggleBtn);
            recentBox.parentNode.appendChild(toggleContainer);
            
            // Handle arrow flips and smooth view transitions
            let isExpanded = false;
            toggleBtn.addEventListener('click', function () {
                isExpanded = !isExpanded;
                for (let i = 5; i < entries.length; i++) {
                    entries[i].style.display = isExpanded ? 'block' : 'none';
                }
                toggleBtn.innerHTML = isExpanded ? 
                    '<i class="fas fa-chevron-up mr-1"></i> View Less Actions' : 
                    '<i class="fas fa-chevron-down mr-1"></i> View More Actions';
            });
        }
    }
});
document.addEventListener("DOMContentLoaded", function () {
    // -------------------------------------------------------------
    // 1. LIMIT RECENT ACTIONS AND ADD TOGGLE ARROWS
    // -------------------------------------------------------------
    const recentBox = document.querySelector('.timeline') || document.querySelector('#content-related');
    
    if (recentBox) {
        const entries = recentBox.children;
        
        // Target an initial slice of 5 items
        if (entries.length > 5) {
            for (let i = 5; i < entries.length; i++) {
                entries[i].style.display = 'none';
            }
            
            // Build the control wrapper
            const toggleContainer = document.createElement('div');
            toggleContainer.className = 'text-center my-3';
            
            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'btn btn-xs btn-outline-secondary px-3';
            toggleBtn.innerHTML = '<i class="fas fa-chevron-down mr-1"></i> View More Actions';
            
            toggleContainer.appendChild(toggleBtn);
            recentBox.parentNode.appendChild(toggleContainer);
            
            let isExpanded = false;
            toggleBtn.addEventListener('click', function () {
                isExpanded = !isExpanded;
                for (let i = 5; i < entries.length; i++) {
                    entries[i].style.display = isExpanded ? 'block' : 'none';
                }
                // Toggle between down and up arrows dynamically
                toggleBtn.innerHTML = isExpanded ? 
                    '<i class="fas fa-chevron-up mr-1"></i> View Less Actions' : 
                    '<i class="fas fa-chevron-down mr-1"></i> View More Actions';
            });
        }
    }

    // -------------------------------------------------------------
    // 2. ENFORCE REMOVAL OF JAZZMIN VERSION FOOTER
    // -------------------------------------------------------------
    const versionFooters = document.querySelectorAll('.main-footer .float-right, .main-footer strong + span');
    versionFooters.forEach(footer => {
        if (footer) {
            footer.setAttribute('style', 'display: none !important;');
        }
    });
});