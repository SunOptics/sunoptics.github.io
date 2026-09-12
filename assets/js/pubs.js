/* pubs.js — searchable, shareable publication filters.
   Within a group the pills are OR; groups and search terms are AND. */
(function () {
  'use strict';

  var bar = document.getElementById('filters');
  if (!bar) return;

  var pills = [].slice.call(bar.querySelectorAll('.pill[data-value][data-filter]'));
  var reset = bar.querySelector('[data-filter="reset"]');
  var search = document.getElementById('pub-search');
  var rows = [].slice.call(document.querySelectorAll('.pub[data-type]'));
  var count = document.getElementById('pub-count');
  var heads = [].slice.call(document.querySelectorAll('.year-head'));
  var total = rows.length;
  var searchable = rows.map(function (row) {
    return ['.pub-title', '.pub-authors', '.pub-venue'].map(function (selector) {
      var field = row.querySelector(selector);
      return field ? field.textContent : '';
    }).join(' ').toLowerCase().replace(/\s+/g, ' ');
  });

  function state() {
    var s = {};
    pills.forEach(function (p) {
      if (p.getAttribute('aria-checked') !== 'true') return;
      var k = p.getAttribute('data-filter');
      (s[k] = s[k] || []).push(p.getAttribute('data-value'));
    });
    return s;
  }

  function apply(writeHash) {
    var s = state();
    var keys = Object.keys(s);
    var query = search ? search.value.trim() : '';
    var terms = query ? query.toLowerCase().split(/\s+/) : [];
    var active = keys.length > 0 || terms.length > 0;
    var shown = 0;

    rows.forEach(function (row, index) {
      var ok = keys.every(function (k) {
        return s[k].indexOf(row.getAttribute('data-' + k)) !== -1;
      }) && terms.every(function (term) {
        return searchable[index].indexOf(term) !== -1;
      });
      row.hidden = !ok;
      if (ok) shown++;
    });

    // Hide a section heading whose whole list filtered away.
    heads.forEach(function (head) {
      var group = head.nextElementSibling;
      if (!group || !group.classList.contains('pub-list')) return;
      var any = group.querySelector('.pub:not([hidden])');
      group.hidden = !any;
      head.hidden = !any;
    });

    if (count) {
      count.textContent = shown === 0
        ? 'No publications found. Try another search or clear the filters.'
        : active ? 'Showing ' + shown + ' of ' + total : 'Showing all ' + total;
    }
    if (reset) reset.hidden = !active;

    if (!writeHash) return;
    // Encode values separately so punctuation in a query cannot become a
    // filter delimiter. Preserve normal paper anchors when nothing is active.
    var parts = keys.map(function (k) {
      return k + ':' + s[k].map(encodeURIComponent).join('+');
    });
    if (query) parts.push('q:' + encodeURIComponent(query));
    var frag = parts.join(',');
    if (location.hash.indexOf('#filter=') === 0 || !location.hash || frag) {
      history.replaceState(null, '', location.pathname + location.search +
        (frag ? '#filter=' + frag : ''));
    }
  }

  pills.forEach(function (p) {
    p.addEventListener('click', function () {
      p.setAttribute('aria-checked', p.getAttribute('aria-checked') === 'true' ? 'false' : 'true');
      apply(true);
    });
  });

  if (search) search.addEventListener('input', function () { apply(true); });

  if (reset) {
    reset.addEventListener('click', function () {
      pills.forEach(function (p) { p.setAttribute('aria-checked', 'false'); });
      if (search) search.value = '';
      apply(true);
      if (search) search.focus();
    });
  }

  function decode(value) {
    try { return decodeURIComponent(value); } catch (e) { return ''; }
  }

  // A shared URL and browser history restore the same state. Paper anchors
  // clear any prior filters so their target remains visible.
  function restore() {
    pills.forEach(function (p) { p.setAttribute('aria-checked', 'false'); });
    if (search) search.value = '';
    if (location.hash.indexOf('#filter=') === 0) {
      location.hash.slice(8).split(',').forEach(function (part) {
        var colon = part.indexOf(':');
        if (colon < 0) return;
        var key = part.slice(0, colon);
        var value = part.slice(colon + 1);
        if (key === 'q') {
          if (search) search.value = decode(value);
          return;
        }
        value.split('+').forEach(function (encoded) {
          var val = decode(encoded);
          pills.forEach(function (p) {
            if (p.getAttribute('data-filter') === key && p.getAttribute('data-value') === val) {
              p.setAttribute('aria-checked', 'true');
            }
          });
        });
      });
    }
    apply(false);
  }
  window.addEventListener('hashchange', restore);
  restore();
})();
