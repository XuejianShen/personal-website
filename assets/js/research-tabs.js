(function () {
	var IMAGES_BASE = '../images/';
	var controllers = [];
	var targets = Object.create(null);
	var lastHash = null;
	var verticalTabs = window.matchMedia ? window.matchMedia('(max-width: 840px)') : null;
	var isChinese = document.documentElement && /^zh/i.test(document.documentElement.lang || '');
	var strings = isChinese ? {
		noProjects: '暂无该类别的研究项目。',
		loadError: '无法加载研究项目数据。',
		consoleError: '未找到研究项目数据，请检查项目数据文件的加载顺序。',
		researchProjects: '研究项目',
		papers: '论文：',
		permalink: '此项目链接',
		permalinkLabel: '此项目链接：'
	} : {
		noProjects: 'No projects found for this category.',
		loadError: 'Error: project data could not be loaded.',
		consoleError: 'RESEARCH_PROJECTS data not found. Make sure projects-data.js is loaded before research-tabs.js.',
		researchProjects: 'Research projects',
		papers: 'Papers:',
		permalink: 'Link to this project',
		permalinkLabel: 'Link to this project: '
	};
	var categoryLabels = isChinese ? {
		sidm: '自相互作用暗物质研究项目',
		axions: '轴子与超轻暗物质研究项目',
		highz_galaxies: '高红移星系研究项目',
		smbh: '超大质量黑洞研究项目'
	} : {
		sidm: 'Self-interacting dark matter projects',
		axions: 'Axion and ultra-light dark matter projects',
		highz_galaxies: 'High-redshift galaxy projects',
		smbh: 'Supermassive black hole projects'
	};

	function esc(s) {
		return String(s)
			.replace(/&/g, '&amp;')
			.replace(/"/g, '&quot;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');
	}

	function groupByCategory(projects) {
		var groups = {};
		projects.forEach(function (p) {
			if (!groups[p.category]) groups[p.category] = [];
			groups[p.category].push(p);
		});
		Object.keys(groups).forEach(function (cat) {
			groups[cat].sort(function (a, b) {
				return (a.order || 0) - (b.order || 0);
			});
		});
		return groups;
	}

	function updateHash(id) {
		var hash = '#' + encodeURIComponent(id);
		if (window.location.hash !== hash) {
			// Updating history avoids the browser's automatic jump on a tab click.
			if (window.history && window.history.pushState) {
				window.history.pushState(null, '', hash);
			} else {
				window.location.hash = hash;
			}
		}
		lastHash = id;
	}

	function readHash() {
		try {
			return decodeURIComponent(window.location.hash.slice(1));
		} catch (e) {
			return '';
		}
	}

	function applyHash(moveFocus) {
		var hash = readHash();
		if (hash === lastHash) return;
		lastHash = hash;
		if (!hash) {
			controllers.forEach(function (controller) { controller.activate(0); });
			return;
		}
		var target = targets[hash];
		if (!target) return;
		target.controller.activate(target.index);
		if (moveFocus) target.controller.buttons[target.index].focus({ preventScroll: true });
		// Show the tab labels as well as the requested panel when opening a shared URL.
		window.requestAnimationFrame(function () {
			target.controller.container.scrollIntoView({ block: 'start' });
		});
	}

	function renderTabs(container, projects) {
		if (!projects || projects.length === 0) {
			container.innerHTML = '<p><em>' + esc(strings.noProjects) + '</em></p>';
			return;
		}

		var category = container.getAttribute('data-category');
		var nav = document.createElement('div');
		nav.className = 'project-tabs-nav';
		nav.setAttribute('role', 'tablist');
		nav.setAttribute('aria-label', categoryLabels[category] || strings.researchProjects);
		function setOrientation() {
			nav.setAttribute('aria-orientation', verticalTabs && verticalTabs.matches ? 'vertical' : 'horizontal');
		}
		setOrientation();
		if (verticalTabs) {
			if (verticalTabs.addEventListener) verticalTabs.addEventListener('change', setOrientation);
			else if (verticalTabs.addListener) verticalTabs.addListener(setOrientation);
		}

		var content = document.createElement('div');
		content.className = 'project-tabs-content';
		var buttons = [];
		var panels = [];
		var controller = {
			container: container,
			buttons: buttons,
			activate: function (index) {
				buttons.forEach(function (button, i) {
					var selected = i === index;
					button.classList.toggle('active', selected);
					button.setAttribute('aria-selected', selected ? 'true' : 'false');
					button.tabIndex = selected ? 0 : -1;
					panels[i].classList.toggle('active', selected);
					panels[i].hidden = !selected;
				});
				panels[index].querySelectorAll('img[data-src]').forEach(function (image) {
					image.src = image.getAttribute('data-src');
					image.removeAttribute('data-src');
				});
			}
		};
		controllers.push(controller);

		projects.forEach(function (project, index) {
			var panelId = project.id;
			var tabId = panelId + '-tab';
			var btn = document.createElement('button');
			btn.type = 'button';
			btn.className = 'project-tab-btn';
			btn.textContent = project.title;
			btn.setAttribute('role', 'tab');
			btn.setAttribute('aria-controls', panelId);
			btn.id = tabId;

			var panel = document.createElement('div');
			panel.className = 'project-tab-panel';
			panel.setAttribute('role', 'tabpanel');
			panel.setAttribute('aria-labelledby', tabId);
			panel.id = panelId;
			panel.tabIndex = 0;
			panel.hidden = true;
			buttons.push(btn);
			panels.push(panel);

			function selectProject() {
				controller.activate(index);
				updateHash(panelId);
			}
			btn.addEventListener('click', selectProject);
			btn.addEventListener('keydown', function (event) {
				var isVertical = nav.getAttribute('aria-orientation') === 'vertical';
				var previous = isVertical ? 'ArrowUp' : 'ArrowLeft';
				var next = isVertical ? 'ArrowDown' : 'ArrowRight';
				var focusIndex;
				if (event.key === previous) focusIndex = (index + projects.length - 1) % projects.length;
				else if (event.key === next) focusIndex = (index + 1) % projects.length;
				else if (event.key === 'Home') focusIndex = 0;
				else if (event.key === 'End') focusIndex = projects.length - 1;
				else return;
				event.preventDefault();
				// Manual activation: Enter/Space retain native button behavior.
				buttons.forEach(function (button, i) { button.tabIndex = i === focusIndex ? 0 : -1; });
				buttons[focusIndex].focus();
			});
			nav.appendChild(btn);

			var html = '';
			if (project.image) {
				html += '<div class="project-image">';
				html += '<img data-src="' + IMAGES_BASE + esc(project.image) + '" alt="' + esc(project.title) + '" loading="lazy" decoding="async">';
				html += '</div>';
			}
			html += '<div class="project-description">' + project.description + '</div>';
			html += '<div class="project-papers">';
			if (project.paperLinks && project.paperLinks.length > 0) {
				html += '<span class="project-papers-label">' + esc(strings.papers) + ' </span>';
				project.paperLinks.forEach(function (link) {
					html += '<a href="' + esc(link.url) + '" target="_blank" rel="noopener">' + link.label + '</a> ';
				});
			}
			html += '<a class="project-permalink" href="#' + esc(panelId) + '" aria-label="' + esc(strings.permalinkLabel + project.title) + '">' + esc(strings.permalink) + '</a>';
			html += '</div>';
			panel.innerHTML = html;
			panel.querySelector('.project-permalink').addEventListener('click', function (event) {
				event.preventDefault();
				selectProject();
			});
			content.appendChild(panel);

			var target = { controller: controller, index: index };
			targets[panelId] = target;
			targets[tabId] = target;
			// Keep older positional anchors working while new URLs use stable project IDs.
			targets[category + '-panel-' + index] = target;
			targets[category + '-tab-' + index] = target;
		});

		container.appendChild(nav);
		container.appendChild(content);
		// Resolve the initial URL before assigning any image sources in this group.
		var initialTarget = targets[readHash()];
		controller.activate(initialTarget && initialTarget.controller === controller ? initialTarget.index : 0);
	}

	function init() {
		var containers = document.querySelectorAll('.project-tabs');
		if (containers.length === 0) return;
		if (typeof RESEARCH_PROJECTS === 'undefined' || !RESEARCH_PROJECTS) {
			console.error(strings.consoleError);
			containers.forEach(function (container) {
				container.innerHTML = '<p><em>' + esc(strings.loadError) + '</em></p>';
			});
			return;
		}
		var grouped = groupByCategory(RESEARCH_PROJECTS);
		containers.forEach(function (container) {
			var category = container.getAttribute('data-category');
			renderTabs(container, grouped[category] || []);
		});
		applyHash(false);
		window.addEventListener('hashchange', function () { applyHash(true); });
		window.addEventListener('popstate', function () { applyHash(true); });
	}

	if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
	else init();
})();
