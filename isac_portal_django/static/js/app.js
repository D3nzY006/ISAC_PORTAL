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
