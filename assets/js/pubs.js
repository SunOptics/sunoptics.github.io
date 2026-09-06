/* pubs.js — the publication filter. Load-bearing, not polish: 65 rows without
   it is a wall. Within a group the pills are OR; across groups they are AND. */
(function () {
  'use strict';

  var bar = document.getElementById('filters');
  if (!bar) return;

  var pills = [].slice.call(bar.querySelectorAll('.pill[data-filter]'));
  var reset = bar.querySelector('[data-filter="reset"]');
  var rows = [].slice.call(document.querySelectorAll('.pub[data-type]'));
  var count = document.getElementById('pub-count');
  var groups = document.querySelectorAll('.pub-list');
  var heads = document.querySelectorAll('.year-head');
  var total = rows.length;

  function state() {
    var s = {};
    pills.forEach(function (p) {
      if (p.getAttribute('aria-checked') !== 'true') return;
      var k = p.getAttribute('data-filter');
      (s[k] = s[k] || []).push(p.getAttribute('data-value'));
    });
    return s;
  }

  function apply() {
    var s = state();
    var keys = Object.keys(s);
    var shown = 0;

    rows.forEach(function (row) {
      var ok = keys.every(function (k) {
        return s[k].indexOf(row.getAttribute('data-' + k)) !== -1;
      });
      row.hidden = !ok;
      if (ok) shown++;
    });

    // Hide a section heading whose whole list filtered away.
    for (var i = 0; i < groups.length; i++) {
      var any = groups[i].querySelector('.pub:not([hidden])');
      groups[i].hidden = !any;
      if (heads[i]) heads[i].hidden = !any;
    }

    if (count) {
      count.textContent = keys.length
        ? 'Showing ' + shown + ' of ' + total
        : 'Showing all ' + total;
    }
    if (reset) reset.hidden = !keys.length;

    // Mirror into the hash so a filtered view is linkable — but never clobber
    // a deep link to one paper.
    var frag = keys.map(function (k) { return k + ':' + s[k].join('+'); }).join(',');
    var target = frag ? '#filter=' + frag : ' ';
    if (location.hash.indexOf('#filter=') === 0 || !location.hash || frag) {
      history.replaceState(null, '', frag ? target : location.pathname);
    }
  }

  pills.forEach(function (p) {
    if (p.getAttribute('data-filter') === 'reset') return;
    p.addEventListener('click', function () {
      p.setAttribute('aria-checked', p.getAttribute('aria-checked') === 'true' ? 'false' : 'true');
      apply();
    });
  });

  if (reset) {
    reset.addEventListener('click', function () {
      pills.forEach(function (p) { p.setAttribute('aria-checked', 'false'); });
      apply();
    });
  }

  // Restore from the hash on load.
  if (location.hash.indexOf('#filter=') === 0) {
    location.hash.slice(8).split(',').forEach(function (part) {
      var bits = part.split(':');
      if (bits.length !== 2) return;
      bits[1].split('+').forEach(function (val) {
        pills.forEach(function (p) {
          if (p.getAttribute('data-filter') === bits[0] && p.getAttribute('data-value') === val) {
            p.setAttribute('aria-checked', 'true');
          }
        });
      });
    });
  }
  apply();
})();
