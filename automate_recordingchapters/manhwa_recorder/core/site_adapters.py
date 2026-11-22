"""Website adapters: site-specific behaviour lives here, not in the controller.

Add a new site by subclassing SiteAdapter and registering it in ADAPTERS.
"""
from __future__ import annotations

from urllib.parse import urlparse


class SiteAdapter:
    name = "generic"
    domains: tuple[str, ...] = ()
    # CSS selector for chapter images ("" -> every <img> on the page)
    image_selector = "img"

    # JS returning {y, vh, h} of the element that actually scrolls.
    scroll_state_js = """() => {
        const se = document.scrollingElement || document.documentElement;
        return {y: Math.round(se.scrollTop), vh: Math.round(window.innerHeight),
                h: Math.round(se.scrollHeight)};
    }"""

    # JS returning true if the chapter bottom / navigation boundary has been reached
    end_boundary_js = """() => {
        // Look for Prev / Next navigation buttons or containers at bottom
        const navBtns = Array.from(document.querySelectorAll('button, a')).filter(el => {
            const t = (el.innerText || '').trim();
            return t === 'Prev' || t === 'Next' || t.includes('Prev') || t.includes('Next');
        });
        const bottomBtn = navBtns.length ? navBtns[navBtns.length - 1] : null;
        if (bottomBtn) {
            const r = bottomBtn.getBoundingClientRect();
            // If the top of the Prev/Next button is entering viewport (within 100px of bottom)
            if (r.top <= window.innerHeight + 60) {
                return true;
            }
        }
        return false;
    }"""

    # JS returning {x, y, w, h} of the manhwa comic content column in viewport
    content_box_js = """() => {
        const imgs = Array.from(document.querySelectorAll('img')).filter(i => (i.naturalHeight || i.height) > 300);
        if (!imgs.length) return null;
        const r = imgs[0].getBoundingClientRect();
        return {x: Math.round(r.x), y: 0, w: Math.round(r.width), h: window.innerHeight};
    }"""

    def images_loaded_js(self) -> str:
        sel = self.image_selector or "img"
        return f"""() => {{
            const imgs = Array.from(document.querySelectorAll({sel!r}));
            const done = imgs.filter(i => i.complete && i.naturalHeight > 0).length;
            return {{total: imgs.length, loaded: done}};
        }}"""

    def matches(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith("." + d) for d in self.domains)


class AsuraScansAdapter(SiteAdapter):
    name = "asurascans"
    domains = ("asurascans.com", "asuracomic.net", "asurascans.net")
    image_selector = "img"

    end_boundary_js = """() => {
        // Prev/Next buttons check
        const prevBtns = Array.from(document.querySelectorAll('button, a')).filter(el => {
            const t = (el.innerText || '').trim();
            return t === 'Prev' || t === '< Prev' || t.includes('Prev');
        });
        const btn = prevBtns.length ? prevBtns[prevBtns.length - 1] : null;
        if (btn && btn.offsetParent !== null) {
            const r = btn.getBoundingClientRect();
            if (r.top <= window.innerHeight + 10) return true;
        }
        // Also check last comic panel bottom
        const panels = Array.from(document.querySelectorAll('img')).filter(i => (i.src || '').includes('/chapters/') && (i.naturalHeight || i.height) > 300);
        if (panels.length) {
            const last = panels[panels.length - 1];
            // Stop immediately when the bottom of the last panel has reached the bottom of the viewport
            if (last.getBoundingClientRect().bottom <= window.innerHeight + 5) return true;
        }
        return false;
    }"""

    content_box_js = """() => {
        const panels = Array.from(document.querySelectorAll('img')).filter(i => (i.src || '').includes('/chapters/') && (i.naturalHeight || i.height) > 300);
        if (!panels.length) return null;
        const r = panels[0].getBoundingClientRect();
        return {x: Math.round(r.x), y: 0, w: Math.round(r.width), h: window.innerHeight};
    }"""

    def images_loaded_js(self) -> str:
        return """() => {
            const imgs = Array.from(document.querySelectorAll('img'))
                .filter(i => (i.naturalWidth || i.width) >= 300);
            const done = imgs.filter(i => i.complete && i.naturalHeight > 0).length;
            return {total: imgs.length, loaded: done};
        }"""


class LocalSampleAdapter(SiteAdapter):
    name = "local-sample"
    image_selector = "img.panel"

    end_boundary_js = """() => {
        const footer = document.getElementById('footer');
        if (footer) {
            const r = footer.getBoundingClientRect();
            if (r.top <= window.innerHeight + 30) return true;
        }
        return false;
    }"""

    content_box_js = """() => {
        const r = document.getElementById('reader') || document.querySelector('img.panel');
        if (!r) return null;
        const b = r.getBoundingClientRect();
        return {x: Math.round(b.x), y: 0, w: Math.round(b.width), h: window.innerHeight};
    }"""

    def matches(self, url: str) -> bool:
        return url.startswith("file:") and "sample_chapter" in url


ADAPTERS: list[SiteAdapter] = [AsuraScansAdapter(), LocalSampleAdapter()]
GENERIC = SiteAdapter()


def adapter_names() -> list[str]:
    return ["auto", GENERIC.name] + [a.name for a in ADAPTERS]


def get_adapter(url: str, name: str = "auto") -> SiteAdapter:
    if name not in ("", "auto"):
        for a in [GENERIC, *ADAPTERS]:
            if a.name == name:
                return a
    for a in ADAPTERS:
        if a.matches(url):
            return a
    return GENERIC
