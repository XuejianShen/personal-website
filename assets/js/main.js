/*
	Arcana by HTML5 UP
	html5up.net | @ajlkn
	Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

	var	$window = $(window),
		$body = $('body');
	var chinese = (document.documentElement.lang || '').toLowerCase().indexOf('zh') === 0;
	var menuOpenLabel = chinese ? '打开导航菜单' : 'Open navigation menu';
	var menuCloseLabel = chinese ? '关闭导航菜单' : 'Close navigation menu';

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
			var logoText = chinese ? '沈学简 · AI 译文' : ($('#logo').length ? $('#logo').html() : 'Xuejian Shen');
			$(
				'<div id="titleBar">' +
					'<a href="#navPanel" class="toggle" aria-label="' + menuOpenLabel + '" aria-controls="navPanel" aria-expanded="false"></a>' +
					'<span class="title">' + logoText + '</span>' +
				'</div>'
			)
				.appendTo($body);

		// Panel.
			$(
				'<div id="navPanel">' +
					'<nav aria-label="' + (chinese ? '移动端导航' : 'Mobile navigation') + '">' +
						$('#nav').navList() +
					'</nav>' +
				'</div>'
			)
				.appendTo($body)
				.panel({
					delay: 500,
					hideOnClick: true,
					hideOnEscape: true,
					hideOnSwipe: true,
					resetScroll: true,
					resetForms: true,
					side: 'left',
					target: $body,
					visibleClass: 'navPanel-visible'
				});



	// Keep the language switch visible in the mobile title bar as well as the menu.
	var languageSource = document.querySelector('#nav [data-language-switch]');
	if (languageSource) {
		var mobileLanguage = languageSource.cloneNode(true);
		mobileLanguage.classList.add('mobile-language-switch');
		document.getElementById('titleBar').appendChild(mobileLanguage);
		document.querySelectorAll('#navPanel a').forEach(function(link) {
			if (link.getAttribute('href') === languageSource.getAttribute('href')) {
				['data-language-switch', 'hreflang', 'lang', 'aria-label'].forEach(function(name) {
					link.setAttribute(name, languageSource.getAttribute(name) || '');
				});
			}
		});
	}
	function syncLanguageLinks() {
		document.querySelectorAll('[data-language-switch]').forEach(function(link) {
			link.setAttribute('href', link.getAttribute('href').split('#')[0] + window.location.hash);
		});
	}
	syncLanguageLinks();
	window.addEventListener('hashchange', syncLanguageLinks);
	window.addEventListener('popstate', syncLanguageLinks);
	document.addEventListener('click', syncLanguageLinks);

	// Keep the mobile menu's accessible state in step with the panel plugin.
	var menuToggle = document.querySelector('#titleBar .toggle');
	var menuPanel = document.getElementById('navPanel');
	function syncMenuState() {
		var expanded = document.body.classList.contains('navPanel-visible');
		menuToggle.setAttribute('aria-expanded', String(expanded));
		menuToggle.setAttribute('aria-label', expanded ? menuCloseLabel : menuOpenLabel);
		menuPanel.inert = !expanded;
		menuPanel.setAttribute('aria-hidden', String(!expanded));
	}
	if (menuToggle && menuPanel) {
		syncMenuState();
		new MutationObserver(syncMenuState).observe(document.body, { attributes: true, attributeFilter: ['class'] });
		document.addEventListener('keydown', function(event) {
			if (event.key === 'Escape' && document.body.classList.contains('navPanel-visible')) {
				menuToggle.focus();
			}
		});
	}

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
		// Keep gallery tiles still for reduced-motion and data-saving preferences.
		if ((window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
			|| (navigator.connection && navigator.connection.saveData)) return;
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

// Gallery lightbox: open a tile's media large in-page (index page only).
// Each .gallery-item carries: data-type="video|image", an <a class="gallery-tile" href="<full-res file>"
// data-full-label="..."> wrapping the in-page media, and a hidden <figcaption class="gallery-meta">
// with the title/credit HTML. Without JS the tile link simply opens the full-res file in a new tab.
(function() {
	var chinese = (document.documentElement.lang || '').toLowerCase().indexOf('zh') === 0;
	var items = Array.prototype.slice.call(document.querySelectorAll('.gallery-item'));
	if (!items.length) return;

	var lightbox = document.createElement('div');
	lightbox.className = 'gallery-lightbox';
	lightbox.setAttribute('role', 'dialog');
	lightbox.setAttribute('aria-modal', 'true');
	lightbox.setAttribute('aria-label', chinese ? '图像与视频浏览器' : 'Media viewer');
	lightbox.innerHTML =
		'<div class="gallery-lightbox-backdrop" data-action="close"></div>' +
		'<button type="button" class="gallery-lightbox-close" data-action="close" aria-label="' + (chinese ? '关闭（Esc）' : 'Close (Esc)') + '">&#x2715;</button>' +
		'<button type="button" class="gallery-lightbox-nav gallery-lightbox-prev" data-action="prev" aria-label="' + (chinese ? '上一项' : 'Previous') + '">&#x2039;</button>' +
		'<button type="button" class="gallery-lightbox-nav gallery-lightbox-next" data-action="next" aria-label="' + (chinese ? '下一项' : 'Next') + '">&#x203A;</button>' +
		'<figure class="gallery-lightbox-figure">' +
			'<div class="gallery-lightbox-media"></div>' +
			'<figcaption class="gallery-lightbox-caption">' +
				'<h3 class="gallery-lightbox-title"></h3>' +
				'<p class="gallery-lightbox-credit"></p>' +
				'<p class="gallery-lightbox-actions">' +
					'<a class="gallery-lightbox-full" target="_blank" rel="noopener noreferrer"></a>' +
					'<span class="gallery-lightbox-counter"></span>' +
				'</p>' +
			'</figcaption>' +
		'</figure>';
	document.body.appendChild(lightbox);

	var mediaBox = lightbox.querySelector('.gallery-lightbox-media');
	var titleEl = lightbox.querySelector('.gallery-lightbox-title');
	var creditEl = lightbox.querySelector('.gallery-lightbox-credit');
	var fullLink = lightbox.querySelector('.gallery-lightbox-full');
	var counterEl = lightbox.querySelector('.gallery-lightbox-counter');
	var closeBtn = lightbox.querySelector('.gallery-lightbox-close');
	var prevBtn = lightbox.querySelector('.gallery-lightbox-prev');
	var nextBtn = lightbox.querySelector('.gallery-lightbox-next');

	var current = -1;
	var lastFocus = null;
	var tileVideos = Array.prototype.slice.call(document.querySelectorAll('.gallery-video-lazy'));

	function textOf(item, selector) {
		var el = item.querySelector(selector);
		return el ? el.innerHTML : '';
	}

	function clearMedia() {
		var video = mediaBox.querySelector('video');
		if (video) {
			video.pause();
			video.removeAttribute('src');
			video.load();
		}
		mediaBox.innerHTML = '';
	}

	function render(index) {
		var item = items[index];
		var tile = item.querySelector('.gallery-tile');
		var type = item.getAttribute('data-type') || 'image';
		var title = textOf(item, '.gallery-meta-title') || textOf(item, '.gallery-tile-title');

		clearMedia();

		if (type === 'video') {
			var source = item.querySelector('video source');
			var src = source ? (source.getAttribute('data-src') || source.getAttribute('src')) : '';
			var video = document.createElement('video');
			video.controls = true;
			video.autoplay = true;
			video.muted = true;
			video.loop = true;
			video.setAttribute('playsinline', '');
			video.preload = 'auto';
			var poster = item.querySelector('video');
			if (poster && poster.getAttribute('poster')) video.poster = poster.getAttribute('poster');
			video.src = src;
			mediaBox.appendChild(video);
			video.play().catch(function() {});
		} else {
			var img = item.querySelector('img');
			var picture = document.createElement('img');
			picture.src = img ? img.getAttribute('src') : tile.getAttribute('href');
			picture.alt = img ? (img.getAttribute('alt') || '') : '';
			mediaBox.appendChild(picture);
		}

		titleEl.innerHTML = title;
		creditEl.innerHTML = textOf(item, '.gallery-meta-credit');
		fullLink.href = tile.getAttribute('href');
		fullLink.textContent = tile.getAttribute('data-full-label') || (chinese ? '打开全分辨率文件' : 'Open full resolution');
		counterEl.textContent = (index + 1) + ' / ' + items.length;
		prevBtn.disabled = index === 0;
		nextBtn.disabled = index === items.length - 1;
		current = index;
	}

	function open(index) {
		lastFocus = document.activeElement;
		tileVideos.forEach(function(v) { v.pause(); });
		render(index);
		lightbox.classList.add('is-open');
		document.body.classList.add('gallery-lightbox-open');
		closeBtn.focus();
	}

	function close() {
		if (current < 0) return;
		clearMedia();
		lightbox.classList.remove('is-open');
		document.body.classList.remove('gallery-lightbox-open');
		current = -1;
		// Resume in-page autoplay for tiles that were already loaded.
		tileVideos.forEach(function(v) {
			if (v.dataset.loaded) v.play().catch(function() {});
		});
		if (lastFocus && lastFocus.focus) lastFocus.focus();
	}

	function step(delta) {
		if (current < 0) return;
		var next = current + delta;
		if (next < 0 || next >= items.length) return;
		render(next);
	}

	items.forEach(function(item, index) {
		var tile = item.querySelector('.gallery-tile');
		if (!tile) return;
		tile.addEventListener('click', function(event) {
			// Let modified clicks (new tab, etc.) behave like a normal link.
			if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
			event.preventDefault();
			open(index);
		});
	});

	lightbox.addEventListener('click', function(event) {
		var target = event.target.closest('[data-action]');
		if (!target) return;
		var action = target.getAttribute('data-action');
		if (action === 'close') close();
		else if (action === 'prev') step(-1);
		else if (action === 'next') step(1);
	});

	document.addEventListener('keydown', function(event) {
		if (current < 0) return;
		if (event.key === 'Escape') { event.preventDefault(); close(); }
		else if (event.key === 'ArrowLeft') { event.preventDefault(); step(-1); }
		else if (event.key === 'ArrowRight') { event.preventDefault(); step(1); }
		else if (event.key === 'Tab') {
			// Keep keyboard focus inside the dialog.
			var focusable = Array.prototype.slice.call(
				lightbox.querySelectorAll('button:not([disabled]), a[href], video[controls]')
			);
			if (!focusable.length) return;
			var first = focusable[0], last = focusable[focusable.length - 1];
			if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
			else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
		}
	});

	// Horizontal swipe on touch screens moves between items.
	var touchStartX = null;
	lightbox.addEventListener('touchstart', function(event) {
		touchStartX = event.changedTouches[0].clientX;
	}, { passive: true });
	lightbox.addEventListener('touchend', function(event) {
		if (touchStartX === null) return;
		var dx = event.changedTouches[0].clientX - touchStartX;
		touchStartX = null;
		if (Math.abs(dx) > 60) step(dx < 0 ? 1 : -1);
	}, { passive: true });
})();
