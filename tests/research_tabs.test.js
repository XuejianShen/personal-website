// Run with: node --test tests/research_tabs.test.js
// This DOM fixture exercises URL history and keyboard behavior without packages.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'assets/js/research-tabs.js'), 'utf8');
const bundle = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'assets/js/projects-data.js'), 'utf8'), bundle);
const projects = JSON.parse(JSON.stringify(bundle.RESEARCH_PROJECTS));
const chineseBundle = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'assets/js/projects-data.zh-CN.js'), 'utf8'), chineseBundle);
const chineseProjects = JSON.parse(JSON.stringify(chineseBundle.RESEARCH_PROJECTS));

function fixture({ hash = '', vertical = false, data = projects, lang = 'en', missingData = false } = {}) {
	let document;
	class Element {
		constructor(tag) {
			this.tagName = tag;
			this.attributes = {};
			this.className = '';
			this.children = [];
			this.listeners = {};
			this.hidden = false;
			this.scrolls = 0;
			this.classList = {
				toggle: (name, enabled) => {
					const classes = new Set(this.className.split(/\s+/).filter(Boolean));
					if (enabled) classes.add(name); else classes.delete(name);
					this.className = [...classes].join(' ');
				},
				contains: (name) => this.className.split(/\s+/).includes(name)
			};
		}
		setAttribute(name, value) { this.attributes[name] = String(value); }
		getAttribute(name) { return this.attributes[name] ?? null; }
		removeAttribute(name) { delete this.attributes[name]; }
		appendChild(child) { this.children.push(child); return child; }
		addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
		fire(type, fields = {}) {
			const event = { prevented: false, preventDefault() { this.prevented = true; }, ...fields };
			(this.listeners[type] || []).forEach(fn => fn(event));
			return event;
		}
		focus() { document.activeElement = this; }
		scrollIntoView() { this.scrolls++; }
		querySelectorAll(selector) {
			const matches = element => selector === 'img[data-src]'
				? element.tagName === 'img' && element.getAttribute('data-src') !== null
				: selector.startsWith('.') && element.classList.contains(selector.slice(1));
			return this.children.flatMap(child => [...(matches(child) ? [child] : []), ...child.querySelectorAll(selector)]);
		}
		querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
		set innerHTML(html) {
			this.html = html;
			this.children = [];
			// Only image and permalink nodes need behavior in this fixture.
			for (const match of html.matchAll(/<(img|a)\s+([^>]+)>/g)) {
				if (match[1] === 'a' && !match[2].includes('class="project-permalink"')) continue;
				const element = new Element(match[1]);
				for (const attribute of match[2].matchAll(/([\w-]+)="([^"]*)"/g)) {
					element.setAttribute(attribute[1], attribute[2]);
					if (attribute[1] === 'class') element.className = attribute[2];
				}
				this.appendChild(element);
			}
		}
		get innerHTML() { return this.html; }
	}
	const containers = ['highz_galaxies', 'smbh'].map(category => {
		const element = new Element('div');
		element.className = 'project-tabs';
		element.setAttribute('data-category', category);
		return element;
	});
	document = {
		readyState: 'complete',
		documentElement: { lang },
		activeElement: null,
		createElement: tag => new Element(tag),
		querySelectorAll: selector => selector === '.project-tabs' ? containers : [],
	};
	const media = { matches: vertical, listeners: [], addEventListener(type, fn) { this.listeners.push(fn); } };
	const history = [hash];
	let historyIndex = 0;
	const windowListeners = {};
	const window = {
		location: { hash },
		requestAnimationFrame: fn => fn(),
		matchMedia: () => media,
		addEventListener(type, fn) { (windowListeners[type] ||= []).push(fn); },
		history: {
			pushState(state, unused, nextHash) {
				history.splice(++historyIndex);
				history.push(nextHash);
				window.location.hash = nextHash;
			}
		}
	};
	function fireLocationChange() {
		for (const name of ['popstate', 'hashchange']) (windowListeners[name] || []).forEach(fn => fn());
	}
	const errors = [];
	const context = { window, document, console: { error(message) { errors.push(message); } } };
	if (!missingData) context.RESEARCH_PROJECTS = data;
	vm.runInNewContext(source, context);
	const all = selector => containers.flatMap(c => c.querySelectorAll(selector));
	return {
		window, document, containers, errors,
		tab: id => all('.project-tab-btn').find(tab => tab.id === id + '-tab'),
		panel: id => all('.project-tab-panel').find(panel => panel.id === id),
		setHash(value) { window.location.hash = value; fireLocationChange(); },
		go(offset) { historyIndex += offset; window.location.hash = history[historyIndex]; fireLocationChange(); },
		setVertical(matches) { media.matches = matches; media.listeners.forEach(fn => fn()); }
	};
}

