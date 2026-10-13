(() => {
  "use strict";

  const renderIcons = (scope = document) => {
    const lucide = globalThis.lucide;
    if (!lucide?.createIcons || !lucide.icons) {
      return;
    }
    scope.querySelectorAll("[data-lucide]").forEach((host) => {
      host.dataset.lucide = host.dataset.lucide.trim();
    });
    lucide.createIcons({ icons: lucide.icons });
  };

  const renderIcon = (host) => {
    host.dataset.lucide = host.dataset.lucide.trim();
    renderIcons(host.ownerDocument);
  };

  const root = document.documentElement;
  const storageKey = "dockle-color-scheme";
  const colorPreference = window.matchMedia("(prefers-color-scheme: dark)");
  const themeModes = ["auto", "light", "dark"];

  const configureComponentReference = () => {
    const isReference = Boolean(document.querySelector("#component-reference"))
      || [...document.querySelectorAll("h1, h2")]
        .some((heading) => heading.textContent.trim() === "Component reference");
    if (!isReference) {
      return;
    }
    root.classList.add("dockle-component-reference");
  };

  const loadStoredScheme = () => {
    try {
      return localStorage.getItem(storageKey);
    } catch {
      // Storage can be unavailable for local files or hardened browser policies.
      return null;
    }
  };

  configureComponentReference();
  const storedScheme = loadStoredScheme();

  if (storedScheme === "light" || storedScheme === "dark") {
    root.dataset.colorScheme = storedScheme;
  }

  const selectedScheme = () => {
    if (root.dataset.colorScheme === "light" || root.dataset.colorScheme === "dark") {
      return root.dataset.colorScheme;
    }
    return "auto";
  };

  const resolvedScheme = () => {
    if (root.dataset.colorScheme) {
      return root.dataset.colorScheme;
    }
    return colorPreference.matches ? "dark" : "light";
  };

  const updateThemeButtons = () => {
    const selected = selectedScheme();
    const selectedIndex = themeModes.indexOf(selected);
    const next = themeModes[(selectedIndex + 1) % themeModes.length];
    const icons = { auto: "sun-moon", light: "sun", dark: "moon" };
    document.querySelectorAll("[data-dockle-theme-toggle]").forEach((button) => {
      const icon = button.querySelector("[data-lucide]");
      const resolved = selected === "auto" ? ` (${resolvedScheme()})` : "";
      button.setAttribute(
        "aria-label",
        `Color scheme: ${selected}${resolved}. Switch to ${next}`,
      );
      button.title = button.getAttribute("aria-label");
      if (icon) {
        icon.dataset.lucide = icons[selected];
        renderIcon(icon);
      }
    });
  };

  document.querySelectorAll("[data-dockle-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const currentIndex = themeModes.indexOf(selectedScheme());
      const next = themeModes[(currentIndex + 1) % themeModes.length];
      if (next === "auto") {
        delete root.dataset.colorScheme;
      } else {
        root.dataset.colorScheme = next;
      }
      try {
        if (next === "auto") {
          localStorage.removeItem(storageKey);
        } else {
          localStorage.setItem(storageKey, next);
        }
      } catch {
        // The in-page selection still works for the current page.
      }
      updateThemeButtons();
    });
  });
  colorPreference.addEventListener("change", updateThemeButtons);

  document.querySelectorAll("[data-dockle-menu-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const open = root.toggleAttribute("data-sidebar-open");
      button.setAttribute("aria-expanded", String(open));
    });
  });

  const searchRoot = document.querySelector("[data-dockle-universal-search]");
  const logoUrl = searchRoot?.dataset.dockleLogoUrl;
  const targetTitle = searchRoot?.dataset.dockleTargetTitle;
  root.toggleAttribute("data-dockle-has-logo", Boolean(logoUrl));
  const sidebarScroller = document.querySelector([
    ".dockle-sidebar .dockle-tree",
    'html[data-dockle-framework="doxygen"] #nav-tree',
    'html[data-dockle-framework="jsdoc"] body > nav',
    'html[data-dockle-framework="rustdoc"] .sidebar',
  ].join(","));
  if (sidebarScroller && logoUrl) {
    let compact = false;
    const updateSidebarHeader = () => {
      if (sidebarScroller.scrollTop <= 0) {
        compact = false;
      } else if (sidebarScroller.scrollTop >= 72) {
        compact = true;
      }
      root.toggleAttribute("data-dockle-sidebar-compact", compact);
    };
    sidebarScroller.addEventListener("scroll", updateSidebarHeader, {
      passive: true,
    });
    updateSidebarHeader();
  }
  if (targetTitle && root.dataset.dockleFramework === "jsdoc") {
    const home = document.querySelector("body > nav h2 a");
    if (home) {
      home.textContent = targetTitle;
    }
  }
  if (targetTitle && root.dataset.dockleFramework === "rustdoc") {
    const crate = document.querySelector(".sidebar .sidebar-crate h2 > a");
    if (crate) {
      crate.textContent = targetTitle;
    }
  }

  const normalizedPagePath = (url) => {
    const path = new URL(url, document.baseURI).pathname;
    return path.replace(/index\.html$/, "").replace(/\/$/, "");
  };
  const markCurrentNavigation = () => {
    const currentPath = normalizedPagePath(location.href);
    const selectors = {
      doxygen: "#nav-tree .label > a[href]",
      jsdoc: "body > nav a[href]",
      mkdocs: ".dockle-tree a[href]",
      rustdoc: ".sidebar a[href]",
      sphinx: ".dockle-tree a[href]",
    };
    const selector = selectors[root.dataset.dockleFramework];
    if (!selector) {
      return;
    }
    const matches = [...document.querySelectorAll(selector)].filter((link) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#")) {
        return false;
      }
      const target = new URL(link.href, document.baseURI);
      return !target.hash && normalizedPagePath(target) === currentPath;
    });
    const currentLinks = root.dataset.dockleFramework === "rustdoc"
      ? matches.slice(0, 1)
      : matches;
    document.querySelectorAll(`${selector}.dockle-current`).forEach((link) => {
      link.classList.remove("dockle-current");
      link.removeAttribute("aria-current");
    });
    document.querySelectorAll("#nav-tree .dockle-current-item").forEach(
      (item) => item.classList.remove("dockle-current-item"),
    );
    if (root.dataset.dockleFramework === "rustdoc") {
      matches.slice(1).forEach((link) => {
        link.closest("li")?.classList.remove("current");
      });
    }
    currentLinks.forEach((link) => {
      link.classList.add("dockle-current");
      link.setAttribute("aria-current", "page");
      link.closest("#nav-tree .item")?.classList.add("dockle-current-item");
    });
  };
  markCurrentNavigation();
  window.addEventListener("load", markCurrentNavigation);

  if (logoUrl) {
    const brandSelectors = [
      ".dockle-brand a",
      ".dockle-mobile-header a",
      ".dockle-compat-brand",
      "#projectname",
    ];
    document.querySelectorAll(brandSelectors.join(",")).forEach((brand) => {
      if (brand.querySelector(".dockle-logo")) {
        return;
      }
      const logo = document.createElement("img");
      logo.className = "dockle-logo";
      logo.src = logoUrl;
      logo.alt = "";
      brand.prepend(logo);
    });
  }

  const alertConfig = {
    attention: ["Attention", "circle-alert"],
    caution: ["Caution", "circle-alert"],
    danger: ["Danger", "octagon-alert"],
    error: ["Error", "circle-x"],
    hint: ["Hint", "lightbulb"],
    important: ["Important", "flame"],
    note: ["Note", "info"],
    seealso: ["See also", "eye"],
    tip: ["Tip", "lightbulb"],
    todo: ["Todo", "list-todo"],
    warning: ["Warning", "triangle-alert"],
  };

  document.querySelectorAll("blockquote").forEach((quote) => {
    const first = quote.firstElementChild;
    if (!first) {
      return;
    }
    const match = /^\[!(\w+)\]/i.exec(first.textContent.trim());
    const type = match?.[1].toLocaleLowerCase();
    if (!type || !alertConfig[type]) {
      return;
    }
    const marker = first.matches("p") ? first : first.querySelector(":scope > p:first-child");
    if (!marker) {
      return;
    }
    marker.innerHTML = marker.innerHTML.replace(/^\s*\[!\w+\]\s*/i, "");
    if (!marker.textContent.trim()) {
      marker.remove();
    }
    quote.classList.add("dockle-alert", `dockle-alert-${type}`);
    const title = document.createElement("p");
    title.className = "dockle-alert-title";
    title.textContent = alertConfig[type][0];
    quote.prepend(title);
  });

  const doxygenTypes = {
    attention: "caution",
    bug: "danger",
    deprecated: "warning",
    important: "important",
    note: "note",
    pre: "hint",
    remark: "tip",
    seealso: "seealso",
    todo: "todo",
    warning: "warning",
  };
  const alertSelector = [
    ".dockle-alert",
    ".admonition",
    ...Object.keys(doxygenTypes).map((type) => `dl.${type}`),
  ].join(",");
  document.querySelectorAll(alertSelector).forEach((alert) => {
    const wasDockleAlert = alert.classList.contains("dockle-alert");
    let type;
    if (!wasDockleAlert && root.dataset.dockleFramework === "doxygen") {
      const doxygenType = [...alert.classList].find((name) => doxygenTypes[name]);
      type = doxygenTypes[doxygenType];
    }
    if (!type) {
      type = [...alert.classList].find((name) => alertConfig[name]);
    }
    if (!type) {
      type = [...alert.classList]
        .map((name) => /^dockle-alert-(\w+)$/.exec(name)?.[1])
        .find((name) => alertConfig[name]);
    }
    if (!type) {
      type = "note";
    }
    alert.classList.add("dockle-alert", `dockle-alert-${type}`);
    const title = alert.querySelector(":scope > .admonition-title, :scope > dt, :scope > .dockle-alert-title");
    if (!title) {
      return;
    }
    title.classList.add("dockle-alert-title");
    if (!wasDockleAlert && root.dataset.dockleFramework === "doxygen") {
      title.textContent = alertConfig[type][0];
    }
    if (!title.querySelector("[data-lucide]")) {
      const icon = document.createElement("i");
      icon.dataset.lucide = alertConfig[type][1];
      icon.setAttribute("aria-hidden", "true");
      title.prepend(document.createTextNode(" "));
      title.prepend(icon);
    }
  });

  const tabStorageKey = (group) => `dockle-tab-group:${group}`;
  const storedTab = (group) => {
    try {
      return sessionStorage.getItem(tabStorageKey(group));
    } catch {
      return null;
    }
  };
  const storeTab = (group, label) => {
    try {
      sessionStorage.setItem(tabStorageKey(group), label);
    } catch {
      // Tab linking still works within the current page without storage.
    }
  };

  const normalizeAliasTable = (panel) => {
    const fragments = [];
    const source = [...panel.childNodes].map((node) => {
      if (node.nodeType === Node.COMMENT_NODE) {
        return "";
      }
      if (node instanceof Element && node.matches(".fragment")) {
        const marker = `\uE000${fragments.length}\uE001`;
        fragments.push(node);
        return marker;
      }
      return node.textContent || "";
    }).join(" ");
    const cells = source.split("|").map((cell) => cell.trim()).filter(Boolean);
    const separator = /^[-\u2013\u2014:]+$/;
    if (cells.length < 6
        || cells[0].toLowerCase() !== "field"
        || cells[1].toLowerCase() !== "value"
        || !separator.test(cells[2])
        || !separator.test(cells[3])) {
      return;
    }
    const table = document.createElement("table");
    table.className = "markdownTable dockle-alias-table";
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    cells.slice(0, 2).forEach((label) => {
      const heading = document.createElement("th");
      heading.textContent = label;
      headRow.append(heading);
    });
    head.append(headRow);
    table.append(head);
    const body = document.createElement("tbody");
    for (let index = 4; index + 1 < cells.length; index += 2) {
      const row = document.createElement("tr");
      cells.slice(index, index + 2).forEach((value) => {
        const cell = document.createElement("td");
        const marker = /\uE000(\d+)\uE001/.exec(value);
        if (marker) {
          cell.append(fragments[Number(marker[1])]);
        } else {
          cell.textContent = value;
        }
        row.append(cell);
      });
      body.append(row);
    }
    table.append(body);
    panel.replaceChildren(table);
  };

  const selectTab = (tabSet, button, options = {}) => {
    const { focus = false, synchronize = true } = options;
    const buttons = [...tabSet.querySelectorAll(":scope > .dockle-tab-list > [role=tab]")];
    const panels = [...tabSet.querySelectorAll(":scope > .dockle-tab-panel")];
    const selectedIndex = buttons.indexOf(button);
    if (selectedIndex < 0) {
      return;
    }
    buttons.forEach((candidate, index) => {
      const selected = index === selectedIndex;
      candidate.setAttribute("aria-selected", String(selected));
      candidate.tabIndex = selected ? 0 : -1;
      panels[index].hidden = !selected;
    });
    if (focus) {
      button.focus();
    }
    const group = tabSet.dataset.dockleTabGroup;
    if (!group || !synchronize) {
      return;
    }
    const label = button.dataset.dockleTabLabel;
    storeTab(group, label);
    document.querySelectorAll(".dockle-tabs[data-dockle-tab-group]")
      .forEach((candidateSet) => {
        if (candidateSet === tabSet
            || candidateSet.dataset.dockleTabGroup !== group) {
          return;
        }
        const matchingButton = [...candidateSet.querySelectorAll(
          ":scope > .dockle-tab-list > [role=tab]",
        )].find((candidate) => candidate.dataset.dockleTabLabel === label);
        if (matchingButton) {
          selectTab(candidateSet, matchingButton, { synchronize: false });
        }
      });
  };

  document.querySelectorAll(".dockle-tabs, .tabbed").forEach((tabSet, setIndex) => {
    tabSet.classList.add("dockle-tabs");
    const details = [...tabSet.querySelectorAll(":scope > details")];
    const aliasList = tabSet.querySelector(":scope > ul");
    const aliasItems = aliasList
      ? [...aliasList.querySelectorAll(":scope > li")]
      : [];
    const sources = details.length
      ? details.map((detail) => {
        const title = detail.querySelector(":scope > summary");
        return {
          nodes: [...detail.childNodes].filter((node) => node !== title),
          open: detail.open,
          title: title?.textContent.trim(),
        };
      })
      : aliasItems.map((item) => {
        const title = item.querySelector(
          ".dockle-tab-title, .tab-title",
        );
        const titleText = title?.textContent.trim();
        title?.remove();
        return {
          nodes: [...item.childNodes],
          open: false,
          title: titleText,
        };
      });
    if (!sources.length) {
      return;
    }
    const tabList = document.createElement("div");
    tabList.className = "dockle-tab-list";
    tabList.setAttribute("role", "tablist");
    tabList.setAttribute(
      "aria-label",
      tabSet.dataset.dockleTabGroup || "Content tabs",
    );
    const requestedLabel = tabSet.dataset.dockleTabGroup
      ? storedTab(tabSet.dataset.dockleTabGroup)
      : null;
    let selectedIndex = sources.findIndex((source) => source.open);
    const requestedIndex = requestedLabel
      ? sources.findIndex((source) => source.title === requestedLabel)
      : -1;
    selectedIndex = requestedIndex >= 0 ? requestedIndex : Math.max(selectedIndex, 0);
    const panels = [];
    const buttons = [];
    sources.forEach((source, tabIndex) => {
      const button = document.createElement("button");
      const panel = document.createElement("div");
      const selected = tabIndex === selectedIndex;
      button.type = "button";
      button.id = `dockle-tab-${setIndex}-${tabIndex}`;
      button.textContent = source.title || `Tab ${tabIndex + 1}`;
      button.dataset.dockleTabLabel = button.textContent;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(selected));
      button.setAttribute("aria-controls", `dockle-panel-${setIndex}-${tabIndex}`);
      button.tabIndex = selected ? 0 : -1;
      panel.id = `dockle-panel-${setIndex}-${tabIndex}`;
      panel.className = "dockle-tab-panel";
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", button.id);
      panel.hidden = !selected;
      source.nodes.forEach((node) => panel.append(node));
      normalizeAliasTable(panel);
      button.addEventListener("click", () => {
        selectTab(tabSet, button);
      });
      button.addEventListener("keydown", (event) => {
        const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
        if (!keys.includes(event.key)) {
          return;
        }
        event.preventDefault();
        const current = buttons.indexOf(button);
        const indexes = {
          ArrowLeft: (current - 1 + sources.length) % sources.length,
          ArrowRight: (current + 1) % sources.length,
          Home: 0,
          End: sources.length - 1,
        };
        selectTab(tabSet, buttons[indexes[event.key]], { focus: true });
      });
      panels.push(panel);
      buttons.push(button);
      tabList.append(button);
    });
    tabSet.replaceChildren(tabList, ...panels);
  });

  const copyText = async (text) => {
    if (!navigator.clipboard?.writeText) {
      throw new Error("The Clipboard API is unavailable");
    }
    await navigator.clipboard.writeText(text);
  };

  const isBreakOnlyMarkup = (text) => {
    const markup = text.trim().toLowerCase();
    let offset = 0;
    let found = false;
    while (offset < markup.length) {
      if (!markup.startsWith("<br", offset)) {
        return false;
      }
      offset += 3;
      while (/\s/.test(markup[offset] || "")) {
        offset += 1;
      }
      if (markup[offset] === "/") {
        offset += 1;
        while (/\s/.test(markup[offset] || "")) {
          offset += 1;
        }
      }
      if (markup[offset] !== ">") {
        return false;
      }
      offset += 1;
      found = true;
    }
    return found;
  };

  const codeText = (container) => {
    const lines = [...container.querySelectorAll(":scope > .line")];
    if (lines.length) {
      return lines.map((line) => {
        const text = line.textContent.trim();
        return isBreakOnlyMarkup(text) ? "" : line.textContent;
      }).join("\n");
    }
    const source = container.matches("pre")
      ? container
      : container.querySelector("pre code, pre, code");
    return source?.innerText.replace(/\n$/, "") || "";
  };

  const normalizeDoxygenBlankCodeLines = () => {
    if (root.dataset.dockleFramework !== "doxygen") {
      return;
    }
    document.querySelectorAll("div.fragment > .line").forEach((line) => {
      if (isBreakOnlyMarkup(line.textContent)) {
        line.textContent = "";
      }
    });
  };

  const languageAliases = new Map([
    ["c++", "cpp"],
    ["cxx", "cpp"],
    ["default", "plaintext"],
    ["js", "javascript"],
    ["md", "markdown"],
    ["none", "plaintext"],
    ["plain", "plaintext"],
    ["ps1", "powershell"],
    ["pwsh", "powershell"],
    ["py", "python"],
    ["rs", "rust"],
    ["shell", "bash"],
    ["shell-session", "console"],
    ["shellsession", "console"],
    ["terminal", "console"],
    ["text", "plaintext"],
    ["ts", "typescript"],
    ["txt", "plaintext"],
    ["yml", "yaml"],
  ]);

  const canonicalLanguage = (language) => {
    const normalized = language.trim().toLowerCase();
    return languageAliases.get(normalized) || normalized;
  };

  const addLanguageGalleries = () => {
    document.querySelectorAll(".dockle-language-gallery")
      .forEach((gallery, galleryIndex) => {
        if (gallery.dataset.dockleReady !== undefined) {
          return;
        }
        let end = gallery.nextElementSibling;
        while (
          end
          && !end.classList.contains("dockle-language-gallery-end")
        ) {
          end = end.nextElementSibling;
        }
        if (!end) {
          return;
        }
        gallery.dataset.dockleReady = "";

        const controls = document.createElement("div");
        controls.className = "dockle-language-gallery-controls";
        const label = document.createElement("label");
        label.className = "dockle-language-gallery-label";
        label.textContent = "Filter languages";
        const input = document.createElement("input");
        input.className = "dockle-language-gallery-filter";
        input.id = `dockle-language-gallery-filter-${galleryIndex}`;
        input.type = "search";
        input.placeholder = "Filter by language or alias";
        input.autocomplete = "off";
        label.htmlFor = input.id;
        const count = document.createElement("span");
        count.className = "dockle-language-gallery-count";
        count.setAttribute("aria-live", "polite");
        controls.append(label, input, count);

        const list = document.createElement("div");
        list.className = "dockle-language-gallery-list";
        const entries = [];
        let item;
        let current = gallery.nextElementSibling;
        while (current && current !== end) {
          const next = current.nextElementSibling;
          if (
            current.classList.contains("dockle-language-gallery-header")
          ) {
            item = document.createElement("article");
            item.className = "dockle-language-gallery-item";
            item.dataset.dockleSearch = current.textContent.toLowerCase();
            const identifier = current.querySelector("code")?.textContent;
            if (identifier) {
              item.dataset.dockleLanguage = canonicalLanguage(identifier);
            }
            entries.push(item);
            list.append(item);
          }
          if (item) {
            item.append(current);
          }
          current = next;
        }
        end.remove();

        const update = () => {
          const query = input.value.trim().toLowerCase();
          let visible = 0;
          entries.forEach((entry) => {
            entry.hidden = !entry.dataset.dockleSearch.includes(query);
            visible += entry.hidden ? 0 : 1;
          });
          count.textContent = `${visible} of ${entries.length} languages`;
        };
        input.addEventListener("input", update);
        gallery.replaceChildren(controls, list);
        update();
      });
  };

  const languageName = (element) => {
    const prefixes = ["language-", "lang-", "highlight-"];
    const ancestors = [];
    for (
      let candidate = element;
      candidate && candidate !== document.body;
      candidate = candidate.parentElement
    ) {
      ancestors.push(candidate);
      if (candidate.dataset.dockleLanguage) {
        return canonicalLanguage(candidate.dataset.dockleLanguage);
      }
    }
    for (const candidate of ancestors) {
      for (const name of candidate.classList) {
        const prefix = prefixes.find((value) => name.startsWith(value));
        if (prefix) {
          return canonicalLanguage(name.slice(prefix.length));
        }
      }
      if (candidate.matches("pre.rust, code.rust")) {
        return "rust";
      }
    }
    return "";
  };

  const highlightCode = (code, language, source) => {
    if (code.dataset.dockleHighlighted === language) {
      return;
    }
    delete code.dataset.highlighted;
    code.textContent = source;
    [...code.classList]
      .filter((name) => name === "hljs" || name.startsWith("language-"))
      .forEach((name) => code.classList.remove(name));
    code.classList.add(`language-${language}`);
    globalThis.hljs.highlightElement(code);
    code.dataset.dockleHighlighted = language;
  };

  const applySyntaxHighlighting = () => {
    const highlighter = globalThis.hljs;
    if (!highlighter?.highlightElement || !highlighter?.getLanguage) {
      return;
    }

    document.querySelectorAll("div.fragment")
      .forEach((fragment) => {
        if (fragment.querySelector(".lineno")) {
          return;
        }
        const language = languageName(fragment);
        if (!highlighter.getLanguage(language)) {
          return;
        }
        let code = fragment.querySelector(":scope > code");
        if (!code) {
          const source = codeText(fragment);
          code = document.createElement("code");
          fragment.replaceChildren(code);
          highlightCode(code, language, source);
          return;
        }
        highlightCode(code, language, code.textContent);
      });

    document.querySelectorAll("pre").forEach((pre) => {
      if (
        pre.closest("div.fragment")
        || pre.matches(".source.linenums")
        || pre.querySelector(".lineno")
      ) {
        return;
      }
      let code = pre.querySelector(":scope > code");
      const language = languageName(code || pre);
      if (!language || !highlighter.getLanguage(language)) {
        return;
      }
      if (!code) {
        const source = pre.textContent;
        code = document.createElement("code");
        pre.replaceChildren(code);
        highlightCode(code, language, source);
        return;
      }
      if (code.querySelector("a[id], a[href^='#']")) {
        return;
      }
      highlightCode(code, language, code.textContent);
    });
  };

  const addCodeCopyButtons = () => {
    const containers = [
      ...document.querySelectorAll(".highlight, div.fragment, .example-wrap"),
      ...[...document.querySelectorAll("pre")].filter(
        (pre) => !pre.closest(".highlight, div.fragment, .example-wrap"),
      ),
    ];
    containers.forEach((sourceContainer) => {
      let container = sourceContainer;
      if (sourceContainer.matches("pre")) {
        container = document.createElement("div");
        sourceContainer.before(container);
        container.append(sourceContainer);
      }
      if (container.classList.contains("dockle-code-block")) {
        return;
      }
      container.classList.add("dockle-code-block");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "dockle-copy-button";
      button.setAttribute("aria-label", "Copy code");
      button.title = "Copy code";
      button.innerHTML = '<i data-lucide="copy" aria-hidden="true"></i>';
      button.addEventListener("click", async () => {
        try {
          await copyText(codeText(container));
          const icon = button.querySelector("[data-lucide]");
          icon.dataset.lucide = "check";
          renderIcon(icon);
          button.setAttribute("aria-label", "Code copied");
          button.title = "Code copied";
          window.setTimeout(() => {
            const currentIcon = button.querySelector("[data-lucide]");
            currentIcon.dataset.lucide = "copy";
            renderIcon(currentIcon);
            button.setAttribute("aria-label", "Copy code");
            button.title = "Copy code";
          }, 1600);
        } catch {
          button.setAttribute("aria-label", "Unable to copy code");
          button.title = "Unable to copy code";
        }
      });
      container.append(button);
    });
  };

  const replaceRustdocIcons = () => {
    if (root.dataset.dockleFramework !== "rustdoc") {
      return;
    }
    const controls = [
      ["#copy-path", "copy"],
      [".settings-menu > a", "settings"],
      [".help-menu > a", "circle-help"],
      ["button#toggle-all-docs", "chevrons-down"],
    ];
    controls.forEach(([selector, iconName]) => {
      document.querySelectorAll(selector).forEach((control) => {
        if (control.querySelector(":scope > .dockle-rustdoc-icon")) {
          return;
        }
        const icon = document.createElement("i");
        icon.className = "dockle-rustdoc-icon";
        icon.dataset.lucide = iconName;
        icon.setAttribute("aria-hidden", "true");
        control.prepend(icon);
        if (control.id === "copy-path") {
          const updateCopyPathIcon = () => {
            icon.dataset.lucide = control.classList.contains("clicked")
              ? "check"
              : "copy";
            renderIcon(icon);
          };
          new MutationObserver(updateCopyPathIcon).observe(control, {
            attributeFilter: ["class"],
            attributes: true,
          });
        }
      });
    });
  };

  const addHeadingPermalinks = () => {
    const contentSelectors = {
      doxygen: "#doc-content .contents",
      jsdoc: "#main",
      mkdocs: ".dockle-article",
      rustdoc: "#main-content",
      sphinx: ".dockle-article",
    };
    const content = document.querySelector(
      contentSelectors[root.dataset.dockleFramework],
    );
    if (!content) {
      return;
    }
    const uniqueHeadingId = (title) => {
      const base = title
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || "section";
      let candidate = base;
      let suffix = 2;
      while (document.getElementById(candidate)) {
        candidate = `${base}-${suffix}`;
        suffix += 1;
      }
      return candidate;
    };
    content.querySelectorAll("h1, h2, h3, h4, h5, h6").forEach((heading) => {
      if (!heading.getClientRects().length
          || heading.querySelector(":scope > .dockle-heading-anchor")) {
        return;
      }
      const nativeLink = heading.querySelector(
        ":scope > .headerlink, :scope > .doc-anchor",
      );
      const nativeTarget = heading.querySelector(":scope > .anchor[id]");
      const nativeHref = nativeLink?.getAttribute("href") || "";
      let target = heading.id || nativeTarget?.id || "";
      if (!target && nativeHref.startsWith("#") && nativeHref.length > 1) {
        target = nativeHref.slice(1);
      }
      const title = heading.cloneNode(true);
      title.querySelectorAll(
        ".anchor, .doc-anchor, .headerlink, .dockle-heading-anchor, button",
      ).forEach((element) => element.remove());
      const headingTitle = title.textContent.trim();
      if (!headingTitle) {
        return;
      }
      if (!target) {
        target = uniqueHeadingId(headingTitle);
        heading.id = target;
      }
      heading.querySelectorAll(":scope > .headerlink, :scope > .doc-anchor")
        .forEach((anchor) => anchor.remove());
      const link = document.createElement("a");
      link.className = "dockle-heading-anchor";
      link.href = `#${target}`;
      link.title = "Link to this heading";
      link.setAttribute("aria-label", `Link to ${headingTitle}`);
      link.innerHTML = '<i data-lucide="pilcrow" aria-hidden="true"></i>';
      heading.append(link);
    });
  };

  const setupAnchorHighlights = () => {
    let activeTarget;
    const pageTocLinks = () => [...document.querySelectorAll(
      "#page-nav a[href], .dockle-on-this-page a[href]",
    )];
    const markActiveTocLink = (hash) => {
      pageTocLinks().forEach((link) => {
        link.classList.remove("dockle-toc-current");
        if (link.getAttribute("aria-current") === "location") {
          link.removeAttribute("aria-current");
        }
      });
      if (!hash || hash === "#") {
        return;
      }
      pageTocLinks().forEach((link) => {
        const destination = new URL(link.href, document.baseURI);
        if (destination.hash === hash
            && normalizedPagePath(destination) === normalizedPagePath(location.href)) {
          link.classList.add("dockle-toc-current");
          link.setAttribute("aria-current", "location");
        }
      });
    };
    const targetForHash = (hash) => {
      if (!hash || hash === "#") {
        return null;
      }
      let identifier;
      try {
        identifier = decodeURIComponent(hash.slice(1));
      } catch {
        identifier = hash.slice(1);
      }
      const target = document.getElementById(identifier);
      if (!target) {
        return null;
      }
      const headingSelector = "h1, h2, h3, h4, h5, h6";
      return target.matches(headingSelector)
        ? target
        : target.closest(headingSelector)
          || target.querySelector(`:scope > :is(${headingSelector})`)
          || target;
    };
    const highlightHashTarget = (hash = location.hash) => {
      const target = targetForHash(hash);
      activeTarget?.classList.remove("dockle-anchor-highlight");
      activeTarget = null;
      markActiveTocLink(hash);
      if (!target) {
        return;
      }
      document.querySelectorAll(".glow").forEach(
        (element) => element.classList.remove("glow"),
      );
      target.classList.remove("dockle-anchor-highlight");
      // Force layout so selecting the same target restarts the animation.
      target.getBoundingClientRect();
      target.classList.add("dockle-anchor-highlight");
      activeTarget = target;
    };
    window.addEventListener("hashchange", () => highlightHashTarget());
    if (root.dataset.dockleFramework === "doxygen") {
      window.addEventListener("load", () => highlightHashTarget());
    }
    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) {
        return;
      }
      const link = event.target.closest("a[href]");
      if (!link) {
        return;
      }
      const destination = new URL(link.href, document.baseURI);
      if (destination.hash
          && normalizedPagePath(destination) === normalizedPagePath(location.href)) {
        setTimeout(() => highlightHashTarget(destination.hash));
        if (event.detail > 0 && link.matches(".dockle-heading-anchor")) {
          setTimeout(() => link.blur(), 700);
        }
      }
    });
    highlightHashTarget();
  };

  const placeBuiltWithFooter = () => {
    const footer = document.querySelector("[data-dockle-built-with]");
    const destinations = {
      doxygen: "#doc-content .contents",
      jsdoc: "#main",
      mkdocs: ".dockle-article",
      rustdoc: "#main-content",
      sphinx: ".dockle-article",
    };
    const selector = destinations[root.dataset.dockleFramework];
    const destination = selector ? document.querySelector(selector) : null;
    if (footer && destination && !destination.contains(footer)) {
      destination.append(footer);
    }
  };

  const createCompatibilityPageNav = (framework) => {
    const pageNav = document.createElement("aside");
    if (framework === "doxygen") {
      pageNav.id = "page-nav";
      document.querySelector("#container")?.append(pageNav);
      return pageNav;
    }
    pageNav.className = "dockle-on-this-page dockle-compat-toc";
    pageNav.setAttribute("aria-label", "On this page");
    document.body.append(pageNav);
    return pageNav;
  };

  const compatibilityPageNav = (framework) => {
    const selector = framework === "doxygen"
      ? "#page-nav"
      : ".dockle-compat-toc";
    return document.querySelector(selector)
      || createCompatibilityPageNav(framework);
  };

  const compatibilityHeadings = (framework) => {
    const headingSelectors = {
      doxygen: "#doc-content .contents h1.doxsection, "
        + "#doc-content .contents h2.doxsection, "
        + "#doc-content .contents h2.groupheader, "
        + "#doc-content .contents h2.memtitle, "
        + "#doc-content .contents h3",
      jsdoc: "#main article h2, #main article h3",
      rustdoc: "#main-content .docblock h2, "
        + "#main-content .docblock h3, "
        + "#main-content .docblock h4, "
        + "#main-content > h2.section-header",
    };
    const headings = [...document.querySelectorAll(headingSelectors[framework])]
      .filter((heading) => getComputedStyle(heading).display !== "none");
    if (headings.length) {
      return headings;
    }
    const fallbackSelectors = {
      doxygen: "#doc-content div.header .title",
      jsdoc: "#main h1",
      rustdoc: "#main-content h1",
    };
    const heading = document.querySelector(fallbackSelectors[framework]);
    if (!heading) {
      return headings;
    }
    heading.id ||= "dockle-page-start";
    return [heading];
  };

  const pageTocContents = (pageNav, framework) => {
    let contents = framework === "doxygen"
      ? pageNav.querySelector("#page-nav-contents")
      : pageNav;
    if (contents) {
      return contents;
    }
    contents = document.createElement("div");
    contents.id = "page-nav-contents";
    pageNav.append(contents);
    return contents;
  };

  const addPageTocTitle = (contents) => {
    if (contents.querySelector(".dockle-toc-title")) {
      return;
    }
    const title = document.createElement("strong");
    title.className = "dockle-toc-title";
    title.textContent = "On this page";
    contents.prepend(title);
  };

  const populatePageToc = (contents, framework) => {
    const headings = compatibilityHeadings(framework);
    if (!headings.length) {
      return;
    }
    const normalizeHash = (hash) => {
      try {
        return decodeURIComponent(hash);
      } catch {
        return hash;
      }
    };
    const existingHashes = new Set(
      [...contents.querySelectorAll("a[href]")].map((link) => {
        try {
          return normalizeHash(new URL(link.href, document.baseURI).hash);
        } catch {
          return "";
        }
      }),
    );
    const list = document.createElement("ul");
    list.className = "page-outline";
    const levels = headings.map((heading) => Number(heading.tagName.slice(1)));
    const baseLevel = Math.min(...levels);
    headings.forEach((heading, index) => {
      const anchor = heading.querySelector(".anchor[id]");
      heading.id ||= anchor?.id || `dockle-section-${index + 1}`;
      if (existingHashes.has(normalizeHash(`#${heading.id}`))) {
        return;
      }
      const item = document.createElement("li");
      const depth = Math.min(Number(heading.tagName.slice(1)) - baseLevel, 2);
      item.classList.add(`dockle-toc-depth-${depth}`);
      const link = document.createElement("a");
      link.href = `#${heading.id}`;
      const title = heading.cloneNode(true);
      title.querySelectorAll(
        ".anchor, .doc-anchor, .headerlink, .dockle-heading-anchor",
      ).forEach((anchor) => anchor.remove());
      link.textContent = title.textContent.trim();
      item.append(link);
      list.append(item);
    });
    if (list.children.length) {
      contents.append(list);
    }
  };

  const addLanguageGalleryTocLinks = () => {
    const pageNav = document.querySelector("#page-nav, .dockle-on-this-page");
    if (!pageNav) {
      return;
    }
    const links = [...pageNav.querySelectorAll("a[href]")];
    const sectionLink = links.find(
      (link) => link.textContent.replace(/\s+/g, " ").trim()
        === "Language highlighting",
    );
    const sectionItem = sectionLink?.closest("li");
    if (!sectionItem) {
      return;
    }
    let languageList = sectionItem.querySelector(":scope > .dockle-language-toc");
    if (!languageList) {
      languageList = document.createElement("ul");
      languageList.className = "dockle-language-toc";
      sectionItem.append(languageList);
    }
    const hashFor = (link) => {
      try {
        return new URL(link.getAttribute("href"), document.baseURI).hash;
      } catch {
        return "";
      }
    };
    document.querySelectorAll(
      ".dockle-language-gallery-header[id]",
    ).forEach((heading) => {
      const hash = `#${heading.id}`;
      let link = [...pageNav.querySelectorAll("a[href]")]
        .find((candidate) => hashFor(candidate) === hash);
      let item = link?.closest("li");
      if (!item) {
        item = document.createElement("li");
        link = document.createElement("a");
        link.href = hash;
        item.append(link);
      }
      item.classList.add("dockle-language-toc-item");
      link.textContent = heading.querySelector(":scope > strong, :scope > b")
        ?.textContent
        || heading.dataset.dockleLanguage
        || heading.id.replace(/^language-/, "");
      languageList.append(item);
    });
    if (!languageList.children.length) {
      languageList.remove();
    }
  };

  const preserveDoxygenPageTocNavigation = (pageNav) => {
    if (pageNav.dataset.dockleNavigationFixed === "true") {
      return;
    }
    pageNav.dataset.dockleNavigationFixed = "true";
    pageNav.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) {
        return;
      }
      const link = event.target.closest('a[href^="#"]:not(.noscroll)');
      if (link && pageNav.contains(link)) {
        event.stopPropagation();
      }
    }, true);
  };

  const normalizeDoxygenSidebar = () => {
    if (root.dataset.dockleFramework !== "doxygen") {
      return;
    }
    const navTree = document.querySelector("#nav-tree");
    if (!navTree) {
      return;
    }
    const normalizeHierarchy = () => {
      const currentPath = normalizedPagePath(location.href);
      const pageHeading = document.querySelector(
        "#doc-content .contents h1.doxsection, #doc-content div.header .title",
      );
      const pageTitle = pageHeading?.textContent.replace(/\s+/g, " ").trim();
      if (pageTitle) {
        navTree.querySelectorAll(".label > a[href]").forEach((link) => {
          const destination = new URL(link.href, document.baseURI);
          if (!destination.hash
              && normalizedPagePath(destination) === currentPath) {
            const label = link.querySelector("span") || link;
            if (label.textContent !== pageTitle) {
              label.textContent = pageTitle;
            }
          }
        });
      }
      markCurrentNavigation();
    };
    normalizeHierarchy();
    if (navTree.dataset.dockleHierarchyNormalized === "true") {
      return;
    }
    navTree.dataset.dockleHierarchyNormalized = "true";
    new MutationObserver(normalizeHierarchy).observe(navTree, {
      childList: true,
      subtree: true,
    });
  };

  const ensureCompatibilityPageToc = () => {
    const framework = root.dataset.dockleFramework;
    if (!["doxygen", "jsdoc", "rustdoc"].includes(framework)) {
      return;
    }
    const pageNav = compatibilityPageNav(framework);
    const usesNativePageToc = framework === "doxygen"
      && pageNav.classList.contains("page-nav-panel");
    if (usesNativePageToc) {
      pageNav.querySelectorAll("a[href] > .anchor[id]").forEach(
        (anchor) => anchor.remove(),
      );
      preserveDoxygenPageTocNavigation(pageNav);
    }
    pageNav.querySelectorAll(".dockle-heading-anchor").forEach(
      (anchor) => anchor.remove(),
    );
    pageNav.classList.add("dockle-page-toc");
    const contents = pageTocContents(pageNav, framework);
    if (framework === "doxygen") {
      contents.replaceChildren();
    }
    addPageTocTitle(contents);
    populatePageToc(contents, framework);
    root.classList.add("dockle-has-page-toc");
    root.classList.toggle("dockle-native-page-toc", usesNativePageToc);
  };

  const addDoxygenNavigation = () => {
    if (root.dataset.dockleFramework !== "doxygen" || !Array.isArray(globalThis.NAVTREE)) {
      return;
    }
    const pages = [];
    const seen = new Map();
    const visit = (items) => {
      items.forEach(([title, target, children]) => {
        const hasFragment = typeof target === "string" && target.includes("#");
        const pageLocation = typeof target === "string" ? target.split("#")[0] : "";
        if (!hasFragment && pageLocation.endsWith(".html")) {
          if (seen.has(pageLocation)) {
            seen.get(pageLocation).title = title;
          } else {
            const page = { location: pageLocation, title };
            seen.set(pageLocation, page);
            pages.push(page);
          }
        }
        if (Array.isArray(children)) {
          visit(children);
        }
      });
    };
    visit(globalThis.NAVTREE);
    const current = location.pathname.split("/").pop() || "index.html";
    const index = pages.findIndex((page) => page.location === current);
    const contents = document.querySelector("#doc-content .contents");
    if (index < 0 || !contents || contents.querySelector(".dockle-generated-page-links")) {
      return;
    }
    const navigation = document.createElement("nav");
    navigation.className = "dockle-page-links dockle-generated-page-links";
    navigation.setAttribute("aria-label", "Page navigation");
    const addLink = (page, direction) => {
      if (!page) {
        return;
      }
      const link = document.createElement("a");
      link.className = direction === "Previous" ? "dockle-previous" : "dockle-next";
      link.href = page.location;
      link.innerHTML = direction === "Previous"
        ? `<i data-lucide="arrow-left" aria-hidden="true"></i><span><small>${direction}</small>${page.title}</span>`
        : `<span><small>${direction}</small>${page.title}</span><i data-lucide="arrow-right" aria-hidden="true"></i>`;
      navigation.append(link);
    };
    addLink(pages[index - 1], "Previous");
    addLink(pages[index + 1], "Next");
    if (navigation.children.length) {
      contents.append(navigation);
    }
  };

  const normalize = (value) => value.toLocaleLowerCase();
  const cleanSearchTitle = (value) => {
    const separator = Math.max(value.lastIndexOf(" — "), value.lastIndexOf(" – "));
    return separator < 0 ? value : value.slice(0, separator);
  };
  const searchExcerpt = (value, query) => {
    const content = value.replace(/\s+/g, " ").trim();
    if (!content) {
      return "";
    }
    const folded = normalize(content);
    const terms = normalize(query).split(/\s+/).filter(Boolean);
    let matchAt = folded.indexOf(normalize(query));
    if (matchAt < 0) {
      matchAt = Math.min(...terms.map((term) => {
        const position = folded.indexOf(term);
        return position < 0 ? Infinity : position;
      }));
    }
    const start = Number.isFinite(matchAt) && matchAt > 70
      ? content.indexOf(" ", matchAt - 70) + 1 : 0;
    const limit = Math.min(content.length, start + 220);
    const wordEnd = content.lastIndexOf(" ", limit);
    const end = limit < content.length && wordEnd > start ? wordEnd : limit;
    return `${start ? "… " : ""}${content.slice(start, end)}${end < content.length ? " …" : ""}`;
  };
  const decodeSearchHighlight = (value) => {
    const template = document.createElement("template");
    template.innerHTML = value;
    return template.content.textContent || "";
  };
  const appendSearchHighlight = (host, value, query) => {
    const terms = [...new Set(query.split(/\s+/).filter(Boolean))];
    if (!terms.length) {
      host.textContent = value;
      return;
    }
    const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`));
    const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
    for (const fragment of value.split(pattern)) {
      if (terms.some((term) => normalize(term) === normalize(fragment))) {
        const mark = document.createElement("mark");
        mark.textContent = fragment;
        host.append(mark);
      } else {
        host.append(document.createTextNode(fragment));
      }
    }
  };
  const score = (entry, terms) => {
    const title = normalize(entry.title);
    const text = normalize(entry.text);
    return terms.reduce((total, term) => {
      if (title === term) {
        return total + 20;
      }
      if (title.includes(term)) {
        return total + 8;
      }
      if (text.includes(term)) {
        return total + 1;
      }
      return -1000;
    }, 0);
  };

  document.querySelectorAll("[data-dockle-search]").forEach((input) => {
    const selector = `[data-dockle-search-results="${input.id}"]`;
    const results = document.querySelector(selector);
    if (!results) {
      return;
    }

    let documents;
    let hostedSearch;
    let liveRequestId = 0;
    let pageRequestId = 0;
    const pageResults = document.querySelector("[data-dockle-search-page]");
    const pageSummary = document.querySelector("[data-dockle-search-summary]");
    const rootPath = input.dataset.dockleRoot.replace(/\/?$/, "/");
    const loadDocuments = async () => {
      if (!documents) {
        const response = await fetch(input.dataset.dockleSearch);
        if (!response.ok) {
          throw new Error(`Search index returned ${response.status}`);
        }
        documents = (await response.json()).docs || [];
      }
      return documents;
    };

    const localSearch = async (query, limit, page) => {
      const terms = normalize(query).split(/\s+/).filter(Boolean);
      const matches = (await loadDocuments())
        .map((entry) => ({ entry, score: score(entry, terms) }))
        .filter((match) => match.score >= 0)
        .sort((left, right) => right.score - left.score);
      const start = (page - 1) * limit;
      return {
        count: matches.length,
        next: start + limit < matches.length,
        matches: matches.slice(start, start + limit).map(({ entry }) => ({
          title: cleanSearchTitle(entry.title),
          excerpt: searchExcerpt(entry.text, query),
          href: new URL(`${rootPath}${entry.location}`, document.baseURI).href,
        })),
      };
    };

    const search = async (query, limit, page = 1) => {
      if (hostedSearch) {
        try {
          const url = new URL("/_/api/v3/search/", location.origin);
          url.searchParams.set("q", `project:${hostedSearch.project}/${hostedSearch.version} ${query}`);
          url.searchParams.set("page_size", String(limit));
          url.searchParams.set("page", String(page));
          const response = await fetch(url);
          if (!response.ok) {
            throw new Error(`Read the Docs search returned ${response.status}`);
          }
          const data = await response.json();
          if (data.count) {
            return {
              count: data.count,
              next: data.next,
              matches: data.results.map((entry) => {
                const highlights = entry.blocks?.flatMap((block) => block.highlights?.content || []) || [];
                const context = highlights.filter(Boolean).slice(0, 2).join(" … ")
                  || entry.blocks?.find((block) => block.content)?.content || "";
                return {
                  title: cleanSearchTitle(entry.title),
                  excerpt: searchExcerpt(decodeSearchHighlight(context), query),
                  href: new URL(entry.path, entry.domain).href,
                };
              }),
            };
          }
        } catch {
          // Read the Docs preview builds may not have a server index yet.
        }
      }
      return localSearch(query, limit, page);
    };

    const setHostedSearch = (eventData) => {
      const data = eventData?.detail?.data?.() || eventData?.data?.();
      const project = data?.projects?.current?.slug;
      const version = data?.versions?.current?.slug;
      if (project && version && !/^\d+$/.test(version)) {
        hostedSearch = { project, version };
        if (pageResults) {
          void renderPage();
        } else if (input.value.trim().length >= 2) {
          input.dispatchEvent(new Event("input"));
        }
      }
    };

    const closeResults = () => {
      results.hidden = true;
      results.replaceChildren();
    };

    input.addEventListener("input", async () => {
      const query = input.value.trim();
      const currentRequest = ++liveRequestId;
      results.replaceChildren();
      results.hidden = query.length < 2;
      if (results.hidden) {
        return;
      }

      try {
        const { matches } = await search(query, 8);
        if (currentRequest !== liveRequestId) {
          return;
        }
        for (const match of matches) {
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.href = match.href;
          const title = document.createElement("strong");
          title.textContent = match.title;
          link.append(title);
          if (match.excerpt) {
            const excerpt = document.createElement("small");
            excerpt.className = "dockle-live-search-snippet";
            appendSearchHighlight(excerpt, match.excerpt, query);
            link.append(excerpt);
          }
          item.append(link);
          results.append(item);
        }
        if (!matches.length) {
          const item = document.createElement("li");
          item.textContent = "No matching pages";
          results.append(item);
        }
      } catch {
        if (currentRequest !== liveRequestId) {
          return;
        }
        const item = document.createElement("li");
        item.textContent = "Search is unavailable";
        results.append(item);
      }
    });

    const renderPage = async () => {
      const query = new URLSearchParams(location.search).get("q")?.trim() || "";
      input.value = query;
      if (!pageResults || !pageSummary) {
        return;
      }
      pageResults.replaceChildren();
      pageResults.parentElement?.querySelector(".dockle-search-more")?.remove();
      pageSummary.textContent = query ? `Searching for “${query}”…` : "Enter a search term above.";
      if (!query) {
        return;
      }
      const currentRequest = ++pageRequestId;
      const addPage = async (page) => {
        try {
          const { matches, count, next } = await search(query, 25, page);
          if (currentRequest !== pageRequestId) {
            return;
          }
          pageSummary.textContent = count === 1 ? "1 matching page" : `${count} matching pages`;
          for (const match of matches) {
            const item = document.createElement("li");
            const link = document.createElement("a");
            link.href = match.href;
            link.textContent = match.title;
            const excerpt = document.createElement("p");
            appendSearchHighlight(excerpt, match.excerpt, query);
            item.append(link, excerpt);
            pageResults.append(item);
          }
          pageResults.parentElement?.querySelector(".dockle-search-more")?.remove();
          if (next) {
            const more = document.createElement("button");
            more.className = "dockle-search-more";
            more.type = "button";
            more.textContent = "Load more results";
            more.addEventListener("click", () => {
              more.disabled = true;
              void addPage(page + 1);
            });
            pageResults.after(more);
          }
        } catch {
          pageSummary.textContent = "Search is unavailable";
        }
      };
      await addPage(1);
    };
    if (pageResults) {
      void renderPage();
    }
    document.addEventListener("readthedocs-addons-data-ready", setHostedSearch);
    if (window.ReadTheDocsEventData) {
      setHostedSearch(window.ReadTheDocsEventData);
    }

    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeResults();
        input.blur();
      }
    });
    document.addEventListener("click", (event) => {
      if (!searchRoot?.contains(event.target)) {
        closeResults();
      }
    });
  });

  normalizeDoxygenSidebar();
  window.addEventListener("load", normalizeDoxygenSidebar);
  addDoxygenNavigation();
  addLanguageGalleries();
  normalizeDoxygenBlankCodeLines();
  applySyntaxHighlighting();
  addCodeCopyButtons();
  replaceRustdocIcons();
  placeBuiltWithFooter();
  const finalizePageToc = () => {
    ensureCompatibilityPageToc();
    addLanguageGalleryTocLinks();
  };
  if (root.dataset.dockleFramework === "doxygen") {
    window.addEventListener("load", finalizePageToc);
  } else {
    finalizePageToc();
  }
  addHeadingPermalinks();
  setupAnchorHighlights();
  renderIcons();
  window.addEventListener("load", () => renderIcons());
  updateThemeButtons();
})();
