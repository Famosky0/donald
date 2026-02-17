(function () {
  const trigger = document.getElementById("recentlyDeletedLink");
  const menu = document.getElementById("recentlyDeletedContextMenu");
  const modal = document.getElementById("deleteAllModal");
  const cancelBtn = document.querySelector("[data-cancel-delete-all]");
  const confirmBtn = document.querySelector("[data-confirm-delete-all]");
  const deleteAllBtn = document.getElementById("deleteAllTrigger");

  if (trigger && menu && modal && deleteAllBtn) {
    function openMenu(event) {
      event.preventDefault();
      event.stopPropagation();
      menu.style.top = `${event.clientY}px`;
      menu.style.left = `${event.clientX}px`;
      menu.classList.remove("hidden");
    }

    function hideMenu() {
      menu.classList.add("hidden");
    }

    function openModal() {
      modal.classList.remove("hidden");
      modal.classList.add("flex");
    }

    function closeModal() {
      modal.classList.add("hidden");
      modal.classList.remove("flex");
    }

    trigger.addEventListener("contextmenu", openMenu);

    deleteAllBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      hideMenu();
      openModal();
    });

    cancelBtn?.addEventListener("click", closeModal);

    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal();
      }
    });

    confirmBtn?.addEventListener("click", () => {
      fetch("/notes/recently-deleted/purge-all", {
        method: "POST"
      }).then(() => {
        window.location.href = "/notes/recently-deleted";
      });
    });

    document.addEventListener("click", hideMenu);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hideMenu();
        closeModal();
      }
    });
  }

  const mobileQuery = window.matchMedia("(max-width: 768px)");
  const layout = document.getElementById("notesLayout");
  const MOBILE_PAGE_KEY = "recentlyDeletedMobilePage";
  const NOTES_ROOT_URL = "/notes?folders=1";
  const RECENTLY_DELETED_LIST_URL = "/notes/recently-deleted";

  function computeInitialMobilePage() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("note_id")) return "note";
    return "list";
  }

  function setMobilePage(page, persist = true) {
    if (!layout) return;
    layout.dataset.mobilePage = page;
    if (persist) {
      sessionStorage.setItem(MOBILE_PAGE_KEY, page);
    }
  }

  function navigateRecentlyDeletedMobile(event, targetPage, url) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    if (mobileQuery.matches && targetPage) {
      if (targetPage === "folders") {
        sessionStorage.setItem("notesMobilePage", "folders");
        if (url) {
          window.location.href = url;
        }
        return;
      }

      sessionStorage.setItem(MOBILE_PAGE_KEY, targetPage);
    }

    window.location.href = url;
  }

  window.navigateRecentlyDeletedMobile = navigateRecentlyDeletedMobile;

  document.addEventListener("DOMContentLoaded", () => {
    if (!mobileQuery.matches || !layout) return;
    setMobilePage(computeInitialMobilePage(), false);
  });

  function getCurrentMobilePage() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("note_id")) return "note";
    return "list";
  }

  function routeToNotesRoot() {
    sessionStorage.setItem("notesMobilePage", "folders");
    window.location.href = NOTES_ROOT_URL;
  }

  function routeToRecentlyDeletedList() {
    setMobilePage("list");
    window.location.href = RECENTLY_DELETED_LIST_URL;
  }

  function setupMobileBackNavigation() {
    if (!mobileQuery.matches) return;

    const page = getCurrentMobilePage();
    const stateKey = `recentlyDeletedBack:${page}`;
    const currentState = window.history.state;

    if (!currentState || currentState.recentlyDeletedBack !== stateKey) {
      window.history.pushState(
        { recentlyDeletedBack: stateKey },
        "",
        window.location.href
      );
    }

    window.addEventListener("popstate", () => {
      if (!mobileQuery.matches) return;
      const currentPage = getCurrentMobilePage();
      if (currentPage === "note") {
        routeToRecentlyDeletedList();
        return;
      }
      routeToNotesRoot();
    });
  }

  document.addEventListener("DOMContentLoaded", setupMobileBackNavigation);
})();
