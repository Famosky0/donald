import { renderColorPicker } from "../ui/color-picker.js";

(function () {
  const layout = document.getElementById("notesLayout");
  const folderOptionsModal = document.getElementById("folderOptionsModal");
  const createFolderModal = document.getElementById("createFolderModal");
  const folderColorModal = document.getElementById("folderColorModal");
  const folderColorPickerModal = document.getElementById("folderColorPickerModal");
  const folderColorWheel = document.getElementById("folderColorWheel");



  function normalizeFolderId(value) {
    if (!value || value === "null" || value === "None") return null;
    return value;
  }

  let activeFolderId = normalizeFolderId(layout?.dataset.activeFolderId);
  window.activeFolderId = activeFolderId;

  function setActiveFolder(folderId) {
    activeFolderId = normalizeFolderId(folderId);
    window.activeFolderId = activeFolderId;
  }

  function restoreSidebarState() {
    if (
      layout &&
      localStorage.getItem("notesSidebarCollapsed") === "true"
    ) {
      layout.classList.add("notes-collapsed");
    }
  }

  if (document.readyState === "loading") {
    window.addEventListener("load", restoreSidebarState);
  } else {
    restoreSidebarState();
  }

  function toggleNotesSidebar() {
    if (!layout) return;
    layout.classList.toggle("notes-collapsed");

    localStorage.setItem(
      "notesSidebarCollapsed",
      layout.classList.contains("notes-collapsed")
    );
  }

  function toggleFolders() {
    document.getElementById("foldersList")?.classList.toggle("hidden");
  }

  function toggleFoldersChevron() {
    const chevron = document.getElementById("foldersChevron");
    const folders = document.getElementById("foldersList");
    if (!chevron || !folders) return;

    chevron.classList.toggle("rotate-180");

    const isOpen = folders.classList.contains("max-h-96");
    if (isOpen) {
      folders.classList.remove("max-h-96", "opacity-100", "translate-y-0");
      folders.classList.add("max-h-0", "opacity-0", "-translate-y-1");
    } else {
      folders.classList.remove("max-h-0", "opacity-0", "-translate-y-1");
      folders.classList.add("max-h-96", "opacity-100", "translate-y-0");
    }
  }

  function openCreateFolderModal(parentId = null) {
    if (!createFolderModal) return;

    const parentInput = document.getElementById("createFolderParentId");
    if (parentInput) {
      parentInput.value = parentId ?? "";
    }

    createFolderModal.classList.remove("hidden");
    createFolderModal.classList.add("flex");

    const nameInput = createFolderModal.querySelector('input[name="name"]');
    if (nameInput) {
      setTimeout(() => nameInput.focus(), 0);
    }
  }

  function closeCreateFolderModal() {
    if (!createFolderModal) return;
    createFolderModal.classList.add("hidden");
    createFolderModal.classList.remove("flex");

    const parentInput = document.getElementById("createFolderParentId");
    if (parentInput) parentInput.value = "";
  }

  function hideFolderOptionsModal() {
    if (!folderOptionsModal) return;
    folderOptionsModal.classList.add("hidden");
    folderOptionsModal.classList.remove("block");
  }

  function showFolderOptionsMenu(event, folderId) {
    event.stopPropagation();

    if (!folderOptionsModal) return;
    const menu = folderOptionsModal.querySelector(".modal-content");
    if (!menu) return;

    setActiveFolder(folderId);

    if (typeof window.closeAllModals === "function") {
      window.closeAllModals();
    }

    folderOptionsModal.classList.remove("hidden");
    folderOptionsModal.classList.add("block");

    menu.style.visibility = "hidden";
    menu.style.top = "0px";
    menu.style.left = "0px";

    const rect = menu.getBoundingClientRect();
    const padding = 12;
    let left = event.clientX;
    let top = event.clientY;

    if (left + rect.width + padding > window.innerWidth) {
      left = window.innerWidth - rect.width - padding;
    }
    if (top + rect.height + padding > window.innerHeight) {
      top = window.innerHeight - rect.height - padding;
    }

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    menu.style.visibility = "";
  }

  function startInlineRename() {
    hideFolderOptionsModal();

    if (!activeFolderId) return;
    const folderEl = document.querySelector(
      `[data-folder-id="${activeFolderId}"]`
    );
    if (!folderEl) return;

    const oldName = folderEl.textContent.trim();
    const input = document.createElement("input");
    input.type = "text";
    input.value = oldName;
    input.className = `
      w-full bg-transparent border border-white/20
      rounded px-1 text-sm text-white outline-none
    `;

    folderEl.replaceWith(input);
    input.focus();
    input.select();

    function cancelRename() {
      input.replaceWith(folderEl);
    }

    function submitRename() {
      if (!input.value.trim()) return cancelRename();

      fetch(`/notes/folders/rename/${activeFolderId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `name=${encodeURIComponent(input.value.trim())}`
      }).then(() => {
        folderEl.textContent = input.value.trim();
        input.replaceWith(folderEl);
      });
    }

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitRename();
      if (e.key === "Escape") cancelRename();
    });

    input.addEventListener("blur", cancelRename);
  }

  function deleteFolder() {
    if (!activeFolderId) return;
    hideFolderOptionsModal();

    const folderEl = document.querySelector(
      `[data-folder-id="${activeFolderId}"]`
    )?.closest("li");

    if (folderEl) {
      folderEl.classList.add("opacity-0");
      setTimeout(() => folderEl.remove(), 150);
    }

    fetch(`/notes/folders/delete/${activeFolderId}`, {
      method: "POST"
    });

    setActiveFolder(null);
  }

  function createSubfolder() {
    hideFolderOptionsModal();
    const parentInput = document.getElementById("createFolderParentId");
    if (parentInput) {
      parentInput.value = activeFolderId || "";
    }
    openCreateFolderModal();
  }

  function openFolderOptions(event, folderId) {
    showFolderOptionsMenu(event, folderId);
  }

  function openFolderContextMenu(event, folderId) {
    event.preventDefault();
    showFolderOptionsMenu(event, folderId);
  }

  function decrementFolderCount(folderId) {
    if (!folderId) return;
    const el = document.querySelector(`[data-folder-count="${folderId}"]`);
    if (!el) return;

    const current = parseInt(el.textContent, 10) || 0;
    el.textContent = Math.max(0, current - 1);
  }

  // ===============================
  // Folder Color Picker
  // ===============================

  function openFolderColorModal() {
    hideFolderOptionsModal();     // close ellipsis menu
    closeAllModals();             // global safety
  
    if (!folderColorModal) return;
  
    folderColorModal.classList.remove("hidden");
    folderColorModal.classList.add("flex");
  
    renderColorPicker(folderColorPickerModal, (color) => {
      applyFolderColor(color);
      closeAllModals();
    });

    if (folderColorWheel) {
      folderColorWheel.oninput = (e) => {
        const value = e.target.value;
    
        applyFolderColor({ value });
      };
    }    

    folderColorWheel.onchange = (e) => {
      applyFolderColor({ value: e.target.value });
      closeAllModals();
    };
    
  }
  
  


  function applyFolderColor(color) {
    if (!activeFolderId) return;
  
    const folderEl = document.querySelector(
      `li[data-folder-id="${activeFolderId}"]`
    );
    if (!folderEl) return;
  
    // Apply instantly (UX)
    folderEl.style.backgroundColor = color.value;
  
    // Persist to DB
    fetch(`/notes/folders/color/${activeFolderId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ color: color.value })
    });
  }

  
  
  


  

  // expose functions used by HTML
  window.toggleNotesSidebar = toggleNotesSidebar;
  window.toggleFolders = toggleFolders;
  window.toggleFoldersChevron = toggleFoldersChevron;
  window.openCreateFolderModal = openCreateFolderModal;
  window.closeCreateFolderModal = closeCreateFolderModal;
  window.openFolderOptions = openFolderOptions;
  window.openFolderContextMenu = openFolderContextMenu;
  window.startInlineRename = startInlineRename;
  window.deleteFolder = deleteFolder;
  window.createSubfolder = createSubfolder;
  window.decrementFolderCount = decrementFolderCount;
  window.openFolderColorModal = openFolderColorModal;
})();
