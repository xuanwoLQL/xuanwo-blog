(function () {
    'use strict';

    var root = document.documentElement;
    var preference = null;

    root.classList.add('js');

    try {
        preference = localStorage.getItem('pref-theme');
    } catch (error) {
        /* Storage can be disabled by browser privacy settings. */
    }

    var queryTheme = /[?&]theme=(light|dark)/.exec(window.location.search);
    if (queryTheme) preference = queryTheme[1];
    root.dataset.theme = preference === 'light' ? 'light' : 'dark';

    window.setTimeout(function () {
        if (window.__vortexReady) return;
        var items = document.querySelectorAll('.reveal, [data-reveal]');
        for (var i = 0; i < items.length; i++) items[i].classList.add('is-visible');
    }, 2600);
})();
