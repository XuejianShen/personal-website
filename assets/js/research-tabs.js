(function () {
	var PROJECTS_BASE = '../projects/';
	var IMAGES_BASE = '../images/';

	function loadJSON(url) {
		return fetch(url).then(function (res) {
			if (!res.ok) throw new Error('Failed to load ' + url);
			return res.json();
		});
	}

	function loadProjects() {
		return loadJSON(PROJECTS_BASE + 'manifest.json').then(function (manifest) {
			var promises = manifest.map(function (filename) {
				return loadJSON(PROJECTS_BASE + filename);
			});
			return Promise.all(promises);
		});
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

	function renderTabs(container, projects) {
		if (!projects || projects.length === 0) {
			container.innerHTML = '<p><em>No projects found for this category.</em></p>';
			return;
		}

		var nav = document.createElement('div');
		nav.className = 'project-tabs-nav';
		nav.setAttribute('role', 'tablist');

		var content = document.createElement('div');
		content.className = 'project-tabs-content';

		projects.forEach(function (project, index) {
			var tabId = container.getAttribute('data-category') + '-tab-' + index;
			var panelId = container.getAttribute('data-category') + '-panel-' + index;

			var btn = document.createElement('button');
			btn.className = 'project-tab-btn' + (index === 0 ? ' active' : '');
			btn.textContent = project.title;
			btn.setAttribute('role', 'tab');
			btn.setAttribute('aria-selected', index === 0 ? 'true' : 'false');
			btn.setAttribute('aria-controls', panelId);
			btn.id = tabId;

			var panel = document.createElement('div');
			panel.className = 'project-tab-panel' + (index === 0 ? ' active' : '');
			panel.setAttribute('role', 'tabpanel');
			panel.setAttribute('aria-labelledby', tabId);
			panel.id = panelId;

			btn.addEventListener('click', function () {
				container.querySelectorAll('.project-tab-btn').forEach(function (b) {
					b.classList.remove('active');
					b.setAttribute('aria-selected', 'false');
				});
				container.querySelectorAll('.project-tab-panel').forEach(function (p) {
					p.classList.remove('active');
				});
				btn.classList.add('active');
				btn.setAttribute('aria-selected', 'true');
				panel.classList.add('active');
			});

			nav.appendChild(btn);

			var html = '';

			if (project.image) {
				html += '<div class="project-image">';
				html += '<img src="' + IMAGES_BASE + project.image + '" alt="' + project.title + '">';
				html += '</div>';
			}

			html += '<div class="project-description">' + project.description + '</div>';

			if (project.paperLinks && project.paperLinks.length > 0) {
				html += '<div class="project-papers">';
				html += '<span class="project-papers-label">Papers: </span>';
				project.paperLinks.forEach(function (link) {
					html += '<a href="' + link.url + '" target="_blank" rel="noopener">' + link.label + '</a> ';
				});
				html += '</div>';
			}

			panel.innerHTML = html;
			content.appendChild(panel);
		});

		container.appendChild(nav);
		container.appendChild(content);
	}

	function init() {
		var containers = document.querySelectorAll('.project-tabs');
		if (containers.length === 0) return;

		loadProjects()
			.then(function (projects) {
				var grouped = groupByCategory(projects);
				containers.forEach(function (container) {
					var category = container.getAttribute('data-category');
					renderTabs(container, grouped[category] || []);
				});
			})
			.catch(function (err) {
				console.error('Error loading research projects:', err);
			});
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
