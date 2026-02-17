// ===============================
// GLOBAL MODAL SYSTEM
// ===============================
function closeAllModals() {
  document.querySelectorAll(".modal").forEach(modal => {
    modal.classList.add("hidden");
    modal.classList.remove("flex", "block");
  });
}

// Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeAllModals();
  }
});

// Click outside
document.addEventListener("click", (e) => {
  const openModal = document.querySelector(".modal:not(.hidden)");
  if (!openModal) return;

  // Clicked inside modal → ignore
  if (e.target.closest(".modal-content")) return;

  // Clicked the overlay itself → close
  if (e.target === openModal) {
    closeAllModals();
  }
});

// Close buttons
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-close-modal]")) {
    closeAllModals();
  }
});

document.getElementById("newFolderBtn")?.addEventListener("click", (e) => {
  e.stopPropagation(); // 🔥 CRITICAL
  openCreateFolderModal();
});