test('a shared Lumina URL opens the correct panel, including after project reordering', () => {
	const reordered = projects.map(project => ({ ...project, order: project.id === 'lumina' ? -1 : project.order }));
	for (const data of [projects, reordered]) {
		const page = fixture({ hash: '#lumina', data });
		assert.equal(page.panel('lumina').hidden, false);
		const inactiveImage = page.panel('uv-variability').querySelectorAll('img[data-src]')[0];
		assert.ok(inactiveImage, 'the inactive first panel keeps its deferred image source');
		assert.equal(inactiveImage.src, undefined, 'opening a deep link never assigns the first panel image source');
		assert.equal(page.tab('lumina').getAttribute('aria-selected'), 'true');
		assert.equal(page.tab('lumina').tabIndex, 0);
		assert.equal(page.panel('lumina').getAttribute('aria-labelledby'), 'lumina-tab');
		assert.equal(page.containers[0].scrolls, 1);
		assert.equal(page.panel('lumina').querySelector('.project-permalink').getAttribute('href'), '#lumina');
	}
});

test('legacy positional deep links also defer the inactive first image on initial load', () => {
	const page = fixture({ hash: '#highz_galaxies-panel-4' });
	assert.equal(page.panel('lumina').hidden, false);
	const inactiveImage = page.panel('uv-variability').querySelectorAll('img[data-src]')[0];
	assert.ok(inactiveImage);
	assert.equal(inactiveImage.src, undefined);
});

test('tab clicks update share URLs without jumping, and Back/Forward restore selection', () => {
	const page = fixture();
	page.tab('thesan-zoom').fire('click');
	assert.equal(page.window.location.hash, '#thesan-zoom');
	assert.equal(page.containers[0].scrolls, 0);
	assert.equal(page.panel('thesan-zoom').hidden, false);
	assert.equal(page.panel('uv-variability').hidden, true);
	page.tab('lumina').fire('click');
	page.go(-1);
	assert.equal(page.panel('thesan-zoom').hidden, false);
	page.go(-1);
	assert.equal(page.panel('uv-variability').hidden, false);
	page.go(1);
	assert.equal(page.panel('thesan-zoom').hidden, false);
	assert.equal(page.containers[0].scrolls, 2, 'duplicate popstate/hashchange events do not scroll twice');
});

test('direct hash changes activate projects in the second category and positional URLs still work', () => {
	const page = fixture();
	page.setHash('#dsidm-seeding');
	assert.equal(page.panel('dsidm-seeding').hidden, false);
	assert.equal(page.panel('quasar-luminosity-function').hidden, true);
	assert.equal(page.document.activeElement, page.tab('dsidm-seeding'));
	page.setHash('#highz_galaxies-panel-4');
	assert.equal(page.panel('lumina').hidden, false);
	page.setHash('#not-a-project');
	assert.equal(page.panel('lumina').hidden, false);
	assert.doesNotThrow(() => page.setHash('#bad%encoding'));
});

test('desktop arrow keys wrap focus, Home/End work, and activation remains explicit', () => {
	const page = fixture();
	let event = page.tab('uv-variability').fire('keydown', { key: 'ArrowRight' });
	assert.equal(event.prevented, true);
	assert.equal(page.document.activeElement, page.tab('tng-predictions'));
	assert.equal(page.panel('uv-variability').hidden, false, 'arrow focus does not activate a different panel');
	assert.equal(page.tab('tng-predictions').tabIndex, 0);
	assert.equal(page.tab('uv-variability').tabIndex, -1);
	page.tab('tng-predictions').fire('click');
	assert.equal(page.panel('tng-predictions').hidden, false);
	page.tab('tng-predictions').fire('keydown', { key: 'End' });
	assert.equal(page.document.activeElement, page.tab('lumina'));
	page.tab('lumina').fire('keydown', { key: 'Home' });
	assert.equal(page.document.activeElement, page.tab('uv-variability'));
	page.tab('uv-variability').fire('keydown', { key: 'ArrowLeft' });
	assert.equal(page.document.activeElement, page.tab('lumina'));
	event = page.tab('lumina').fire('keydown', { key: 'ArrowDown' });
	assert.equal(event.prevented, false, 'desktop vertical keys retain native page scrolling');
});

test('narrow-screen tabs expose vertical orientation and Up/Down keyboard controls', () => {
	const page = fixture({ vertical: true });
	const nav = page.containers[0].querySelector('.project-tabs-nav');
	assert.equal(nav.getAttribute('aria-orientation'), 'vertical');
	page.tab('uv-variability').fire('keydown', { key: 'ArrowDown' });
	assert.equal(page.document.activeElement, page.tab('tng-predictions'));
	page.tab('uv-variability').fire('keydown', { key: 'ArrowUp' });
	assert.equal(page.document.activeElement, page.tab('lumina'));
	assert.equal(page.tab('lumina').fire('keydown', { key: 'ArrowRight' }).prevented, false);
	page.setVertical(false);
	assert.equal(nav.getAttribute('aria-orientation'), 'horizontal');
});

