"""Serves the real AgentMemory viewer dashboard through the WebUI origin.

The viewer ships as one self-contained HTML page from the AgentMemory REST
server (GET /agentmemory/viewer). The user's browser cannot reach
container-local ports (only the WebUI port is published), so this handler
re-serves that page same-origin and injects a small shim that:

  1. rewrites the viewer's /agentmemory/* REST calls to the plugin
     passthrough handler (/api/plugins/agentmemory/passthrough), attaching
     the WebUI CSRF token;
  2. stubs window.WebSocket so the live-stream connection fails fast and the
     viewer falls back to its REST polling path (WebSockets cannot be
     proxied through the Flask WebUI).

The handler stays read-only: it only ever performs a GET against the
AgentMemory server and caches the page briefly.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request

from flask import Request, Response

from helpers.api import ApiHandler

_CACHE_TTL_SECONDS = 300
_page_cache: dict[str, object] = {"html": "", "fetched_at": 0.0}

SHIM = r"""
<script>
/* __agentmemory_embed_shim__ */
(function () {
  if (window.__agentmemoryEmbedShim) return;
  window.__agentmemoryEmbedShim = true;
  /* debug: surface JS errors via document.title for embed diagnosis */
  window.__embedErrors = [];
  function reportError(msg) {
    try {
      window.__embedErrors.push(String(msg).slice(0, 200));
      document.title = 'EMBED-ERR: ' + String(msg).slice(0, 120);
    } catch (e) {}
  }
  window.addEventListener('error', function (e) {
    var loc = (e && e.filename ? e.filename.split('/').pop() : '?') + ':' + (e && e.lineno) + ':' + (e && e.colno);
    reportError(((e && e.message) || 'error') + ' @' + loc);
  });
  window.addEventListener('unhandledrejection', function (e) {
    reportError('rejection: ' + ((e && e.reason && (e.reason.message || e.reason)) || '?'));
  });
  var PROXY_BASE = '/api/plugins/agentmemory/passthrough?path=';
  var csrfToken = '';
  var bootstrapPromise = fetch('/api/csrf_token', { credentials: 'same-origin' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { csrfToken = (d && d.token) || ''; })
    .catch(function () { csrfToken = ''; });
  var origFetch = window.fetch.bind(window);
  function rewrite(url) {
    var s = String(url);
    var m = s.match(/^(?:https?:\/\/[^\/]+)?\/agentmemory\/([^?#]+)/);
    if (!m) return null;
    var q = s.match(/\?([^#]*)/);
    var proxied = PROXY_BASE + encodeURIComponent(m[1]);
    if (q && q[1]) proxied += '&' + q[1];
    return proxied;
  }
  window.fetch = function (input, init) {
    init = init || {};
    var url = typeof input === 'string' ? input : (input && input.url) || String(input);
    var proxied = rewrite(url);
    if (!proxied) return origFetch(input, init);
    function call() {
      init.credentials = 'same-origin';
      var headers = new Headers(init.headers || {});
      if (csrfToken) headers.set('X-CSRF-Token', csrfToken);
      init.headers = headers;
      return origFetch(proxied, init).then(function (res) {
        if (res.status === 403) {
          return bootstrapPromise.then(function () { return origFetch(proxied, init); });
        }
        return res;
      });
    }
    if (csrfToken) return call();
    return bootstrapPromise.then(call);
  };
  /* WebSocket stub. The first instance fails fast ONCE so the viewer
     cleanly enters its REST-polling fallback (10s data refresh). Later
     instances stay silent, so the reconnect attempts stop churning. */
  var stubWsCount = 0;
  function StubWS(url) {
    this.url = url;
    this.readyState = 0;
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    var self = this;
    stubWsCount += 1;
    if (stubWsCount === 1) {
      setTimeout(function () {
        self.readyState = 3;
        var ev = { code: 1006, reason: 'embedded-mode', wasClean: false };
        if (typeof self.onclose === 'function') { try { self.onclose(ev); } catch (e) {} }
        (self._closeFns || []).forEach(function (fn) { try { fn(ev); } catch (e2) {} });
      }, 60);
    }
  }
  StubWS.prototype.close = function () { this.readyState = 3; };
  StubWS.prototype.send = function () {};
  StubWS.prototype.addEventListener = function (t, fn) {
    if (t === 'close') this._closeFns = (this._closeFns || []).concat(fn);
  };
  StubWS.prototype.removeEventListener = function () {};
  StubWS.prototype.dispatchEvent = function () { return false; };
  window.WebSocket = StubWS;
  /* Post-load patches: keep the dashboard usable in embedded mode.
     1) The viewer's refresh path wipes tab content (loading spinner) before
        fetching, which snaps scroll to the top on every 10s poll. Wrap every
        load* function to save/restore scroll positions of all scrollables.
     2) Show a stable status label instead of connecting/polling flicker. */
  window.addEventListener('load', function () {
    setTimeout(function () {
      if (window.__agentmemoryEmbedPatched) return;
      window.__agentmemoryEmbedPatched = true;
      function saveScrolls() {
        var saved = [];
        try {
          var doc = document.scrollingElement || document.documentElement;
          if (doc && doc.scrollTop > 0) saved.push([doc, doc.scrollTop]);
        } catch (e) {}
        try {
          document.querySelectorAll('*').forEach(function (el) {
            if (el.scrollTop > 0) saved.push([el, el.scrollTop]);
          });
        } catch (e2) {}
        return saved;
      }
      function restoreScrolls(saved) {
        saved.forEach(function (p) {
          try { if (Math.abs(p[0].scrollTop - p[1]) > 4) p[0].scrollTop = p[1]; } catch (e) {}
        });
      }
      Object.keys(window).forEach(function (k) {
        if (!/^load[A-Z]/.test(k) || typeof window[k] !== 'function') return;
        var orig = window[k];
        window[k] = function () {
          var saved = saveScrolls();
          var r = orig.apply(this, arguments);
          var restore = function () { restoreScrolls(saved); };
          if (r && typeof r.then === 'function') { r.then(restore, restore); }
          else { setTimeout(restore, 400); setTimeout(restore, 1500); }
          return r;
        };
      });
      if (typeof window.setWsStatus === 'function') {
        var origStatus = window.setWsStatus;
        window.setWsStatus = function () {
          return origStatus.call(this, 'embedded', 'connected');
        };
        window.setWsStatus('embedded', 'connected');
      }
      /* 3) Flicker-free refresh: the viewer resets state.<tab>.loaded=false
         before each refresh, and load<Tab>() wipes the view with a loading
         spinner when !loaded. Once a tab has rendered, make its loaded flag
         sticky so refreshes re-render silently over existing content
         (stale-while-revalidate) instead of flashing a spinner. */
      function stickyLoaded(obj) {
        if (!obj || typeof obj !== 'object' || !('loaded' in obj)) return;
        var val = obj.loaded;
        Object.defineProperty(obj, 'loaded', {
          get: function () { return val; },
          set: function (nv) {
            if (nv === false && val === true) return; /* swallow reset */
            val = nv;
          },
          configurable: true,
          enumerable: true,
        });
      }
      if (window.state && typeof window.state === 'object') {
        Object.keys(window.state).forEach(function (k) {
          stickyLoaded(window.state[k]);
        });
      }
    }, 0);
  });
})();
</script>
"""


def _target_base() -> str:
    import os

    override = os.environ.get("AGENTMEMORY_URL")
    if override:
        return override.rstrip("/")
    try:
        from helpers import plugins

        config = plugins.get_plugin_config("agentmemory") or {}
        url = str(config.get("url") or "").strip()
        if url:
            return url.rstrip("/")
    except Exception:
        pass
    return "http://localhost:3111"


def _viewer_candidates() -> list[str]:
    """Candidate bases for the standalone viewer page, best first.

    The REST endpoint (/agentmemory/viewer) serves a page whose inline
    script contains backslash-escaped quotes — syntactically invalid JS
    (verified with `node --check`). The standalone viewer server (3113+
    with fallback drift across restarts) serves the valid build, so we
    prefer it and only fall back to REST as a last resort.
    """
    import os

    bases: list[str] = []
    cached_base = str(_page_cache.get("base") or "")
    if cached_base:
        bases.append(cached_base)
    env_viewer = os.environ.get("AGENTMEMORY_VIEWER_URL")
    if env_viewer:
        bases.append(env_viewer.rstrip("/"))
    bases.extend(f"http://localhost:{p}" for p in (3113, 3114, 3115, 3116))
    bases.append(_target_base())  # REST fallback (known-broken script, last resort)
    seen: set[str] = set()
    return [b for b in bases if not (b in seen or seen.add(b))]


def _fetch_viewer_page() -> bytes:
    """Fetch the viewer page as raw bytes (never decode/re-encode).

    The viewer's inline app script is a single minified line; any lossy
    text transformation (utf-8 replace, newline normalization) corrupts it
    and produces a browser SyntaxError. Byte-safe end to end.
    """
    now = time.monotonic()
    cached = _page_cache.get("html")
    if isinstance(cached, bytes) and cached and now - float(_page_cache.get("fetched_at") or 0.0) < _CACHE_TTL_SECONDS:
        return cached
    last_error: Exception | None = None
    rest_base = _target_base().rstrip("/")
    for base in _viewer_candidates():
        base = base.rstrip("/")
        # REST base serves the page at /agentmemory/viewer; every standalone
        # viewer server serves it at the root path.
        url = f"{base}/agentmemory/viewer" if base == rest_base else f"{base}/"
        try:
            req = urllib.request.Request(url, method="GET", headers={"Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=6) as response:
                payload = response.read()
            if b"agentmemory viewer" not in payload[:4096] or len(payload) < 150000:
                continue
            _page_cache["html"] = payload
            _page_cache["fetched_at"] = now
            _page_cache["base"] = base
            return payload
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("no agentmemory viewer page available")


class Viewer(ApiHandler):
    """GET /api/plugins/agentmemory/viewer -> embedded real dashboard."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        # The iframe navigates here directly (plain GET, no JS headers yet).
        # requires_auth still applies; same-origin session cookies are sent.
        return False

    async def process(self, input: dict, request: Request) -> Response:
        noshim = (request.args.get("noshim") or "").lower() in {"1", "true", "yes"}
        try:
            html = _fetch_viewer_page()
            if noshim:
                return Response(html, status=200, content_type="text/html; charset=utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Response(
                "<html><body style='font-family:sans-serif;padding:24px'>"
                "<h3>AgentMemory viewer unavailable</h3>"
                f"<p>Could not reach the AgentMemory server: {exc}</p>"
                "<p>Start it inside the container with:"
                " <code>npx -y @agentmemory/agentmemory</code></p></body></html>",
                status=502,
                content_type="text/html; charset=utf-8",
            )
        shim_bytes = SHIM.encode("utf-8")
        marker = b"<head>"
        idx = html.find(marker)
        if idx == -1:
            html = shim_bytes + html
        else:
            idx += len(marker)
            html = html[:idx] + shim_bytes + html[idx:]
        response = Response(html, status=200, content_type="text/html; charset=utf-8")
        # Never let the browser cache the dashboard shell: a cached stale
        # page (e.g. the broken REST build) would keep breaking the panel.
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response
