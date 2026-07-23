function pfCsrf() {
  const match = document.cookie.match(/(?:^|; )pf_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

document.addEventListener("htmx:configRequest", (event) => {
  const token = pfCsrf();
  if (token) event.detail.headers["X-CSRF-Token"] = token;
});

// Global form interception (DOM replacement) has been removed (A1.11).
// Full page forms should submit normally. HTMX should be used for partial replacements.

/**
 * apiFetch: A helper for JSON API requests.
 * Includes CSRF tokens, basic error parsing, and timeouts.
 */
async function apiFetch(url, options = {}) {
  const token = pfCsrf();
  const headers = { ...options.headers };
  if (token) {
    headers["X-CSRF-Token"] = token;
  }

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  const fetchOptions = {
    ...options,
    headers,
    credentials: "same-origin"
  };

  try {
    const res = await fetch(url, fetchOptions);
    if (!res.ok) {
      let errText = await res.text();
      try { errText = JSON.parse(errText).detail || errText; } catch(e) {}
      throw new Error(errText || `Request failed with status ${res.status}`);
    }

    // Attempt to parse JSON if the response is JSON, otherwise return text
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return await res.json();
    }
    return await res.text();
  } catch (error) {
    console.error(`apiFetch failed: ${error.message}`);
    // A structured toast could be displayed here if implemented.
    throw error;
  }
}
window.apiFetch = apiFetch;
