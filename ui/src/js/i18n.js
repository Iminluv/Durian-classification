let currentLanguage = localStorage.getItem('app_lang') || 'vi';
let translations = { en: {}, vi: {} };

async function initI18n() {
    try {
        // Load locales JSON files using standard fetch API
        const [enRes, viRes] = await Promise.all([
            fetch('locales/en.json').then(r => r.json()),
            fetch('locales/vi.json').then(r => r.json())
        ]);
        translations.en = enRes;
        translations.vi = viRes;
        logger.log("Locales loaded successfully.");
        updateDOM();
    } catch (e) {
        console.error("Failed to load i18n locales:", e);
    }
}

function t(key) {
    const langDict = translations[currentLanguage] || {};
    return langDict[key] || key;
}

function setLanguage(lang) {
    if (lang === 'en' || lang === 'vi') {
        currentLanguage = lang;
        localStorage.setItem('app_lang', lang);
        updateDOM();
        
        // Notify backend about language change if needed
        fetch('http://127.0.0.1:8000/api/config/rules') // placeholder or config
            .catch(() => {});
    }
}

function updateDOM() {
    // Standard data-i18n attribute translation updates
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.textContent = t(key);
    });

    const placeholders = document.querySelectorAll('[data-i18n-placeholder]');
    placeholders.forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        el.setAttribute('placeholder', t(key));
    });
}

// Simple Logger placeholder for frontend
const logger = {
    log: (...args) => console.log("[i18n]", ...args)
};

// Export to window for global access
window.t = t;
window.setLanguage = setLanguage;
window.currentLanguage = () => currentLanguage;
window.initI18n = initI18n;
