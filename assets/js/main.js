/*
	Arcana by HTML5 UP
	html5up.net | @ajlkn
	Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

	var	$window = $(window),
		$body = $('body');

	// Breakpoints.
		breakpoints({
			wide:      [ '1281px',  '1680px' ],
			normal:    [ '981px',   '1280px' ],
			narrow:    [ '841px',   '980px'  ],
			narrower:  [ '737px',   '840px'  ],
			mobile:    [ '481px',   '736px'  ],
			mobilep:   [ null,      '480px'  ]
		});

	// Play initial animations on page load.
		$window.on('load', function() {
			window.setTimeout(function() {
				$body.removeClass('is-preload');
			}, 100);
		});

	// Dropdowns.
		$('#nav > ul').dropotron({
			offsetY: -15,
			hoverDelay: 0,
			alignment: 'center'
		});

	// Nav.

		// Bar.
			var logoText = $('#logo').length ? $('#logo').html() : 'Xuejian Shen';
			$(
				'<div id="titleBar">' +
					'<a href="#navPanel" class="toggle"></a>' +
					'<span class="title">' + logoText + '</span>' +
				'</div>'
			)
				.appendTo($body);

		// Panel.
			$(
				'<div id="navPanel">' +
					'<nav>' +
						$('#nav').navList() +
					'</nav>' +
				'</div>'
			)
				.appendTo($body)
				.panel({
					delay: 500,
					hideOnClick: true,
					hideOnSwipe: true,
					resetScroll: true,
					resetForms: true,
					side: 'left',
					target: $body,
					visibleClass: 'navPanel-visible'
				});

})(jQuery);

// Lazy-load gallery autoplay videos when scrolled into view.
(function() {
	var videos = document.querySelectorAll('.gallery-video-lazy');
	if (!videos.length) return;

	function loadVideo(video) {
		if (video.dataset.loaded) return;
		var source = video.querySelector('source[data-src]');
		if (!source) return;
		source.src = source.getAttribute('data-src');
		video.load();
		video.dataset.loaded = 'true';
	}

	function playVideo(video) {
		loadVideo(video);
		video.play().catch(function() {});
	}

	if (!('IntersectionObserver' in window)) {
		videos.forEach(playVideo);
		return;
	}

	var observer = new IntersectionObserver(function(entries) {
		entries.forEach(function(entry) {
			var video = entry.target;
			if (entry.isIntersecting) {
				playVideo(video);
			} else {
				video.pause();
			}
		});
	}, { rootMargin: '100px', threshold: 0.1 });

	videos.forEach(function(video) {
		observer.observe(video);
	});
})();