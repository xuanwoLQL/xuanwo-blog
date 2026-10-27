/* ==========================================================================
   漩涡 · interactions
   ========================================================================== */

(function () {
    'use strict';

    var root = document.documentElement;
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    /* ----------------------------------------------------------------------
       Theme
       ---------------------------------------------------------------------- */

    function currentTheme() {
        return root.dataset.theme === 'light' ? 'light' : 'dark';
    }

    function updateThemeColor() {
        var meta = document.querySelector('meta[name="theme-color"]');
        if (!meta) return;
        var bg = getComputedStyle(root).getPropertyValue('--bg').trim();
        if (bg) meta.setAttribute('content', bg);
    }

    function initTheme() {
        var toggle = document.getElementById('theme-toggle');
        updateThemeColor();
        if (!toggle) return;
        toggle.addEventListener('click', function () {
            var next = currentTheme() === 'dark' ? 'light' : 'dark';
            root.dataset.theme = next;
            try {
                localStorage.setItem('pref-theme', next);
            } catch (e) { /* storage disabled */ }
            updateThemeColor();
            document.dispatchEvent(new CustomEvent('vortex:themechange'));
        });
    }

    /* ----------------------------------------------------------------------
       Header / mobile menu
       ---------------------------------------------------------------------- */

    function initHeader() {
        var main = document.querySelector('main.main');
        if (main && !main.id) main.id = 'main';
        var header = document.getElementById('site-header');
        var toggle = document.getElementById('menu-toggle');
        var nav = document.getElementById('site-nav');
        var body = document.body;

        if (header) {
            var ticking = false;
            var onScroll = function () {
                if (ticking) return;
                ticking = true;
                window.requestAnimationFrame(function () {
                    header.classList.toggle('is-scrolled', window.scrollY > 12);
                    ticking = false;
                });
            };
            window.addEventListener('scroll', onScroll, { passive: true });
            onScroll();
        }

        if (!toggle || !nav) return;

        function closeNav() {
            body.classList.remove('nav-open');
            toggle.setAttribute('aria-expanded', 'false');
        }

        toggle.addEventListener('click', function () {
            var open = body.classList.toggle('nav-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });

        nav.addEventListener('click', function (event) {
            if (event.target.closest('a')) closeNav();
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') closeNav();
        });

        document.addEventListener('click', function (event) {
            if (!body.classList.contains('nav-open')) return;
            if (!event.target.closest('.site-header') && !event.target.closest('.site-nav')) {
                closeNav();
            }
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth > 760) closeNav();
        });
    }

    /* ----------------------------------------------------------------------
       Canvas vortex
       ---------------------------------------------------------------------- */

    function initVortex() {
        var canvas = document.getElementById('vortex-canvas');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        if (!ctx) return;

        var particles = [];
        var width = 0;
        var height = 0;
        var dpr = 1;
        var cx = 0;
        var cy = 0;
        var baseCx = 0;
        var baseCy = 0;
        var maxR = 300;
        var mouse = { x: 0, y: 0, active: false };
        var colors = { a: [94, 234, 212], b: [232, 197, 71] };
        var raf = 0;
        var running = false;
        var visible = true;
        var last = 0;

        function parseColor(value) {
            value = (value || '').trim();
            var hex = value.match(/^#([0-9a-f]{6})$/i);
            if (hex) {
                var n = parseInt(hex[1], 16);
                return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
            }
            var rgb = value.match(/rgba?\(([^)]+)\)/);
            if (rgb) {
                var parts = rgb[1].split(',').map(function (p) { return parseFloat(p); });
                return [parts[0] || 0, parts[1] || 0, parts[2] || 0];
            }
            return [94, 234, 212];
        }

        function readColors() {
            var style = getComputedStyle(root);
            colors.a = parseColor(style.getPropertyValue('--accent'));
            colors.b = parseColor(style.getPropertyValue('--accent-2'));
        }

        function mix(a, b, t) {
            return [
                Math.round(a[0] + (b[0] - a[0]) * t),
                Math.round(a[1] + (b[1] - a[1]) * t),
                Math.round(a[2] + (b[2] - a[2]) * t)
            ];
        }

        function resize() {
            var rect = canvas.getBoundingClientRect();
            width = Math.max(1, rect.width);
            height = Math.max(1, rect.height);
            dpr = Math.min(window.devicePixelRatio || 1, 1.6);
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            var hero = canvas.parentElement;
            var orb = hero ? hero.querySelector('.vortex-orb') : null;
            if (orb) {
                var hr = hero.getBoundingClientRect();
                var or = orb.getBoundingClientRect();
                baseCx = or.left - hr.left + or.width / 2;
                baseCy = or.top - hr.top + or.height / 2;
                maxR = Math.max(or.width * 1.35, Math.min(width, height) * 0.42);
            } else {
                baseCx = width * (width > 900 ? 0.72 : 0.5);
                baseCy = height * 0.5;
                maxR = Math.max(width, height) * 0.42;
            }
            cx = baseCx;
            cy = baseCy;

            var count = width < 700 ? 72 : (width < 1100 ? 120 : 160);
            if (particles.length !== count) {
                particles = [];
                for (var i = 0; i < count; i++) {
                    particles.push(makeParticle(true));
                }
            }
            canvas.dataset.particles = String(particles.length);
            canvas.dataset.size = Math.round(width) + 'x' + Math.round(height);
        }

        function makeParticle(spread) {
            var radius = spread
                ? maxR * (0.18 + Math.random() * 0.92)
                : maxR * (0.85 + Math.random() * 0.35);
            return {
                angle: Math.random() * Math.PI * 2,
                radius: radius,
                speed: 0.18 + Math.random() * 0.55,
                size: 0.5 + Math.random() * 1.6,
                phase: Math.random(),
                wobble: Math.random() * Math.PI * 2
            };
        }

        function draw(now) {
            if (!running) return;
            if (!last) last = now;
            var dt = Math.min((now - last) / 1000, 0.05);
            last = now;

            cx += (baseCx - cx) * 0.06;
            cy += (baseCy - cy) * 0.06;

            if (mouse.active) {
                cx += (mouse.x - width / 2) * 0.035;
                cy += (mouse.y - height / 2) * 0.025;
            }

            ctx.clearRect(0, 0, width, height);
            ctx.globalCompositeOperation = 'lighter';

            for (var i = 0; i < particles.length; i++) {
                var p = particles[i];
                var pull = 0.45 + 26 / (p.radius + 34);
                p.angle += p.speed * dt * pull;
                p.radius -= (5 + 150 / (p.radius + 48)) * dt * 0.42;

                if (p.radius < 5) {
                    p.radius = maxR * (0.9 + Math.random() * 0.35);
                    p.angle = Math.random() * Math.PI * 2;
                    p.phase = Math.random();
                }

                var t = 1 - p.radius / maxR;
                t = Math.max(0, Math.min(1, t));
                var wobble = Math.sin(now / 2600 + p.wobble) * 0.04;
                var angle = p.angle + wobble;
                var x = cx + Math.cos(angle) * p.radius;
                var y = cy + Math.sin(angle) * p.radius * 0.92;
                var prevAngle = angle - p.speed * dt * pull * 4.2;
                var px = cx + Math.cos(prevAngle) * (p.radius + 1.6);
                var py = cy + Math.sin(prevAngle) * (p.radius + 1.6) * 0.92;

                var color = mix(colors.a, colors.b, Math.min(1, t * 0.9 + p.phase * 0.22));
                var alpha = 0.06 + t * 0.42;
                ctx.strokeStyle = 'rgba(' + color[0] + ',' + color[1] + ',' + color[2] + ',' + alpha.toFixed(3) + ')';
                ctx.lineWidth = p.size * (0.6 + t * 1.1);
                ctx.beginPath();
                ctx.moveTo(px, py);
                ctx.lineTo(x, y);
                ctx.stroke();

                if (t > 0.72) {
                    ctx.fillStyle = 'rgba(' + color[0] + ',' + color[1] + ',' + color[2] + ',' + (t * 0.64).toFixed(3) + ')';
                    ctx.beginPath();
                    ctx.arc(x, y, p.size * 0.9, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            ctx.globalCompositeOperation = 'source-over';
            canvas.dataset.frames = String((parseInt(canvas.dataset.frames || '0', 10) || 0) + 1);
            raf = window.requestAnimationFrame(draw);
        }

        function start() {
            if (running) return;
            running = true;
            last = 0;
            raf = window.requestAnimationFrame(draw);
        }

        function stop() {
            running = false;
            if (raf) window.cancelAnimationFrame(raf);
            raf = 0;
        }

        function staticFrame() {
            resize();
            ctx.clearRect(0, 0, width, height);
            ctx.globalCompositeOperation = 'lighter';
            for (var i = 0; i < particles.length; i++) {
                var p = particles[i];
                var t = 1 - p.radius / maxR;
                var color = mix(colors.a, colors.b, Math.min(1, t));
                var x = cx + Math.cos(p.angle) * p.radius;
                var y = cy + Math.sin(p.angle) * p.radius * 0.92;
                ctx.fillStyle = 'rgba(' + color[0] + ',' + color[1] + ',' + color[2] + ',' + (0.1 + t * 0.4).toFixed(3) + ')';
                ctx.beginPath();
                ctx.arc(x, y, p.size, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.globalCompositeOperation = 'source-over';
        }

        readColors();
        resize();

        if (reduceMotion) {
            staticFrame();
        } else {
            start();
        }

        window.addEventListener('resize', function () {
            window.clearTimeout(canvas._resizeTimer);
            canvas._resizeTimer = window.setTimeout(function () {
                resize();
                if (reduceMotion) staticFrame();
            }, 160);
        });

        document.addEventListener('vortex:themechange', function () {
            readColors();
            if (reduceMotion) staticFrame();
        });

        document.addEventListener('visibilitychange', function () {
            if (document.hidden) stop();
            else if (!reduceMotion && visible) start();
        });

        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (entries) {
                visible = entries[0].isIntersecting;
                if (visible && !document.hidden && !reduceMotion) start();
                else stop();
            }, { threshold: 0 }).observe(canvas);
        }

        window.addEventListener('pointermove', function (event) {
            mouse.x = event.clientX;
            mouse.y = event.clientY;
            mouse.active = true;
        }, { passive: true });

        document.addEventListener('pointerleave', function () {
            mouse.active = false;
        });
    }

    /* ----------------------------------------------------------------------
       Reveal on scroll
       ---------------------------------------------------------------------- */

    function initReveal() {
        var items = document.querySelectorAll('[data-reveal], .reveal');
        if (!items.length) return;

        if (!('IntersectionObserver' in window) || reduceMotion) {
            for (var i = 0; i < items.length; i++) items[i].classList.add('is-visible');
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -6% 0px' });

        for (var j = 0; j < items.length; j++) observer.observe(items[j]);
    }

    /* ----------------------------------------------------------------------
       Animated counters
       ---------------------------------------------------------------------- */

    function initCounters() {
        var nums = document.querySelectorAll('.stat-num[data-count]');
        if (!nums.length) return;

        // The server renders the real values for no-JS readers and search crawlers.
        // Reset to zero only when the animation can actually run.
        if (!reduceMotion) {
            nums.forEach(function (el) { el.textContent = '0'; });
        }

        function animate(el) {
            var target = parseInt(el.getAttribute('data-count'), 10) || 0;
            if (reduceMotion) {
                el.textContent = String(target);
                return;
            }
            var start = performance.now();
            var duration = 1300;
            function frame(now) {
                var p = Math.min(1, (now - start) / duration);
                var eased = 1 - Math.pow(1 - p, 3);
                el.textContent = String(Math.round(target * eased));
                if (p < 1) window.requestAnimationFrame(frame);
            }
            window.requestAnimationFrame(frame);
        }

        if (!('IntersectionObserver' in window)) {
            nums.forEach(animate);
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animate(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        nums.forEach(function (el) { observer.observe(el); });
    }

    /* ----------------------------------------------------------------------
       Card spotlight
       ---------------------------------------------------------------------- */

    function initSpotlight() {
        var cards = document.querySelectorAll('.spotlight');
        if (!cards.length || window.matchMedia('(hover: none)').matches) return;

        cards.forEach(function (card) {
            var frame = 0;
            card.addEventListener('pointermove', function (event) {
                if (frame) return;
                frame = window.requestAnimationFrame(function () {
                    var rect = card.getBoundingClientRect();
                    card.style.setProperty('--mx', (event.clientX - rect.left) + 'px');
                    card.style.setProperty('--my', (event.clientY - rect.top) + 'px');
                    frame = 0;
                });
            });
        });
    }

    /* ----------------------------------------------------------------------
       Reading progress
       ---------------------------------------------------------------------- */

    function initReadingProgress() {
        var bar = document.getElementById('reading-progress');
        var article = document.querySelector('.article, .project-single');
        if (!bar || !article) return;

        var ticking = false;
        function update() {
            if (ticking) return;
            ticking = true;
            window.requestAnimationFrame(function () {
                var rect = article.getBoundingClientRect();
                var total = article.offsetHeight - window.innerHeight * 0.55;
                var scrolled = -rect.top + window.innerHeight * 0.28;
                var p = total > 0 ? scrolled / total : 0;
                p = Math.max(0, Math.min(1, p));
                bar.style.width = (p * 100).toFixed(2) + '%';
                ticking = false;
            });
        }
        window.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', update);
        update();
    }

    /* ----------------------------------------------------------------------
       TOC scroll spy
       ---------------------------------------------------------------------- */

    function initTocToggle() {
        var toc = document.querySelector('.article-toc');
        var button = toc ? toc.querySelector('.toc-toggle') : null;
        if (!toc || !button) return;
        button.addEventListener('click', function () {
            var open = toc.classList.toggle('is-open');
            button.setAttribute('aria-expanded', open ? 'true' : 'false');
            button.textContent = open ? '收起' : '展开';
        });
    }

    function initTocSpy() {
        var toc = document.querySelector('.article-toc');
        var body = document.querySelector('.article-body');
        if (!toc || !body || !('IntersectionObserver' in window)) return;

        var links = {};
        toc.querySelectorAll('a[href^="#"]').forEach(function (link) {
            var id = decodeURIComponent(link.getAttribute('href').slice(1));
            if (!id) return;
            links[id] = link;
            link.addEventListener('click', function () {
                Object.keys(links).forEach(function (key) {
                    links[key].classList.remove('active');
                });
                link.classList.add('active');
            });
        });

        var headings = body.querySelectorAll('h2[id], h3[id]');
        if (!headings.length) return;

        var current = null;
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var id = entry.target.id;
                if (current && links[current]) links[current].classList.remove('active');
                current = id;
                if (links[id]) links[id].classList.add('active');
            });
        }, { rootMargin: '-18% 0px -72% 0px', threshold: 0 });

        headings.forEach(function (h) { observer.observe(h); });
    }

    /* ----------------------------------------------------------------------
       Code copy buttons
       ---------------------------------------------------------------------- */

    function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text);
        }
        return new Promise(function (resolve, reject) {
            var area = document.createElement('textarea');
            area.value = text;
            area.style.position = 'fixed';
            area.style.opacity = '0';
            document.body.appendChild(area);
            area.select();
            try {
                document.execCommand('copy');
                resolve();
            } catch (error) {
                reject(error);
            }
            document.body.removeChild(area);
        });
    }

    function initCopyButtons() {
        var blocks = document.querySelectorAll('.highlight, .article-body pre, .project-body pre');
        blocks.forEach(function (block) {
            if (block.dataset.copyReady) return;
            if (block.closest('.highlight') && !block.classList.contains('highlight')) return;
            var code = block.querySelector('code');
            if (!code) return;
            block.dataset.copyReady = '1';
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'copy-code';
            button.textContent = '复制';
            button.setAttribute('aria-label', '复制代码');
            button.addEventListener('click', function () {
                copyText(code.innerText).then(function () {
                    button.textContent = '已复制';
                    button.classList.add('copied');
                    window.setTimeout(function () {
                        button.textContent = '复制';
                        button.classList.remove('copied');
                    }, 1800);
                });
            });
            block.appendChild(button);
        });
    }

    /* ----------------------------------------------------------------------
       Table wrappers
       ---------------------------------------------------------------------- */

    function initTables() {
        document.querySelectorAll('.article-body table, .project-body table').forEach(function (table) {
            if (table.parentElement && table.parentElement.classList.contains('table-wrap')) return;
            var wrap = document.createElement('div');
            wrap.className = 'table-wrap';
            table.parentNode.insertBefore(wrap, table);
            wrap.appendChild(table);
        });
    }

    /* ----------------------------------------------------------------------
       Image lightbox
       ---------------------------------------------------------------------- */

    function initLightbox() {
        var body = document.querySelector('.article-body, .project-body');
        if (!body) return;

        var overlay = document.createElement('div');
        overlay.className = 'lightbox';
        overlay.innerHTML = '<button class="lightbox-close" type="button" aria-label="关闭">×</button><img alt="">';
        document.body.appendChild(overlay);
        var img = overlay.querySelector('img');

        function close() {
            overlay.classList.remove('is-open');
            document.body.classList.remove('lightbox-open');
            img.removeAttribute('src');
        }

        body.addEventListener('click', function (event) {
            var target = event.target;
            if (target.tagName !== 'IMG') return;
            if (target.closest('a')) return;
            img.src = target.currentSrc || target.src;
            img.alt = target.alt || '';
            overlay.classList.add('is-open');
            document.body.classList.add('lightbox-open');
        });

        overlay.addEventListener('click', function (event) {
            if (event.target === overlay || event.target.classList.contains('lightbox-close')) close();
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && overlay.classList.contains('is-open')) close();
        });
    }

    /* ----------------------------------------------------------------------
       Filters (notes + projects)
       ---------------------------------------------------------------------- */

    function initFilterView(options) {
        var grid = document.getElementById(options.grid);
        if (!grid) return;
        var cards = Array.prototype.slice.call(grid.querySelectorAll(options.card));
        var chips = Array.prototype.slice.call(document.querySelectorAll(options.chips));
        var search = document.getElementById(options.search);
        var count = document.getElementById(options.count);
        var empty = document.getElementById(options.empty);
        var total = cards.length;
        var active = 'all';
        var query = '';

        function apply() {
            var visible = 0;
            cards.forEach(function (card) {
                var okCat = active === 'all' || card.dataset[options.dataKey] === active;
                var haystack = (card.dataset.search || '').toLowerCase();
                var okQuery = !query || haystack.indexOf(query) !== -1;
                var show = okCat && okQuery;
                card.hidden = !show;
                if (show) visible++;
            });
            if (count) {
                count.textContent = visible === total
                    ? '共 ' + total + (options.unit || ' 篇')
                    : '显示 ' + visible + ' / ' + total + (options.unit || ' 篇');
            }
            if (empty) empty.hidden = visible !== 0;
        }

        chips.forEach(function (chip) {
            chip.addEventListener('click', function () {
                active = chip.dataset.filter || 'all';
                chips.forEach(function (other) { other.classList.toggle('active', other === chip); });
                apply();
            });
        });

        if (search) {
            search.addEventListener('input', function () {
                query = search.value.trim().toLowerCase();
                apply();
            });
        }

        var params = new URLSearchParams(window.location.search);
        var cat = params.get('cat');
        if (cat) {
            var match = chips.find(function (chip) { return chip.dataset.filter === cat; });
            if (match) {
                active = cat;
                chips.forEach(function (chip) { chip.classList.toggle('active', chip === match); });
            }
        }
        apply();
    }

    function initFilters() {
        initFilterView({
            grid: 'notes-grid',
            card: '.note-card',
            chips: '.notes-toolbar .filter-chip',
            search: 'notes-search',
            count: 'notes-count',
            empty: 'notes-empty',
            dataKey: 'category',
            unit: ' 篇'
        });
        initFilterView({
            grid: 'projects-grid',
            card: '.project-card',
            chips: '.projects-toolbar .filter-chip',
            search: 'projects-search',
            count: 'projects-count',
            empty: 'projects-empty',
            dataKey: 'cat',
            unit: ' 个项目'
        });
    }

    /* ----------------------------------------------------------------------
       Keyboard shortcuts + back to top
       ---------------------------------------------------------------------- */

    function initSearchHints() {
        var box = document.getElementById('searchbox');
        if (!box) return;
        var terms = ['SSRF', '反序列化', '内网渗透', '密码学', 'Python'];
        var wrap = document.createElement('div');
        wrap.className = 'search-hints';
        var label = document.createElement('span');
        label.textContent = '试试搜索';
        wrap.appendChild(label);
        terms.forEach(function (term) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'search-hint';
            button.textContent = term;
            button.addEventListener('click', function () {
                var input = document.getElementById('searchInput');
                if (!input) return;
                input.value = term;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.focus();
            });
            wrap.appendChild(button);
        });
        box.appendChild(wrap);
    }

    function initShortcuts() {
        document.addEventListener('keydown', function (event) {
            var tag = (event.target.tagName || '').toLowerCase();
            var typing = tag === 'input' || tag === 'textarea' || event.target.isContentEditable;

            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                window.location.href = '/search/';
                return;
            }

            if (event.key === '/' && !typing) {
                var notesSearch = document.getElementById('notes-search');
                var projectsSearch = document.getElementById('projects-search');
                var globalSearch = document.getElementById('searchInput');
                if (globalSearch) {
                    event.preventDefault();
                    globalSearch.focus();
                } else if (notesSearch) {
                    event.preventDefault();
                    notesSearch.focus();
                } else if (projectsSearch) {
                    event.preventDefault();
                    projectsSearch.focus();
                } else {
                    event.preventDefault();
                    window.location.href = '/search/';
                }
            }
        });
    }

    function initBackToTop() {
        var link = document.getElementById('top-link');
        if (!link) return;
        var ticking = false;
        function update() {
            if (ticking) return;
            ticking = true;
            window.requestAnimationFrame(function () {
                link.classList.toggle('is-visible', window.scrollY > 600);
                ticking = false;
            });
        }
        window.addEventListener('scroll', update, { passive: true });
        link.addEventListener('click', function (event) {
            event.preventDefault();
            window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
            history.replaceState(null, '', window.location.pathname + window.location.search);
        });
        update();
    }

    /* ---------------------------------------------------------------------- */

    ready(function () {
        initTheme();
        initHeader();
        initVortex();
        initReveal();
        initCounters();
        initSpotlight();
        initReadingProgress();
        initTocToggle();
        initTocSpy();
        initCopyButtons();
        initTables();
        initLightbox();
        initFilters();
        initSearchHints();
        initShortcuts();
        initBackToTop();
        window.__vortexReady = true;
    });
})();
