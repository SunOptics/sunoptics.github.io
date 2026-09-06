/*
 * video.js — click-to-load video.
 *
 * Every thumbnail on this site is served from this domain, and no request
 * reaches YouTube until a visitor actually presses play. That keeps the page
 * fast (twenty-two embedded players would be several megabytes) and keeps
 * Google's cookies off the page for people who only came to read.
 */
(function () {
  'use strict';

  function play(button) {
    var id = button.getAttribute('data-video');
    if (!id) return;
    var frame = document.createElement('iframe');
    frame.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
                '?autoplay=1&rel=0';
    frame.title = button.getAttribute('data-title') || 'Video';
    frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; ' +
                  'gyroscope; picture-in-picture; web-share';
    frame.allowFullscreen = true;
    frame.loading = 'eager';
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    button.replaceWith(frame);
    frame.focus();
  }

  document.addEventListener('click', function (e) {
    var button = e.target.closest && e.target.closest('.video-play');
    if (button) { e.preventDefault(); play(button); }
  });
})();
