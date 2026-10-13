/**
 * ISAC Portal Frontend Engine
 * Includes Password Visibility Toggle, Dark Mode, Responsive Drawer,
 * and Interactive Slide Transitions Carousel.
 */

// Toggle Password Visibility (See / Unsee)
function togglePassword(inputId, triggerBtn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';

  if (triggerBtn) {
    const iconName = isPassword ? 'eye-off' : 'eye';
    triggerBtn.innerHTML = `<i data-lucide="${iconName}" class="eye-icon"></i>`;
    if (window.lucide && typeof lucide.createIcons === 'function') {
      lucide.createIcons();
    }
  }
}

// Global Theme Management & Mobile Drawer
(function () {
  const savedTheme = localStorage.getItem("isac-theme") || "light";
  document.documentElement.dataset.theme = savedTheme;

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".toast").forEach((toast) => {
      window.setTimeout(() => {
        toast.classList.add("is-hiding");
        window.setTimeout(() => toast.remove(), 300);
      }, 3000);
    });

    initSearchableSelects();
    initAnnouncementEventStatus();

    const themeBtn = document.getElementById("themeToggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", function () {
        const current = document.documentElement.dataset.theme;
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        localStorage.setItem("isac-theme", next);
        window.dispatchEvent(new CustomEvent("isac-theme-change", { detail: { theme: next } }));
        if (window.lucide) lucide.createIcons();
      });
    }

    const menuBtn = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    if (menuBtn && sidebar) {
      const closeMenu = (restoreFocus = false) => {
        sidebar.classList.remove("open");
        document.body.classList.remove("menu-open");
        menuBtn.setAttribute("aria-expanded", "false");
        menuBtn.setAttribute("aria-label", "Open navigation");
        if (restoreFocus) menuBtn.focus();
      };
      const openMenu = () => {
        sidebar.classList.add("open");
        document.body.classList.add("menu-open");
        menuBtn.setAttribute("aria-expanded", "true");
        menuBtn.setAttribute("aria-label", "Close navigation");
        const firstLink = sidebar.querySelector("nav a");
        if (firstLink) firstLink.focus();
      };
      menuBtn.addEventListener("click", function () {
        if (sidebar.classList.contains("open")) closeMenu();
        else openMenu();
      });
      if (backdrop) backdrop.addEventListener("click", () => closeMenu(true));
      sidebar.querySelectorAll("nav a").forEach((link) => {
        link.addEventListener("click", () => {
          if (window.innerWidth <= 960) closeMenu();
        });
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && sidebar.classList.contains("open")) closeMenu(true);
      });
      window.addEventListener("resize", () => {
        if (window.innerWidth > 960) closeMenu();
      });
    }

    // Initialize Slide Carousel if present
    initSlideShowcase();
  });
})();

