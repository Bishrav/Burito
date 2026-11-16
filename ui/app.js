const clock = document.querySelector("#clock");
const date = document.querySelector("#date");
const toast = document.querySelector("#toast");

function updateClock() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString([], { hour12: false });
  date.textContent = now.toLocaleDateString([], { year: "numeric", month: "short", day: "2-digit" }).toUpperCase();
}
updateClock();
setInterval(updateClock, 1000);

document.querySelectorAll("[data-nav]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.nav;
    const section = document.getElementById(target);
    if (section) {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.nav === target));
    } else {
      toast.textContent = `${target.toUpperCase()} view is planned; no live data connection is configured.`;
      toast.classList.add("show");
      window.clearTimeout(window.buritoToastTimer);
      window.buritoToastTimer = window.setTimeout(() => toast.classList.remove("show"), 2600);
    }
  });
});

document.querySelector("#composer").addEventListener("submit", (event) => event.preventDefault());
