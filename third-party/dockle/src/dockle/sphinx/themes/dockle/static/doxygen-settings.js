/* global Cookie, dockleDoxygenNavigationPages */

(() => {
  if (typeof Cookie === 'undefined') return;

  // cookie.js resolves to the same documentation root from every nested page.
  const documentationRoot = new URL('.', document.currentScript.src);
  Cookie.cookie_namespace = `dockle_doxygen_${encodeURIComponent(documentationRoot.pathname)}_`;

  const navigationPages = new Set(dockleDoxygenNavigationPages);
  const readSetting = Cookie.readSetting;
  Cookie.readSetting = function (setting, defaultValue) {
    const value = readSetting.call(this, setting, defaultValue);
    if (setting === 'navpath' && value && !navigationPages.has(value.split('#')[0])) {
      // Doxygen's homepage fallback would otherwise reuse this invalid URL.
      this.eraseSetting(setting);
      return defaultValue;
    }
    return value;
  };
})();
