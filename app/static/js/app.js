function pfCsrf() {
  const match = document.cookie.match(/(?:^|; )pf_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

document.addEventListener("htmx:configRequest", (event) => {
  const token = pfCsrf();
  if (token) event.detail.headers["X-CSRF-Token"] = token;
});

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  if ((form.method || "get").toLowerCase() !== "post") return;
  if (form.hasAttribute("hx-post") || form.hasAttribute("hx-get")) return;

  event.preventDefault();
  const action = form.getAttribute("action") || window.location.href;
  fetch(action, {
    method: "POST",
    body: new FormData(form),
    credentials: "same-origin",
    headers: { "X-CSRF-Token": pfCsrf() },
    redirect: "manual"
  }).then((response) => {
    const location = response.headers.get("Location");
    if (response.status >= 300 && response.status < 400 && location) {
      window.location.href = location;
      return undefined;
    }
    return response.text().then((html) => {
      document.open();
      document.write(html);
      document.close();
    });
  }).catch(() => form.submit());
}, true);
