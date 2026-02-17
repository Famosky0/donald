(function () {
  const THEME_KEY = 'theme';
  const root = document.documentElement;
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

  function getStoredTheme() {
    return localStorage.getItem(THEME_KEY) || 'system';
  }

  function shouldUseDark(setting) {
    if (setting === 'dark') return true;
    if (setting === 'light') return false;
    return mediaQuery.matches;
  }

  function applyTheme(setting) {
    root.classList.toggle('dark', shouldUseDark(setting));
  }

  function syncThemeInputs(scope) {
    const target = scope || document;
    const radios = target.querySelectorAll('input[name="theme"]');
    if (!radios.length) return;

    const current = getStoredTheme();
    radios.forEach(radio => {
      radio.checked = radio.value === current;

      if (radio.dataset.themeBound === 'true') return;
      radio.dataset.themeBound = 'true';

      radio.addEventListener('change', () => setTheme(radio.value));
    });
  }

  function setTheme(setting) {
    const themeValue = setting || 'system';
    localStorage.setItem(THEME_KEY, themeValue);
    applyTheme(themeValue);
    syncThemeInputs();
  }

  function applyThemeFromStorage() {
    applyTheme(getStoredTheme());
  }

  mediaQuery.addEventListener('change', () => {
    if (getStoredTheme() === 'system') {
      applyTheme('system');
    }
  });

  applyThemeFromStorage();

  window.ThemeManager = {
    setTheme,
    applyThemeFromStorage,
    syncThemeInputs,
    get theme() {
      return getStoredTheme();
    }
  };
})();

export const FOLDER_COLORS = [
  { id: "default", value: null },
  { id: "indigo", value: "#2D2A55" },
  { id: "teal", value: "#264653" },
  { id: "blue", value: "#2A7FFF" },
  { id: "green", value: "#4CAF50" },
  { id: "orange", value: "#F4A261" },
  { id: "red", value: "#E76F51" },
  { id: "purple", value: "#B5179E" },
  { id: "gray", value: "#6D6875" }
];