test('unopened project images have no source until their panel is selected', () => {
	const page = fixture();
	const panel = page.panel('lumina');
	assert.equal(panel.querySelectorAll('img[data-src]').length, 1);
	const image = panel.querySelectorAll('img[data-src]')[0];
	assert.equal(image.src, undefined);
	page.tab('lumina').fire('click');
	assert.equal(image.src, '../images/whole_with_zoom_callout.png');
	assert.equal(image.getAttribute('data-src'), null);
	assert.equal(image.getAttribute('loading'), 'lazy');
	assert.equal(image.getAttribute('decoding'), 'async');
});


test('Chinese project data preserves all stable IDs, media paths, link targets, and ordering', () => {
	const structure = records => records.map(({ title, description, paperLinks, ...record }) => ({
		...record,
		paperLinks: paperLinks.map(({ label, ...link }) => link)
	}));
	assert.deepEqual(structure(chineseProjects), structure(projects));
	assert.equal(chineseProjects.length, 16);
	for (const project of chineseProjects) {
		assert.match(project.title, /[\u3400-\u9fff]/);
		assert.match(project.description, /[\u3400-\u9fff]/);
		for (const link of project.paperLinks) assert.match(link.label, /[\u3400-\u9fff]/);
	}
});

test('Chinese pages localize tabs, paper labels, permalink text, and ARIA without changing hash behavior', () => {
	const page = fixture({ hash: '#lumina', data: chineseProjects, lang: 'zh-CN' });
	assert.equal(page.tab('lumina').textContent, 'Lumina 计划');
	assert.equal(page.panel('lumina').hidden, false);
	assert.match(page.panel('lumina').innerHTML, /论文：/);
	assert.match(page.panel('lumina').innerHTML, /项目介绍（Zier 等，2026）/);
	const permalink = page.panel('lumina').querySelector('.project-permalink');
	assert.equal(permalink.getAttribute('href'), '#lumina');
	assert.equal(permalink.getAttribute('aria-label'), '此项目链接：Lumina 计划');
	assert.match(page.panel('lumina').innerHTML, />此项目链接<\/a>/);
	assert.equal(page.containers[0].querySelector('.project-tabs-nav').getAttribute('aria-label'), '高红移星系研究项目');
	page.tab('thesan-zoom').fire('click');
	assert.equal(page.window.location.hash, '#thesan-zoom');
	page.go(-1);
	assert.equal(page.panel('lumina').hidden, false);
	assert.ok(page.panel('uv-variability').querySelectorAll('img[data-src]')[0]);
});

test('Chinese empty and unavailable-data states are localized', () => {
	const empty = fixture({ data: chineseProjects.filter(project => project.category !== 'smbh'), lang: 'zh-CN' });
	assert.match(empty.containers[1].innerHTML, /暂无该类别的研究项目/);
	const unavailable = fixture({ lang: 'zh-CN', missingData: true });
	assert.match(unavailable.containers[0].innerHTML, /无法加载研究项目数据/);
	assert.deepEqual(unavailable.errors, ['未找到研究项目数据，请检查项目数据文件的加载顺序。']);
});

test('the builder rejects incomplete overlays, altered links, and missing paper labels', () => {
	const code = `
import copy
from build_projects import translate_projects
project = {'id': 'sample', 'category': 'sidm', 'order': 1, 'image': 'sample.jpg',
           'title': 'Sample', 'description': '<a href="https://example.org/paper">Paper</a>',
           'paperLinks': [{'label': 'Paper', 'url': 'https://example.org/paper'}]}
overlay = {'sample': {'title': '示例', 'description': '<a href="https://example.org/paper">论文</a>',
                      'paperLinks': ['论文']}}
original = copy.deepcopy(project)
translated = translate_projects([project], overlay)[0]
assert project == original
assert translated['paperLinks'][0]['url'] == project['paperLinks'][0]['url']
assert translated['id'] == project['id']
invalid = [dict(), dict(overlay, unknown=overlay['sample'])]
for field, value in [('description', '<a href="https://changed.example/">论文</a>'),
                     ('paperLinks', []), ('title', '')]:
    bad = copy.deepcopy(overlay)
    bad['sample'][field] = value
    invalid.append(bad)
for bad in invalid:
    try:
        translate_projects([project], bad)
    except ValueError:
        pass
    else:
        raise AssertionError('An incomplete or altered overlay was accepted')
`;
	const result = spawnSync('python3', ['-B', '-c', code], { cwd: root, encoding: 'utf8' });
	assert.equal(result.status, 0, result.stderr || result.stdout);
});
