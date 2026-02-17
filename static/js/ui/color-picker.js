// ui/color-picker.js
import { FOLDER_COLORS } from "../core/theme.js";

export function renderColorPicker(container, onSelect) {
  container.innerHTML = "";

  FOLDER_COLORS.forEach(color => {
    const btn = document.createElement("button");
    btn.className =
      "w-6 h-6 rounded-full border border-white/10 hover:scale-110 transition";
    if (color.value) {
      btn.style.backgroundColor = color.value;
    } else {
      btn.style.backgroundColor = "transparent";
      btn.title = "Default";
      btn.setAttribute("aria-label", "Default");
      btn.classList.add("border-white/30");
    }

    btn.onclick = () => onSelect(color);

    container.appendChild(btn);
  });
}
