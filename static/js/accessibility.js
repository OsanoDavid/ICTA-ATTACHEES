/**
 * ICTA Portal - Accessibility Suite (v3)
 * Implements: Sidebar Push Layout & Multi-Color Visibility Themes
 */

(function() {
    let currentFontSize = 100;

    window.toggleAccPanel = function() {
        const panel = document.getElementById('accessibility-panel');
        const isOpening = !panel.classList.contains('active');
        if (isOpening) {
            panel.classList.add('active');
            document.body.classList.add('acc-sidebar-open');
        } else {
            panel.classList.remove('active');
            document.body.classList.remove('acc-sidebar-open');
        }
    };

    window.toggleAccSetting = function(setting) {
        const body = document.body;
        if (setting === 'dyslexic') body.classList.toggle('acc-dyslexic');
    };

    window.setTheme = function(theme) {
        const body = document.body;
        const themeClass = `theme-${theme}`;
        
        if (theme !== 'default' && body.classList.contains(themeClass)) {
            body.classList.remove(themeClass);
            speak("Default theme restored");
        } else {
            body.classList.remove('theme-red', 'theme-yellow', 'theme-blue');
            if (theme !== 'default') {
                body.classList.add(themeClass);
                speak(`${theme} high visibility theme activated`);
            } else {
                speak("Default theme restored");
            }
        }
    };

    window.changeFontSize = function(delta) {
        currentFontSize += delta;
        if (currentFontSize < 80) currentFontSize = 80;
        if (currentFontSize > 220) currentFontSize = 220;
        document.documentElement.style.fontSize = currentFontSize + '%';
        const display = document.getElementById('acc-font-display');
        if (display) display.textContent = currentFontSize + '%';
        speak('Font ' + currentFontSize + ' percent');
    };

    // Visual Display Modes — each mode has its OWN style tag so they stack independently
    const filterMap = {
        dark:     'invert(1) hue-rotate(180deg)',
        contrast: 'contrast(2.2) brightness(1.05)',
        grayscale:'grayscale(1)',
        sepia:    'sepia(0.85) brightness(1.05)'
    };
    const btnMap = {
        dark: 'btn-dark', contrast: 'btn-contrast',
        grayscale: 'btn-gray', sepia: 'btn-sepia'
    };
    const activeModes = {}; // track each mode independently

    window.toggleDisplayMode = function(mode) {
        const btn = document.getElementById(btnMap[mode]);

        if (activeModes[mode]) {
            // Already active — turn OFF this mode
            delete activeModes[mode];
            reapplyFilters();
            if (btn) btn.classList.remove('mode-active');
            speak(mode + ' off');
        } else {
            // Turn ON this mode
            activeModes[mode] = filterMap[mode];
            reapplyFilters();
            if (btn) btn.classList.add('mode-active');
            speak(mode + ' on');
        }
    };

    function buildCombinedFilter() {
        return Object.values(activeModes).join(' ');
    }

    function reapplyFilters() {
        const old = document.getElementById('acc-style-combined');
        if (old) old.remove();
        
        const combined = buildCombinedFilter();
        if (!combined) return;

        const style = document.createElement('style');
        style.id = 'acc-style-combined';
        style.textContent =
            'body > *:not(#accessibility-panel):not(#accessibility-widget):not(#voice-overlay) {' +
            '  filter: ' + combined + ' !important;' +
            '}';
        document.head.appendChild(style);
    }


    // Font Family Switcher
    window.changeFont = function(family) {
        const old = document.getElementById('acc-font-style');
        if (old) old.remove();
        if (!family) return;
        const style = document.createElement('style');
        style.id = 'acc-font-style';
        style.textContent = 'body, body * { font-family: ' + family + ' !important; }';
        document.head.appendChild(style);
        speak('Font changed');
    };

    // Voice Assistant Core
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = SpeechRecognition ? new SpeechRecognition() : null;
    const synth = window.speechSynthesis;

    window.speak = function(text) {
        if (!synth) return;
        synth.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 1.1;
        synth.speak(utter);
    };

    window.startVoiceAssistant = function() {
        if (!recognition) return;
        const overlay = document.getElementById('voice-overlay');
        overlay.style.display = 'flex';
        speak("Voice engine engaged. Command me.");
        recognition.start();

        recognition.onresult = function(event) {
            const command = event.results[0][0].transcript.toLowerCase();
            setTimeout(() => {
                processCommand(command);
                overlay.style.display = 'none';
            }, 800);
        };
        recognition.onerror = () => { overlay.style.display = 'none'; };
    };

    function processCommand(cmd) {
        if (cmd.includes('home')) window.location.href = "/";
        else if (cmd.includes('dashboard')) window.location.href = "/dashboard/";
        else if (cmd.includes('supervisor')) window.location.href = "/supervisor/";
        else if (cmd.includes('roster')) window.location.href = "/roster/bulk-assign/";
        else if (cmd.includes('red theme')) setTheme('red');
        else if (cmd.includes('yellow theme')) setTheme('yellow');
        else if (cmd.includes('blue theme')) setTheme('blue');
        else if (cmd.includes('default theme')) setTheme('default');
        else if (cmd.includes('bigger')) changeFontSize(20);
        else if (cmd.includes('smaller')) changeFontSize(-20);
        else speak("I recognize your voice but that path is not mapped yet.");
    }

    // ===== GEAR BUTTON SPIN ON CLICK =====
    // Fires a fast spin animation each time the button is clicked
    const _origToggle = window.toggleAccPanel;
    window.toggleAccPanel = function() {
        const btn = document.getElementById('accessibility-btn');
        if (btn) {
            btn.classList.add('spinning');
            // After the fast spin animation ends (0.5s), restore idle spin
            setTimeout(() => btn.classList.remove('spinning'), 520);
        }
        _origToggle();
    };

    // ===== PAGE LOAD, SPROUT & NAVIGATION INTERCEPTOR =====
    document.addEventListener("DOMContentLoaded", function() {
        const loader = document.getElementById('system-page-loader');

        // Collect all sproutable elements — any direct children of main sections
        function getSproutTargets() {
            const selectors = [
                'nav', 'header',
                'main > *', '.container > *', '.container-fluid > *',
                'section', 'article', '.card', '.row',
                'form', 'table', 'footer'
            ];
            const seen = new Set();
            const targets = [];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    // Skip the loader and accessibility elements themselves
                    if (!el.closest('#system-page-loader') &&
                        !el.closest('#accessibility-panel') &&
                        !el.closest('#accessibility-widget') &&
                        !seen.has(el)) {
                        seen.add(el);
                        targets.push(el);
                    }
                });
            });
            return targets;
        }

        // Phase 1: On DOMContentLoaded, immediately prep all sprout targets
        const sproutTargets = getSproutTargets();
        sproutTargets.forEach(el => {
            el.classList.add('sprout-auto');
        });

        // Phase 2: After loader delay, hide loader then sprout content in waves
        const LOADER_DURATION = 600; // ms — how long loader shows (keep spinner)
        const SPROUT_DELAY   = 30;  // ms between each sprout wave (fast cascade)

        setTimeout(() => {
            // Fade out loader
            if (loader) loader.classList.add('loaded');

            // After loader finishes fading, stagger sprout the content
            setTimeout(() => {
                sproutTargets.forEach((el, i) => {
                    setTimeout(() => {
                        el.classList.add('sprouted');
                    }, i * SPROUT_DELAY);
                });
            }, 80);
        }, LOADER_DURATION);

        // ===== NAVIGATION LINK INTERCEPTOR =====
        document.addEventListener('click', function(e) {
            const anchor = e.target.closest('a');
            if (anchor) {
                const href = anchor.getAttribute('href');
                const target = anchor.getAttribute('target');
                if (href &&
                    !href.startsWith('#') &&
                    !href.startsWith('javascript:') &&
                    !e.defaultPrevented &&
                    (!target || target === '_self') &&
                    !anchor.classList.contains('no-transition') &&
                    !anchor.hasAttribute('data-bs-toggle') &&
                    !anchor.hasAttribute('data-toggle')) {

                    e.preventDefault();
                    // Show loader
                    if (loader) loader.classList.remove('loaded');
                    // Un-sprout everything for the "leaving" feel
                    document.querySelectorAll('.sprouted').forEach(el => el.classList.remove('sprouted'));
                    // Navigate after spinner has spun beautifully
                    setTimeout(() => { window.location.href = href; }, 500);
                }
            }
        });

        // ===== FORM SUBMIT INTERCEPTOR =====
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form && !form.classList.contains('no-transition')) {
                e.preventDefault();
                if (loader) loader.classList.remove('loaded');
                document.querySelectorAll('.sprouted').forEach(el => el.classList.remove('sprouted'));
                setTimeout(() => { form.submit(); }, 500);
            }
        });
    });
})();