function initSearchableSelects() {
  document.querySelectorAll("select[data-searchable-select]").forEach((select) => {
    const originalRequired = select.required;
    const label = select.labels && select.labels[0];
    const labelText = label ? label.textContent.trim() : "Choose an option";
    const wrapper = document.createElement("div");
    const trigger = document.createElement("button");
    const triggerText = document.createElement("span");
    const chevron = document.createElement("span");
    const menu = document.createElement("div");
    const search = document.createElement("input");
    const list = document.createElement("div");
    const status = document.createElement("small");
    const error = document.createElement("small");
    const options = Array.from(select.options).filter((option) => option.value !== "");
    const emptyLabel = select.dataset.emptyLabel || "Choose an option";
    const idBase = select.id || `searchable-${Math.random().toString(36).slice(2)}`;
    const listId = `${idBase}-options`;
    const optionButtons = [];

    wrapper.className = "searchable-select";
    trigger.type = "button";
    trigger.className = "searchable-select-trigger";
    trigger.id = `${idBase}-trigger`;
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-controls", listId);
    trigger.setAttribute("aria-label", labelText);
    triggerText.className = "searchable-select-value";
    chevron.className = "searchable-select-chevron";
    chevron.setAttribute("aria-hidden", "true");
    trigger.append(triggerText, chevron);

    menu.className = "searchable-select-menu";
    menu.hidden = true;
    search.type = "search";
    search.className = "searchable-select-search";
    search.placeholder = select.dataset.searchPlaceholder || "Search options…";
    search.setAttribute("aria-label", search.placeholder);
    search.setAttribute("aria-controls", listId);
    search.setAttribute("aria-autocomplete", "list");
    search.autocomplete = "off";
    list.className = "searchable-select-options";
    list.id = listId;
    list.setAttribute("role", "listbox");
    status.className = "searchable-select-status";
    status.setAttribute("role", "status");
    status.textContent = "No matching options.";
    status.hidden = true;
    error.className = "searchable-select-error";
    error.textContent = `Please select ${labelText.toLocaleLowerCase()}.`;
    error.hidden = true;

    options.forEach((option) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "searchable-select-option";
      item.setAttribute("role", "option");
      item.dataset.value = option.value;
      item.textContent = option.textContent.trim();
      item.setAttribute("aria-selected", option.selected ? "true" : "false");
      optionButtons.push(item);
      list.appendChild(item);
    });

    menu.append(search, list, status);
    const originalParent = select.parentNode;
    originalParent.insertBefore(wrapper, select);
    wrapper.append(trigger, menu, error, select);
    select.hidden = true;
    select.required = false;
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");
    wrapper.dataset.required = originalRequired ? "true" : "false";
    if (label) label.htmlFor = trigger.id;

    const updateValue = () => {
      const selected = select.options[select.selectedIndex];
      triggerText.textContent = selected && selected.value ? selected.textContent.trim() : emptyLabel;
      optionButtons.forEach((item) => {
        item.setAttribute("aria-selected", item.dataset.value === select.value ? "true" : "false");
      });
    };

    const filterOptions = () => {
      const query = search.value.trim().toLocaleLowerCase();
      let matches = 0;
      optionButtons.forEach((item) => {
        const match = item.textContent.toLocaleLowerCase().includes(query);
        item.hidden = !match;
        if (match) matches += 1;
      });
      status.hidden = matches > 0;
    };

    const closeMenu = (restoreFocus = false) => {
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      wrapper.classList.remove("is-open");
      if (restoreFocus) trigger.focus();
    };

    const openMenu = () => {
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      wrapper.classList.add("is-open");
      search.value = "";
      filterOptions();
      search.focus();
    };

    trigger.addEventListener("click", () => {
      if (menu.hidden) openMenu();
      else closeMenu();
    });

    search.addEventListener("input", filterOptions);
    search.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        const firstVisible = optionButtons.find((item) => !item.hidden);
        if (firstVisible) firstVisible.focus();
      } else if (event.key === "Enter") {
        const firstVisible = optionButtons.find((item) => !item.hidden);
        if (firstVisible) {
          event.preventDefault();
          firstVisible.click();
        }
      } else if (event.key === "Escape") {
        closeMenu(true);
      }
    });

    optionButtons.forEach((item, index) => {
      item.addEventListener("click", () => {
        select.value = item.dataset.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        error.hidden = true;
        trigger.removeAttribute("aria-invalid");
        wrapper.classList.remove("has-error");
        closeMenu(true);
      });
      item.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          closeMenu(true);
        } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          const step = event.key === "ArrowDown" ? 1 : -1;
          for (let i = 1; i <= optionButtons.length; i += 1) {
            const next = optionButtons[(index + step * i + optionButtons.length) % optionButtons.length];
            if (!next.hidden) {
              next.focus();
              break;
            }
          }
        }
      });
    });

    select.addEventListener("change", updateValue);
    document.addEventListener("click", (event) => {
      if (!wrapper.contains(event.target)) closeMenu();
    });

    const form = select.closest("form");
    if (form && !form.dataset.searchableSelectValidation) {
      form.dataset.searchableSelectValidation = "true";
      form.addEventListener("submit", (event) => {
        const missing = Array.from(form.querySelectorAll(".searchable-select[data-required='true']"))
          .filter((item) => !item.querySelector("select").value);
        form.querySelectorAll(".searchable-select[data-required='true']").forEach((item) => {
          const itemSelect = item.querySelector("select");
          const itemError = item.querySelector(".searchable-select-error");
          const itemTrigger = item.querySelector(".searchable-select-trigger");
          const invalid = !itemSelect.value;
          itemError.hidden = !invalid;
          if (invalid) {
            itemTrigger.setAttribute("aria-invalid", "true");
            item.classList.add("has-error");
          } else {
            itemTrigger.removeAttribute("aria-invalid");
            item.classList.remove("has-error");
          }
        });
        if (missing.length) {
          event.preventDefault();
          const firstMissing = missing[0];
          const firstTrigger = firstMissing.querySelector(".searchable-select-trigger");
          if (firstTrigger.getAttribute("aria-expanded") !== "true") firstTrigger.click();
          else firstMissing.querySelector(".searchable-select-search").focus();
        }
      });
    }

    updateValue();
  });
}

