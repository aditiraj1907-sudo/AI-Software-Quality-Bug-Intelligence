// Small client for the backend API. Every page script talks to the server through this file.
(function () {
  const BASE = (window.QBI_API_BASE || '').replace(/\/$/, '');

  function showOffline() {
    if (document.getElementById('offline-banner')) return;
    const b = document.createElement('div');
    b.id = 'offline-banner';
    b.className = 'banner';
    b.setAttribute('role', 'alert');
    b.innerHTML = '<strong>This page needs the backend.</strong> Start it from the project folder with ' +
      '<code>uvicorn backend.main:app --reload</code> and open <code>http://127.0.0.1:8000</code>. ' +
      'Opening the HTML files directly from disk will not work.';
    const main = document.querySelector('main');
    main.insertBefore(b, main.firstChild);
  }

  async function request(method, path, body) {
    let res;
    try {
      res = await fetch(BASE + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined
      });
    } catch (e) {
      showOffline();
      const err = new Error('The backend is not reachable.');
      err.offline = true;
      throw err;
    }
    if (!res.ok) {
      let msg = res.statusText || 'Request failed';
      try {
        const j = await res.json();
        if (typeof j.detail === 'string') msg = j.detail;
        else if (Array.isArray(j.detail) && j.detail[0] && j.detail[0].msg) msg = String(j.detail[0].msg).replace(/^Value error, /, '');
      } catch (e) { /* keep the status text */ }
      throw new Error(msg);
    }
    return res.json();
  }

  window.api = {
    get: path => request('GET', path),
    post: (path, body) => request('POST', path, body || {}),
    del: path => request('DELETE', path)
  };
})();
