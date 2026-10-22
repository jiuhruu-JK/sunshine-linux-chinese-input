class DoxyconfigIcons {
  static sectionIcons = {
    attention: 'circle-alert',
    deprecated: 'pencil',
    important: 'flame',
    note: 'sticky-note',
    pre: 'info',
    remark: 'info',
    warning: 'triangle-alert',
  };

  static init() {
    const replaceIcons = function() {
      for (const [sectionClass, iconName] of Object.entries(DoxyconfigIcons.sectionIcons)) {
        const headings = document.querySelectorAll(`dl.section.${sectionClass} > dt`);
        for (const heading of headings) {
          if (heading.querySelector('[data-lucide]')) {
            continue;
          }

          const icon = document.createElement('i');
          icon.setAttribute('aria-hidden', 'true');
          icon.dataset.lucide = iconName;
          heading.prepend(document.createTextNode(' '));
          heading.prepend(icon);
        }
      }

      for (const icon of document.querySelectorAll('[data-lucide]')) {
        const iconName = icon.dataset.lucide;
        icon.dataset.lucide = iconName.trim();
      }

      globalThis.lucide.createIcons({ icons: globalThis.lucide.icons });
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', replaceIcons);
    } else {
      replaceIcons();
    }
  }
}
