/**
 * Settings Overlay Loader
 * -----------------------
 * Coordinates everything for the async settings modal:
 * - Opens the overlay from the avatar dropdown
 * - Fetches HTML fragments (/account?modal=1)
 * - Initializes nested tabs + theme radios via ThemeManager
 * - Provides close/reset helpers for other modules to call.
 */
window.SettingsPanel = window.SettingsPanel || {
  open() {
    // TODO: fetch modal markup + mount into #settingsOverlay.
  },
  close() {
    // TODO: close overlay + clear injected markup.
  }
};
