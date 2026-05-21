document.addEventListener("DOMContentLoaded", function () {
  const closeBtn = document.getElementById("close-announcement");
  const banner = document.querySelector(".bd-header-announcement");

  if (banner) {
    banner.style.display = "none";
  }

  if (!sessionStorage.getItem("announcementClosed")) {
    if (banner) {
      banner.style.display = "block";
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        banner.style.display = "none";
        sessionStorage.setItem("announcementClosed", "true");
      });
    }
  }
});
