/**
 * Notes Workspace
 * ---------------
 * Keeps the editor pane, autosave, and note context menus in sync with the list.
 */
(function () {
  const AUTOSAVE_DELAY = 700;
  let autosaveTimer = null;
  let activeNoteId = null;
  let isInspectorPinned = false;
  const MOBILE_PAGE_KEY = "notesMobilePage";
  const MOBILE_SCROLL_KEYS = {
    folders: "notesMobileScroll:folders",
    list: "notesMobileScroll:list",
    note: "notesMobileScroll:note"
  };
  const mobileQuery = window.matchMedia("(max-width: 768px)");

  document.addEventListener("DOMContentLoaded", () => {
    const noteId = document
      .getElementById("noteTitle")
      ?.dataset.noteId;
  
    if (noteId) {
      localStorage.setItem("lastOpenedNoteId", noteId);

      const layout = document.getElementById("notesLayout");
      const notesView = layout?.dataset.notesView || "all";
      const folderId = layout?.dataset.activeFolderId || null;

      let scope = "all";
      if (notesView === "root") {
        scope = "root";
      } else if (notesView === "folder" && folderId) {
        scope = `folder:${folderId}`;
      }
  
      fetch("/notes/last-opened", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note_id: noteId, scope })
      });

      const notesList = document.getElementById("notesList");
      const activeCard = notesList?.querySelector(
        `.note-card[data-note-id="${noteId}"]`
      );
      if (notesList && activeCard) {
        notesList.prepend(activeCard);
      }
    }
  });
  
  

  document.addEventListener("DOMContentLoaded", () => {
    const layout = document.getElementById("notesLayout");
    const inspector = document.getElementById("noteInspector");
  
    if (!layout || !inspector) return;
    if (window.matchMedia("(max-width: 768px)").matches) return;
  
    // Force CLOSED state on load
    inspector.classList.add("translate-x-full");
    layout.style.gridTemplateColumns =
      "12rem 14rem minmax(0,1fr) 0";

    const hasActiveNote = Boolean(
      document.getElementById("noteTitle")?.dataset.noteId
    );
    if (hasActiveNote) {
      toggleInspector(true);
      setInspectorPinned(true);
    }
  });
  

  function getActiveFolderId() {
    const id = window.activeFolderId;
    if (!id || id === "null" || id === "None") return null;
    return id;
  }

  function scheduleAutosave() {
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(saveNote, AUTOSAVE_DELAY);
  }

  function saveNote() {
    const titleEl = document.getElementById("noteTitle");
    const contentEl = document.getElementById("noteContent");
    if (!titleEl || !contentEl) return;

    const noteId = titleEl.dataset.noteId;
    if (!noteId) return;

    fetch(`/notes/${noteId}/autosave`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        title: titleEl.value,
        content: contentEl.innerHTML
      })
    });
  }

  function updateNoteListUI() {
    const titleEl = document.getElementById("noteTitle");
    const contentEl = document.getElementById("noteContent");
    if (!titleEl || !contentEl) return;
  
    const noteId = titleEl.dataset.noteId;
    if (!noteId) return;
  
    let card = document.querySelector(`.note-card[data-note-id="${noteId}"]`);
  
    const title = titleEl.value.trim();
    const contentText = contentEl.innerText || "";
    const firstLine = contentText.split("\n")[0].trim();
    
    if (!title && !firstLine) {
      if (card) {
        card.style.display = "none";
      }
      return;
    }

    if (!card) {
      const list = document.getElementById("notesList");
      if (!list) return;

      const params = new URLSearchParams(window.location.search);
      const folderId = params.get("folder_id");
      const noteUrl = folderId
        ? `/notes/${noteId}?folder_id=${folderId}`
        : `/notes/${noteId}`;

      card = document.createElement("div");
      card.dataset.noteId = noteId;
      card.dataset.notesTarget = "note";
      card.className =
        "note-card p-3 rounded-lg bg-white/5 hover:bg-white/10 cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)]";
      card.onclick = (event) => {
        if (typeof window.navigateNotesMobile === "function") {
          window.navigateNotesMobile(event, "note", noteUrl);
          return;
        }
        window.location.href = noteUrl;
      };
      card.oncontextmenu = (event) => {
        openNoteContextMenu(event, noteId);
      };

      const titleNode = document.createElement("p");
      titleNode.className = "note-title text-sm font-medium text-white truncate";

      const timeNode = document.createElement("p");
      timeNode.className = "note-time text-xs text-zinc-400 mt-1";

      card.appendChild(titleNode);
      card.appendChild(timeNode);
      list.prepend(card);
    }
    
    card.style.display = "";
    
    const titleNode = card.querySelector(".note-title");
    const timeNode = card.querySelector(".note-time");

    const displayTitle = title || firstLine;
    titleNode.textContent = displayTitle.slice(0, 80);
    timeNode.textContent = "Just now";
    
  }
  

  document.addEventListener("input", (event) => {
    const isTitle = event.target.id === "noteTitle";
    const isContent =
      event.target.id === "noteContent" ||
      event.target.closest?.("#noteContent");
    if (isTitle || isContent) {
      updateNoteListUI();
      scheduleAutosave();
    }
  });

  function getLayout() {
    return document.getElementById("notesLayout");
  }

  function getScrollAreas() {
    return {
      folders: document.getElementById("notesSidebar"),
      list: document.getElementById("notesListPane"),
      note: document.getElementById("notesEditorPane")
    };
  }

  function storeScrollPositions() {
    if (!mobileQuery.matches) return;
    const areas = getScrollAreas();
    Object.entries(areas).forEach(([key, el]) => {
      if (!el) return;
      sessionStorage.setItem(
        MOBILE_SCROLL_KEYS[key],
        String(el.scrollTop || 0)
      );
    });
  }

  function restoreScrollPosition(page) {
    const areas = getScrollAreas();
    const el = areas[page];
    if (!el) return;
    const stored = sessionStorage.getItem(MOBILE_SCROLL_KEYS[page]);
    if (stored === null) return;
    const value = parseInt(stored, 10);
    if (!Number.isFinite(value)) return;
    requestAnimationFrame(() => {
      el.scrollTop = value;
    });
  }

  function computeInitialMobilePage() {
    const layout = getLayout();
    const forced = layout?.dataset.forceMobilePage;
    if (forced === "folders" || forced === "list" || forced === "note") {
      return forced;
    }

    const pathHasNote = /^\/notes\/\d+/.test(window.location.pathname);
    if (pathHasNote) return "note";

    return "folders";
  }

  function setMobilePage(page, persist = true) {
    const layout = getLayout();
    if (!layout) return;
    layout.dataset.mobilePage = page;
    syncMobileEditorChrome(page);
    if (persist) {
      sessionStorage.setItem(MOBILE_PAGE_KEY, page);
    }
    restoreScrollPosition(page);
  }

  function syncMobileEditorChrome(page) {
    if (!document.body) return;
    const shouldShowEditor =
      mobileQuery.matches && page === "note";
    document.body.classList.toggle(
      "notes-mobile-editor-open",
      shouldShowEditor
    );
  }

  function navigateNotesMobile(event, targetPage, url) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    if (mobileQuery.matches) {
      storeScrollPositions();
      if (targetPage) {
        sessionStorage.setItem(MOBILE_PAGE_KEY, targetPage);
      }

      if (targetPage === "folders") {
        setMobilePage("folders", false);
        if (url) {
          window.history.replaceState(null, "", url);
        }
        return;
      }

      if (targetPage === "list") {
        const nextUrl = new URL(url, window.location.origin);
        nextUrl.searchParams.set("list", "1");
        window.location.href = nextUrl.toString();
        return;
      }
    }

    window.location.href = url;
  }

  window.navigateNotesMobile = navigateNotesMobile;

  document.addEventListener("DOMContentLoaded", () => {
    if (!mobileQuery.matches) return;
    setMobilePage(computeInitialMobilePage(), false);
  });

  mobileQuery.addEventListener("change", (event) => {
    const layout = getLayout();
    if (!layout) return;
    if (!event.matches) {
      document.body?.classList.remove("notes-mobile-editor-open");
      return;
    }
    syncMobileEditorChrome(layout.dataset.mobilePage || "folders");
  });

  window.addEventListener("beforeunload", storeScrollPositions);
  window.addEventListener("pagehide", storeScrollPositions);

  document.getElementById("noteContent")?.addEventListener("input", () => {
    const titleEl = document.getElementById("noteTitle");
    const contentEl = document.getElementById("noteContent");
    if (!titleEl || !contentEl || titleEl.value.trim()) return;

    const firstLine = (contentEl.innerText || "").split("\n")[0].trim();
    if (firstLine) {
      titleEl.value = firstLine.slice(0, 80);
      scheduleAutosave();
    }
  });

  function openNoteContextMenu(event, noteId) {
    event.preventDefault();
    event.stopPropagation();

    const menu = document.getElementById("noteContextMenu");
    if (!menu) return;

    activeNoteId = noteId;
    menu.style.top = `${event.clientY}px`;
    menu.style.left = `${event.clientX}px`;
    menu.classList.remove("hidden");
  }

  function hideNoteContextMenu() {
    document.getElementById("noteContextMenu")?.classList.add("hidden");
  }

  document.addEventListener("click", hideNoteContextMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideNoteContextMenu();
    }
  });

  function contextCreateNote() {
    const folderId = getActiveFolderId();
    if (!folderId) return;

    window.location.href = `/notes/create?folder_id=${folderId}`;
  }

  function contextDeleteNote() {
    if (!activeNoteId) return;
    const deletedId = activeNoteId;

    fetch(`/notes/delete/${deletedId}`, {
      method: "POST"
    }).then(() => {
      const card = document.querySelector(`[data-note-id="${deletedId}"]`);
      if (card) {
        card.classList.add("opacity-0", "translate-x-2");
        setTimeout(() => card.remove(), 200);
      }

      const folderId = getActiveFolderId();
      if (folderId && typeof window.decrementFolderCount === "function") {
        window.decrementFolderCount(folderId);
      }

      const titleEl = document.getElementById("noteTitle");
      if (titleEl && titleEl.dataset.noteId === String(deletedId)) {
        const params = new URLSearchParams(window.location.search);
        const folderParam = params.get("folder_id");
        window.location.href = folderParam
          ? `/notes?folder_id=${folderParam}`
          : `/notes`;
      }

      hideNoteContextMenu();
    });

    activeNoteId = null;
  }

  function createNewNote() {
    const folderId = getActiveFolderId();
    if (mobileQuery.matches) {
      sessionStorage.setItem(MOBILE_PAGE_KEY, "note");
    }
    if (folderId) {
      window.location.href = `/notes/create?folder_id=${folderId}`;
    } else {
      window.location.href = `/notes/create?view=root`;
    }
  }


  function toggleInspector(force = null) {
    const layout = document.getElementById("notesLayout");
    const inspector = document.getElementById("noteInspector");
    if (!layout || !inspector) return;
  
    const isOpen = !inspector.classList.contains("translate-x-full");
    const shouldOpen = force !== null ? force : !isOpen;

    if (force === false && isInspectorPinned) {
      return;
    }
  
    if (shouldOpen) {
      inspector.classList.remove("translate-x-full");
      layout.classList.add("inspector-open");
      layout.style.gridTemplateColumns =
        "12rem 14rem minmax(0,1fr) 16rem";
    } else {
      inspector.classList.add("translate-x-full");
      layout.classList.remove("inspector-open");
      layout.style.gridTemplateColumns =
        "12rem 14rem minmax(0,1fr) 0";
    }
  }

  function setInspectorPinned(nextPinned) {
    isInspectorPinned = nextPinned;

    const pinButton = document.getElementById("inspectorPinBtn");
    if (!pinButton) return;

    pinButton.setAttribute("aria-pressed", String(isInspectorPinned));
    pinButton.title = isInspectorPinned ? "Unpin inspector" : "Pin inspector";
    pinButton.classList.toggle("bg-white/10", isInspectorPinned);
    pinButton.classList.toggle("text-white", isInspectorPinned);
    pinButton.classList.toggle("text-zinc-400", !isInspectorPinned);

    const pinnedIcon = pinButton.querySelector('[data-pin="on"]');
    const unpinnedIcon = pinButton.querySelector('[data-pin="off"]');
    if (pinnedIcon && unpinnedIcon) {
      pinnedIcon.classList.toggle("hidden", !isInspectorPinned);
      unpinnedIcon.classList.toggle("hidden", isInspectorPinned);
    }
  }
  
  document
    .getElementById("inspectorEdgeHover")
    .addEventListener("mouseenter", () => toggleInspector(true));
  document
    .getElementById("noteInspector")
    .addEventListener("mouseleave", () => toggleInspector(false));  

    const edge = document.getElementById("inspectorEdgeHover");
    const inspector = document.getElementById("noteInspector");
    const pinButton = document.getElementById("inspectorPinBtn");
    const boldButton = document.getElementById("inspectorBoldBtn");
    const italicButton = document.getElementById("inspectorItalicBtn");
    const underlineButton = document.getElementById("inspectorUnderlineBtn");
    const strikethroughButton = document.getElementById(
      "inspectorStrikethroughBtn"
    );

    let isHoveringInspector = false;

    if (edge && inspector) {
      edge.addEventListener("mouseenter", () => {
        toggleInspector(true);
      });

      inspector.addEventListener("mouseenter", () => {
        isHoveringInspector = true;
        toggleInspector(true);
      });

      inspector.addEventListener("mouseleave", () => {
        isHoveringInspector = false;
        setTimeout(() => {
          if (!isHoveringInspector) {
            toggleInspector(false);
          }
        }, 150);
      });
    }

    if (pinButton) {
      pinButton.addEventListener("click", (event) => {
        event.stopPropagation();
        setInspectorPinned(!isInspectorPinned);
        if (isInspectorPinned) {
          toggleInspector(true);
        }
      });

      const hasActiveNote = Boolean(
        document.getElementById("noteTitle")?.dataset.noteId
      );
      setInspectorPinned(hasActiveNote);
      if (hasActiveNote) {
        toggleInspector(true);
      }
    }

    const styleButtons = [
      { button: boldButton, command: "bold" },
      { button: italicButton, command: "italic" },
      { button: underlineButton, command: "underline" },
      { button: strikethroughButton, command: "strikeThrough" }
    ];

    function isSelectionInsideEditor(selection, contentEl) {
      if (!selection || selection.rangeCount === 0) return false;
      const range = selection.getRangeAt(0);
      return contentEl.contains(range.commonAncestorContainer);
    }

    function syncStyleButtons() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;

      const selection = document.getSelection();
      if (!isSelectionInsideEditor(selection, contentEl)) {
        styleButtons.forEach(({ button }) => {
          button?.classList.remove("is-active");
        });
        return;
      }

      styleButtons.forEach(({ button, command }) => {
        if (!button) return;
        const isActive = document.queryCommandState(command);
        button.classList.toggle("is-active", isActive);
      });
    }

    let savedSelection = null;

    function saveEditorSelection() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;
      const selection = document.getSelection();
      if (!isSelectionInsideEditor(selection, contentEl)) return;
      const range = selection.getRangeAt(0);
      savedSelection = range.cloneRange();
    }

    function restoreEditorSelection() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl || !savedSelection) return;
      if (!contentEl.contains(savedSelection.commonAncestorContainer)) return;
      const selection = document.getSelection();
      if (!selection) return;
      selection.removeAllRanges();
      selection.addRange(savedSelection);
    }

    function ensureEditorSelection() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;
      let selection = document.getSelection();
      if (!selection || selection.rangeCount === 0) {
        const range = document.createRange();
        range.selectNodeContents(contentEl);
        range.collapse(false);
        selection = document.getSelection();
        if (!selection) return;
        selection.removeAllRanges();
        selection.addRange(range);
        savedSelection = range.cloneRange();
        return;
      }

      if (!isSelectionInsideEditor(selection, contentEl)) {
        restoreEditorSelection();
      }

      if (!isSelectionInsideEditor(selection, contentEl)) {
        const range = document.createRange();
        range.selectNodeContents(contentEl);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
        savedSelection = range.cloneRange();
      }
    }

    function toggleEditorCommand(command) {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;
      contentEl.focus();
      ensureEditorSelection();
      document.execCommand(command);
      saveEditorSelection();
      syncStyleButtons();
    }

    window.toggleBold = () => toggleEditorCommand("bold");
    window.toggleItalic = () => toggleEditorCommand("italic");
    window.toggleUnderline = () => toggleEditorCommand("underline");
    window.toggleStrikethrough = () => toggleEditorCommand("strikeThrough");

    function toggleStyleButton(button, handlerName) {
      if (!button) return;
      let skipClick = false;
      const trigger = (event) => {
        event.preventDefault();
        event.stopPropagation();
        saveEditorSelection();
        if (typeof window[handlerName] === "function") {
          window[handlerName]();
        }
        skipClick = true;
      };
      if ("PointerEvent" in window) {
        button.addEventListener("pointerdown", trigger);
      } else {
        button.addEventListener("mousedown", trigger);
      }
      button.addEventListener("click", (event) => {
        if (skipClick) {
          skipClick = false;
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        event.stopPropagation();
        if (typeof window[handlerName] === "function") {
          window[handlerName]();
        }
      });
    }

    toggleStyleButton(boldButton, "toggleBold");
    toggleStyleButton(italicButton, "toggleItalic");
    toggleStyleButton(underlineButton, "toggleUnderline");
    toggleStyleButton(strikethroughButton, "toggleStrikethrough");

    const contentEl = document.getElementById("noteContent");
    if (contentEl) {
      contentEl.addEventListener("focus", () => {
        saveEditorSelection();
        syncStyleButtons();
      });
      contentEl.addEventListener("keyup", () => {
        saveEditorSelection();
        syncStyleButtons();
      });
      contentEl.addEventListener("mouseup", () => {
        saveEditorSelection();
        syncStyleButtons();
      });
      contentEl.addEventListener("input", () => {
        saveEditorSelection();
        cleanupFontSizePlaceholders(contentEl);
      });
    }
    document.addEventListener("selectionchange", () => {
      saveEditorSelection();
      syncStyleButtons();
    });

    const FONT_SIZE_STORAGE_KEY = "notesEditorFontSize";
    const DEFAULT_FONT_SIZE = 16;
    let isFontSizeDragging = false;

    function updateFontSizeLabel(size) {
      const label = document.getElementById("editorFontSizeValue");
      if (!label) return;
      if (size === null) {
        label.textContent = "--";
        return;
      }
      label.textContent = `${size}px`;
    }

    function syncFontSizeControl(size) {
      const slider = document.getElementById("editorFontSize");
      if (slider) {
        slider.value = String(size);
      }
      updateFontSizeLabel(size);
    }

    function getActiveFontSize() {
      const slider = document.getElementById("editorFontSize");
      const fromSlider = parseInt(slider?.value, 10);
      if (Number.isFinite(fromSlider)) return fromSlider;
      const stored = parseInt(localStorage.getItem(FONT_SIZE_STORAGE_KEY), 10);
      if (Number.isFinite(stored)) return stored;
      return DEFAULT_FONT_SIZE;
    }

    function clampFontSize(size) {
      return Math.min(48, Math.max(8, size));
    }

    function getEditorRange() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return null;
      const selection = document.getSelection();
      if (!selection || selection.rangeCount === 0) return null;
      const range = selection.getRangeAt(0);
      if (!contentEl.contains(range.commonAncestorContainer)) return null;
      return range;
    }

    function wrapNodeWithFontSize(node, size) {
      if (!node || node.nodeType !== Node.TEXT_NODE) return null;
      const parent = node.parentElement;
      if (
        parent &&
        parent.tagName === "SPAN" &&
        parent.dataset.fontSize === String(size)
      ) {
        return null;
      }
      const span = document.createElement("span");
      span.style.fontSize = `${size}px`;
      span.dataset.fontSize = String(size);
      node.parentNode.replaceChild(span, node);
      span.appendChild(node);
      return span;
    }

    function mergeAdjacentFontSizeSpans(container) {
      if (!container) return;
      const walker = document.createTreeWalker(
        container,
        NodeFilter.SHOW_ELEMENT,
        {
          acceptNode(node) {
            return node.tagName === "SPAN" && node.dataset.fontSize
              ? NodeFilter.FILTER_ACCEPT
              : NodeFilter.FILTER_SKIP;
          }
        }
      );
      const spans = [];
      while (walker.nextNode()) {
        spans.push(walker.currentNode);
      }
      spans.forEach((span) => {
        const next = span.nextSibling;
        if (
          next &&
          next.nodeType === Node.ELEMENT_NODE &&
          next.tagName === "SPAN" &&
          next.dataset.fontSize === span.dataset.fontSize
        ) {
          while (next.firstChild) {
            span.appendChild(next.firstChild);
          }
          next.remove();
        }
      });
    }

    function applyFontSizeToSelection(range, size, contentEl) {
      const textNodes = [];
      const walker = document.createTreeWalker(
        contentEl,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode(node) {
            if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
            if (!range.intersectsNode(node)) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          }
        }
      );
      while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
      }

      let firstNode = null;
      let lastNode = null;

      textNodes.forEach((node) => {
        let start =
          node === range.startContainer ? range.startOffset : 0;
        let end = node === range.endContainer ? range.endOffset : node.length;
        if (start === end) return;

        let target = node;
        if (end < target.length) {
          target.splitText(end);
        }
        if (start > 0) {
          target = target.splitText(start);
        }

        const wrapped = wrapNodeWithFontSize(target, size);
        const anchor = wrapped ? wrapped.firstChild || wrapped : target;
        if (!firstNode) firstNode = anchor;
        lastNode = anchor;
      });

      mergeAdjacentFontSizeSpans(contentEl);

      if (firstNode && lastNode) {
        const selection = document.getSelection();
        if (!selection) return;
        const newRange = document.createRange();
        newRange.setStart(firstNode, 0);
        newRange.setEnd(
          lastNode,
          lastNode.nodeType === Node.TEXT_NODE ? lastNode.length : 0
        );
        selection.removeAllRanges();
        selection.addRange(newRange);
      }
    }

    function getClosestFontSizeSpan(node, contentEl) {
      const element =
        node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
      if (!element) return null;
      const span = element.closest?.("span[data-font-size]");
      if (!span || !contentEl.contains(span)) return null;
      return span;
    }

    function applyFontSizeToCaret(range, size, contentEl) {
      const activeSpan = getClosestFontSizeSpan(
        range.startContainer,
        contentEl
      );
      if (activeSpan && activeSpan.dataset.fontSize === String(size)) {
        return;
      }

      const span = document.createElement("span");
      span.style.fontSize = `${size}px`;
      span.dataset.fontSize = String(size);
      const placeholder = document.createTextNode("\u200B");
      span.appendChild(placeholder);

      range.insertNode(span);

      if (activeSpan) {
        const afterSpan = activeSpan.cloneNode(false);
        while (span.nextSibling) {
          afterSpan.appendChild(span.nextSibling);
        }
        activeSpan.after(span);
        if (afterSpan.childNodes.length > 0) {
          span.after(afterSpan);
        }
        if (activeSpan.childNodes.length === 0) {
          activeSpan.remove();
        }
      }

      const selection = document.getSelection();
      if (!selection) return;
      const caretRange = document.createRange();
      caretRange.setStart(placeholder, 1);
      caretRange.collapse(true);
      selection.removeAllRanges();
      selection.addRange(caretRange);
    }

    function cleanupFontSizePlaceholders(contentEl) {
      const walker = document.createTreeWalker(
        contentEl,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode(node) {
            return node.nodeValue && node.nodeValue.includes("\u200B")
              ? NodeFilter.FILTER_ACCEPT
              : NodeFilter.FILTER_REJECT;
          }
        }
      );

      const nodes = [];
      while (walker.nextNode()) {
        nodes.push(walker.currentNode);
      }

      nodes.forEach((node) => {
        node.nodeValue = node.nodeValue.replace(/\u200B/g, "");
        if (node.nodeValue.length === 0) {
          const parent = node.parentElement;
          node.remove();
          if (
            parent &&
            parent.tagName === "SPAN" &&
            parent.dataset.fontSize &&
            parent.childNodes.length === 0
          ) {
            parent.remove();
          }
        }
      });
    }

    function sanitizePastedContent(html) {
      const container = document.createElement("div");
      container.innerHTML = html;

      container.querySelectorAll("font").forEach((node) => {
        node.replaceWith(...node.childNodes);
      });

      container.querySelectorAll("[style]").forEach((el) => {
        el.removeAttribute("style");
      });

      container
        .querySelectorAll("[data-font-size]")
        .forEach((el) => el.removeAttribute("data-font-size"));

      container.querySelectorAll("span").forEach((span) => {
        if (!span.attributes.length) {
          span.replaceWith(...span.childNodes);
        }
      });

      container.querySelectorAll("*").forEach((el) => {
        el.style.fontSize = `${DEFAULT_FONT_SIZE}px`;
        el.style.fontFamily = "inherit";
      });

      return container;
    }

    function insertSanitizedPaste(range, html, contentEl) {
      const container = sanitizePastedContent(html);
      const fragment = document.createDocumentFragment();
      while (container.firstChild) {
        fragment.appendChild(container.firstChild);
      }
      const lastNode = fragment.lastChild;

      range.deleteContents();
      range.insertNode(fragment);

      const selection = document.getSelection();
      if (selection && lastNode) {
        const caretRange = document.createRange();
        caretRange.setStartAfter(lastNode);
        caretRange.collapse(true);
        selection.removeAllRanges();
        selection.addRange(caretRange);
      }

      normalizeEditorDOM();
    }

    function handleEditorPaste(event) {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;
      const range = getEditorRange();
      if (!range) return;

      const clipboard = event.clipboardData;
      if (!clipboard) return;

      event.preventDefault();

      const html = clipboard.getData("text/html");
      const text = clipboard.getData("text/plain");
      if (html) {
        insertSanitizedPaste(range, html, contentEl);
      } else {
        const escaped = (text || "").replace(/\n/g, "<br>");
        insertSanitizedPaste(range, escaped, contentEl);
      }
    }

    function getFontSizeFromNode(node, contentEl) {
      if (!node) return null;
      let element =
        node.nodeType === Node.ELEMENT_NODE
          ? node
          : node.parentElement;
      if (!element) return null;
      if (!contentEl.contains(element)) return null;

      const sizedSpan = element.closest?.("span[data-font-size]");
      if (sizedSpan && contentEl.contains(sizedSpan)) {
        const size = parseInt(sizedSpan.dataset.fontSize, 10);
        return Number.isFinite(size) ? size : null;
      }

      const computed = window.getComputedStyle(element);
      const value = parseInt(computed.fontSize, 10);
      return Number.isFinite(value) ? value : null;
    }

    function getFontSizesInRange(range, contentEl) {
      const sizes = new Map();
      const walker = document.createTreeWalker(
        contentEl,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode(node) {
            if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
            if (!range.intersectsNode(node)) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          }
        }
      );
      while (walker.nextNode()) {
        const size = getFontSizeFromNode(walker.currentNode, contentEl);
        if (!size) continue;
        sizes.set(size, (sizes.get(size) || 0) + 1);
      }
      return sizes;
    }

    function getFontSizeAtCursor() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return null;
      const selection = document.getSelection();
      if (!selection || selection.rangeCount === 0) return null;
      const range = selection.getRangeAt(0);
      if (!contentEl.contains(range.commonAncestorContainer)) return null;

      if (range.collapsed) {
        return (
          getFontSizeFromNode(selection.anchorNode, contentEl) ||
          DEFAULT_FONT_SIZE
        );
      }

      const sizes = getFontSizesInRange(range, contentEl);
      let dominant = DEFAULT_FONT_SIZE;
      let maxCount = 0;
      sizes.forEach((count, size) => {
        if (count > maxCount) {
          dominant = size;
          maxCount = count;
        }
      });
      return dominant;
    }

    function syncFontSizeFromSelection() {
      if (isFontSizeDragging) return;
      const size = getFontSizeAtCursor();
      if (size === null) return;
      syncFontSizeControl(size);
    }

    function setFontSize(size) {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;
      const nextSize = Math.min(
        48,
        Math.max(8, parseInt(size, 10) || DEFAULT_FONT_SIZE)
      );
      syncFontSizeControl(nextSize);
      localStorage.setItem(FONT_SIZE_STORAGE_KEY, String(nextSize));
      contentEl.focus();
      ensureEditorSelection();
      const range = getEditorRange();
      if (!range) return;

      if (range.collapsed) {
        applyFontSizeToCaret(range, nextSize, contentEl);
        mergeAdjacentFontSizeSpans(contentEl);
      } else {
        applyFontSizeToSelection(range, nextSize, contentEl);
        normalizeEditorDOM();
      }
    };

    function normalizeEditorDOM() {
      const contentEl = document.getElementById("noteContent");
      if (!contentEl) return;

      const walker = document.createTreeWalker(
        contentEl,
        NodeFilter.SHOW_ELEMENT,
        {
          acceptNode(node) {
            return node.tagName === "SPAN" && node.dataset.fontSize
              ? NodeFilter.FILTER_ACCEPT
              : NodeFilter.FILTER_SKIP;
          }
        }
      );

      const spans = [];
      while (walker.nextNode()) {
        spans.push(walker.currentNode);
      }

      spans.forEach((span) => {
        const nestedSized = span.querySelector("span[data-font-size]");
        if (nestedSized) {
          const fragment = document.createDocumentFragment();
          Array.from(span.childNodes).forEach((child) => {
            if (
              child.nodeType === Node.ELEMENT_NODE &&
              child.tagName === "SPAN" &&
              child.dataset.fontSize
            ) {
              fragment.appendChild(child);
              return;
            }
            const wrapper = document.createElement("span");
            wrapper.style.fontSize = span.style.fontSize;
            wrapper.dataset.fontSize = span.dataset.fontSize;
            wrapper.appendChild(child);
            fragment.appendChild(wrapper);
          });
          span.replaceWith(fragment);
          return;
        }

        const childSpans = span.querySelectorAll("span[data-font-size]");
        childSpans.forEach((child) => {
          if (child.dataset.fontSize === span.dataset.fontSize) {
            child.replaceWith(...child.childNodes);
          }
        });
      });

      mergeAdjacentFontSizeSpans(contentEl);
      cleanupFontSizePlaceholders(contentEl);
    }

    window.setFontSize = setFontSize;
    window.setEditorFontSize = setFontSize;

    function initFontSizeUI() {
      const contentEl = document.getElementById("noteContent");
      const slider = document.getElementById("editorFontSize");
      const label = document.getElementById("editorFontSizeValue");
      if (!contentEl || !slider || !label) return;
      const stored = parseInt(
        localStorage.getItem(FONT_SIZE_STORAGE_KEY),
        10
      );
      const initialRaw = Number.isFinite(stored)
        ? stored
        : parseInt(slider.value, 10) || DEFAULT_FONT_SIZE;
      const initialSize = Math.min(
        48,
        Math.max(8, parseInt(initialRaw, 10) || DEFAULT_FONT_SIZE)
      );
      syncFontSizeControl(initialSize);
      localStorage.setItem(FONT_SIZE_STORAGE_KEY, String(initialSize));

      slider.addEventListener("input", (event) => {
        setFontSize(event.target.value);
      });
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initFontSizeUI);
    } else {
      initFontSizeUI();
    }

    // selectionchange sync removed for simple slider behavior
    
  

  window.openNoteContextMenu = openNoteContextMenu;
  window.contextCreateNote = contextCreateNote;
  window.contextDeleteNote = contextDeleteNote;
  window.createNewNote = createNewNote;
})();
