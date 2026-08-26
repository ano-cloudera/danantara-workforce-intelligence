(function () {
  async function request(path, options = {}) {
    const response = await fetch(`/api-proxy/${path}`, options);
    const text = await response.text();
    let body;
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      body = { detail: text || "Unexpected empty response" };
    }
    if (!response.ok) {
      const detail = body?.detail?.message || body?.detail || body?.message || `Request failed (${response.status})`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return body;
  }

  window.WorkforceAPI = {
    get: path => request(path),
    post: (path, payload) => request(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    }),
    upload: formData => request("sources/upload", { method: "POST", body: formData }),
    download: async (path, payload, fallbackName = "download.pdf") => {
      const response = await fetch(`/api-proxy/${path}`, {
        method: payload ? "POST" : "GET",
        headers: payload ? { "content-type": "application/json" } : undefined,
        body: payload ? JSON.stringify(payload) : undefined,
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Download failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fallbackName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  };
})();