function initAnnouncementEventStatus() {
  const category = document.querySelector('.form-card select[name="category"]');
  const completedCheckbox = document.querySelector('[data-event-completed-field]');
  if (!category || !completedCheckbox) return;

  const field = completedCheckbox.closest("p");
  const syncVisibility = () => {
    const isEvent = category.value === "event";
    field.hidden = !isEvent;
    if (!isEvent) completedCheckbox.checked = false;
  };

  category.addEventListener("change", syncVisibility);
  syncVisibility();
}

/**
 * Interactive Slide Carousel with Smooth JavaScript Transitions
 */
function initSlideShowcase() {
  const track = document.getElementById("slidesTrack");
  if (!track) return;

  const slides = track.querySelectorAll(".slide-item");
  const prevBtn = document.getElementById("prevSlideBtn");
  const nextBtn = document.getElementById("nextSlideBtn");
  const dotsContainer = document.getElementById("sliderDots");
  const autoPlayBtn = document.getElementById("autoPlayToggle");

  if (!slides.length) return;

  let currentIndex = 0;
  const totalSlides = slides.length;
  let autoPlayTimer = null;
  let isPlaying = false;

  // Build Dots
  if (dotsContainer) {
    dotsContainer.innerHTML = "";
    slides.forEach((_, i) => {
      const dot = document.createElement("button");
      dot.className = `slider-dot ${i === 0 ? "active" : ""}`;
      dot.setAttribute("aria-label", `Slide ${i + 1}`);
      dot.addEventListener("click", () => goToSlide(i));
      dotsContainer.appendChild(dot);
    });
  }

  function updateSlidePosition() {
    track.style.transform = `translateX(-${currentIndex * 100}%)`;

    // Update dots
    if (dotsContainer) {
      const dots = dotsContainer.querySelectorAll(".slider-dot");
      dots.forEach((dot, idx) => {
        dot.classList.toggle("active", idx === currentIndex);
      });
    }

    // Update active tab buttons if any
    document.querySelectorAll(".slide-tab-nav").forEach((tab, idx) => {
      tab.classList.toggle("active", idx === currentIndex);
    });

    if (window.lucide) lucide.createIcons();
  }

  function goToSlide(index) {
    currentIndex = (index + totalSlides) % totalSlides;
    updateSlidePosition();
  }

  function nextSlide() {
    goToSlide(currentIndex + 1);
  }

  function prevSlide() {
    goToSlide(currentIndex - 1);
  }

  if (nextBtn) nextBtn.addEventListener("click", nextSlide);
  if (prevBtn) prevBtn.addEventListener("click", prevSlide);

  // Keyboard navigation
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") nextSlide();
    if (e.key === "ArrowLeft") prevSlide();
  });

  // Touch Swipe Support
  let touchStartX = 0;
  let touchEndX = 0;
  track.addEventListener("touchstart", (e) => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });

  track.addEventListener("touchend", (e) => {
    touchEndX = e.changedTouches[0].screenX;
    if (touchStartX - touchEndX > 50) nextSlide();
    if (touchEndX - touchStartX > 50) prevSlide();
  }, { passive: true });

  // Autoplay functionality
  if (autoPlayBtn) {
    autoPlayBtn.addEventListener("click", function () {
      if (isPlaying) {
        clearInterval(autoPlayTimer);
        isPlaying = false;
        autoPlayBtn.innerHTML = `<i data-lucide="play"></i> Play Slideshow`;
      } else {
        autoPlayTimer = setInterval(nextSlide, 3500);
        isPlaying = true;
        autoPlayBtn.innerHTML = `<i data-lucide="pause"></i> Pause Slideshow`;
      }
      if (window.lucide) lucide.createIcons();
    });
  }

  updateSlidePosition();
}
