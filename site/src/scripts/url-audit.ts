// Public URL audit: form submit, report rendering, #audit=<id> share links.
// Spec: openspec/changes/add-public-url-audit/specs/landing-url-audit/spec.md
// Every value from the API is inserted with textContent (never innerHTML): reports
// contain text from third-party pages.

const API_BASE: string = (import.meta.env.PUBLIC_AUDIT_API as string | undefined) || 'https://api.egeoagents.com';
const CLIENT_TIMEOUT_MS = 35_000;
const SERVICE_URL =
	'https://buy.stripe.com/dRm5kD7CrcPs8ILaco3Ru0j?utm_source=egeoagents&utm_medium=landing&utm_campaign=url_audit';

type Check = { id: string; status: 'pass' | 'fail' | 'unverifiable'; evidence: string; fix?: string };
type Feature = { id: string; score: number; recommendation?: string };
type Challenge = { vendor: string; http_status: number; evidence: string };
type Rewrite = {
	status: string;
	query: string;
	section_heading: string | null;
	before: string | null;
	after?: string;
	violations?: string[];
	note: string;
};
type Report = {
	id: string;
	url: string;
	final_url: string;
	query: string;
	query_source: 'visitor' | 'derived';
	checks: Check[];
	features: { method: string; note: string; items: Feature[] };
	rewrite: Rewrite;
	challenge: Challenge | null;
	created_at: string;
	expires_at: string;
};
type ApiError = { error: string; message: string };

const CHECK_LABELS: Record<string, string> = {
	ai_crawler_access: 'AI crawler access (robots.txt)',
	llms_txt: '/llms.txt',
	json_ld: 'JSON-LD structured data',
	title: '<title>',
	meta_description: 'Meta description',
	single_h1: 'One <h1>',
	visible_text: 'Text visible without JavaScript',
};
const FEATURE_LABELS: Record<string, string> = {
	ranking_emphasis: 'Ranking emphasis',
	user_intent: 'User intent',
	competitive_diff: 'Competitive differentiation',
	social_proof: 'Social proof',
	narrative: 'Narrative',
	authority: 'Authority',
	usps: 'Unique selling points',
	urgency: 'Urgency',
	scannable: 'Scannable format',
	factual: 'Factual specifics',
};
const REWRITE_REASONS: Record<string, string> = {
	no_change:
		'The model found nothing to improve in this section for this query, so there is no before/after to show. Try a more specific target query, such as the question your buyers ask.',
	withheld_fidelity:
		'We generated a rewrite but withheld it: it changed something the fidelity rules protect (links, numbers, headings, tables, code or length).',
	skipped_no_candidate:
		'No content section of 40–600 words was readable without JavaScript (navigation, footers and call-to-action blocks are skipped), so there was nothing to rewrite.',
	skipped_budget:
		'The free daily rewrites are used up. The checks and features above are complete — run the rewrite on your own machine with pip install egeo.',
	skipped_timeout:
		'The page took too long to load, so no time was left for the rewrite. Try again later, or run it locally with pip install egeo.',
	skipped_challenge: 'No rewrite was attempted because the page itself could not be read.',
	error: 'The rewrite failed this time. The checks and features above are complete; try again later.',
};

// ------------------------------------------------------------------ DOM helpers
function el<K extends keyof HTMLElementTagNameMap>(
	tag: K,
	props: { class?: string; text?: string; attrs?: Record<string, string> } = {},
	children: (Node | null | undefined)[] = []
): HTMLElementTagNameMap[K] {
	const node = document.createElement(tag);
	if (props.class) node.className = props.class;
	if (props.text !== undefined) node.textContent = props.text;
	for (const [k, v] of Object.entries(props.attrs || {})) node.setAttribute(k, v);
	for (const c of children) if (c) node.appendChild(c);
	return node;
}

function copyButton(text: string, label = 'copy'): HTMLButtonElement {
	const btn = el('button', { class: 'ua-copy', text: label, attrs: { type: 'button' } });
	btn.addEventListener('click', async () => {
		try {
			await navigator.clipboard.writeText(text);
			btn.textContent = 'copied';
			setTimeout(() => (btn.textContent = label), 1400);
		} catch {
			/* clipboard unavailable */
		}
	});
	return btn;
}

function chip(code: string): HTMLElement {
	return el('div', { class: 'ua-chip' }, [el('code', { text: code }), copyButton(code)]);
}

// ------------------------------------------------------------------ messages
export function retryText(seconds: number): string {
	if (!Number.isFinite(seconds) || seconds <= 0) return 'later';
	if (seconds < 3600) {
		const m = Math.max(1, Math.round(seconds / 60));
		return `in about ${m} minute${m === 1 ? '' : 's'}`;
	}
	const h = Math.round(seconds / 3600);
	return `in about ${h} hour${h === 1 ? '' : 's'}`;
}

export function errorMessage(err: ApiError, retryAfter: number | null): string {
	switch (err.error) {
		case 'invalid_url':
			return `Check the URL: ${err.message}`;
		case 'invalid_query':
			return `Check the target query: ${err.message}`;
		case 'blocked_target':
			return `This URL can't be audited: ${err.message}`;
		case 'rate_limited':
			return `The daily free audits are used up. Retry ${retryText(retryAfter ?? NaN)}, or run E-GEO locally with pip install egeo.`;
		case 'fetch_failed':
			return `We couldn't fetch that page. ${err.message}`;
		case 'audit_timeout':
			return 'The audit took too long. Please try again later.';
		case 'not_found':
			return 'This report expired (reports last 24 hours). Run the audit again below.';
		default:
			return err.message || 'Something went wrong. Please try again later.';
	}
}

const UNAVAILABLE =
	"The audit service is unavailable right now. You can run the same audit on your own machine: pip install egeo.";

// ------------------------------------------------------------------ API
type Result = { ok: true; report: Report } | { ok: false; status: number; error: ApiError; retryAfter: number | null } | { ok: false; status: 0 };

async function call(path: string, init?: RequestInit): Promise<Result> {
	const ctrl = new AbortController();
	const timer = setTimeout(() => ctrl.abort(), CLIENT_TIMEOUT_MS);
	try {
		const res = await fetch(API_BASE + path, { ...init, signal: ctrl.signal });
		const body = await res.json().catch(() => null);
		if (res.ok && body && (body as Report).id) return { ok: true, report: body as Report };
		const ra = res.headers.get('Retry-After');
		const error: ApiError = body && (body as ApiError).error ? (body as ApiError) : { error: 'unknown', message: '' };
		return { ok: false, status: res.status, error, retryAfter: ra ? Number(ra) : null };
	} catch {
		return { ok: false, status: 0 };
	} finally {
		clearTimeout(timer);
	}
}

// ------------------------------------------------------------------ rendering
function renderChecks(checks: Check[]): HTMLElement {
	const list = el('ul', { class: 'ua-checks' });
	for (const c of checks) {
		const li = el('li', { class: `ua-check ua-${c.status}` }, [
			el('span', { class: 'ua-status', text: c.status === 'unverifiable' ? 'unverifiable' : c.status }),
			el('div', { class: 'ua-check-body' }, [
				el('strong', { text: CHECK_LABELS[c.id] || c.id }),
				el('p', { class: 'ua-evidence', text: c.evidence }),
				c.fix ? el('div', { class: 'ua-fix' }, [el('p', { text: c.fix }), copyButton(c.fix, 'copy fix')]) : null,
			]),
		]);
		list.appendChild(li);
	}
	return list;
}

function renderChallenge(challenge: Challenge | null): HTMLElement | null {
	if (!challenge) return null;
	const vendorNames: Record<string, string> = {
		cloudflare: 'Cloudflare',
		perimeterx: 'PerimeterX',
		datadome: 'DataDome',
		imperva: 'Imperva',
		akamai: 'Akamai',
		'ddos-guard': 'DDoS-Guard',
	};
	const vendor = vendorNames[challenge.vendor];
	return el('aside', { class: 'ua-challenge' }, [
		el('p', {
			text: `The site answered with a ${vendor ? `${vendor} ` : ''}bot challenge (HTTP ${challenge.http_status}). AI crawlers may get the same challenge and fail to read the page.`,
		}),
	]);
}

function renderFeatures(features: Report['features']): HTMLElement {
	if (features.items.length === 0) {
		return el('div', {}, [
			el('p', { class: 'ua-label', text: 'Heuristic — not a ranking prediction' }),
			el('p', { class: 'ua-note', text: features.note }),
			el('p', { class: 'ua-reason', text: 'The features were not scored because the page itself could not be read.' }),
		]);
	}
	const list = el('ul', { class: 'ua-features' });
	for (const f of features.items) {
		list.appendChild(
			el('li', {}, [
				el('div', { class: 'ua-feat-head' }, [
					el('span', { text: FEATURE_LABELS[f.id] || f.id }),
					el('b', { text: `${f.score}/10` }),
				]),
				el('div', { class: 'ua-bar', attrs: { 'aria-hidden': 'true' } }, [
					el('i', { attrs: { style: `width:${Math.max(0, Math.min(10, f.score)) * 10}%` } }),
				]),
				f.recommendation ? el('p', { class: 'ua-rec', text: f.recommendation }) : null,
			])
		);
	}
	return el('div', {}, [
		el('p', { class: 'ua-label', text: 'Heuristic — not a ranking prediction' }),
		el('p', { class: 'ua-note', text: features.note }),
		list,
	]);
}

function renderRewrite(rw: Rewrite, source: Report['query_source']): HTMLElement {
	const queryLine = el('p', { class: 'ua-query' }, [
		document.createTextNode('Query: '),
		el('b', { text: rw.query }),
		document.createTextNode(source === 'visitor' ? ' (your query)' : ' (derived from the page title)'),
	]);
	if (rw.status === 'shown' && rw.after !== undefined) {
		return el('div', {}, [
			queryLine,
			el('div', { class: 'ua-diff' }, [
				el('figure', {}, [el('figcaption', { text: 'Before' }), el('pre', { text: rw.before || '' })]),
				el('figure', {}, [
					el('figcaption', {}, [document.createTextNode('After '), copyButton(rw.after, 'copy rewrite')]),
					el('pre', { text: rw.after }),
				]),
			]),
			el('p', { class: 'ua-note', text: rw.note }),
		]);
	}
	const box = el('div', {}, [queryLine, el('p', { class: 'ua-reason', text: REWRITE_REASONS[rw.status] || rw.status })]);
	if (rw.status === 'withheld_fidelity' && rw.violations?.length) {
		box.appendChild(el('ul', { class: 'ua-violations' }, rw.violations.map((v) => el('li', {}, [el('code', { text: v })]))));
	}
	return box;
}

function renderCtas(url: string): HTMLElement {
	return el('div', { class: 'ua-ctas' }, [
		el('p', { text: 'Fix the rest yourself, or have it done:' }),
		chip('pip install egeo'),
		chip(`/geo ${url}`),
		el('a', { class: 'ua-service', text: 'GEO Audit & Implementation — $199 →', attrs: { href: SERVICE_URL } }),
	]);
}

function renderReport(r: Report): HTMLElement {
	const expires = new Date(r.expires_at);
	const share = el('button', { class: 'ua-copy', text: 'copy link', attrs: { type: 'button' } });
	share.addEventListener('click', async () => {
		try {
			await navigator.clipboard.writeText(location.href);
			share.textContent = 'copied';
			setTimeout(() => (share.textContent = 'copy link'), 1400);
		} catch {
			/* clipboard unavailable */
		}
	});
	return el('div', { class: 'ua-report' }, [
		el('div', { class: 'ua-head' }, [
			el('h2', { text: 'Audit report' }),
			el('p', { class: 'ua-url', text: r.final_url }),
			el('p', { class: 'ua-meta' }, [
				document.createTextNode(`Link expires ${isNaN(+expires) ? r.expires_at : expires.toLocaleString()}. `),
				share,
			]),
		]),
		renderChallenge(r.challenge),
		el('section', { class: 'ua-block' }, [el('h3', { text: 'Technical checks' }), renderChecks(r.checks)]),
		el('section', { class: 'ua-block' }, [el('h3', { text: 'GEO features' }), renderFeatures(r.features)]),
		el('section', { class: 'ua-block' }, [
			el('h3', {
				text: r.rewrite.section_heading ? `One section, rewritten: “${r.rewrite.section_heading}”` : 'One section, rewritten',
			}),
			renderRewrite(r.rewrite, r.query_source),
		]),
		renderCtas(r.url),
	]);
}

// ------------------------------------------------------------------ wiring
export function initUrlAudit(): void {
	const form = document.getElementById('audit-form') as HTMLFormElement | null;
	const out = document.getElementById('audit-report');
	const outBody = document.getElementById('audit-report-body');
	if (!form || !out || !outBody) return;
	const status = form.querySelector('.ua-status-line') as HTMLElement;
	const steps = form.querySelector('.ua-steps') as HTMLElement;
	const submit = form.querySelector('button[type="submit"]') as HTMLButtonElement;
	let stepTimers: number[] = [];

	const showSteps = (on: boolean) => {
		stepTimers.forEach(clearTimeout);
		stepTimers = [];
		steps.hidden = !on;
		const items = Array.from(steps.querySelectorAll('li'));
		items.forEach((li) => li.classList.remove('on'));
		if (on) items.forEach((li, i) => stepTimers.push(window.setTimeout(() => li.classList.add('on'), i * 4000)));
	};
	const say = (msg: string, fallback = false) => {
		status.textContent = msg;
		status.hidden = !msg;
		status.classList.toggle('ua-error', !!msg);
		if (fallback) status.appendChild(el('span', {}, [document.createTextNode(' '), copyButton('pip install egeo')]));
	};
	const show = (report: Report) => {
		outBody.replaceChildren(renderReport(report));
		out.hidden = false;
		history.replaceState(null, '', `#audit=${encodeURIComponent(report.id)}`);
		out.scrollIntoView({ behavior: 'smooth', block: 'start' });
	};
	const handle = (res: Result) => {
		if (res.ok) {
			say('');
			show(res.report);
			return;
		}
		if (res.status === 0) {
			say(UNAVAILABLE, true);
			return;
		}
		say(errorMessage(res.error, res.retryAfter));
	};

	form.addEventListener('submit', async (ev) => {
		ev.preventDefault();
		const data = new FormData(form);
		const url = String(data.get('url') || '').trim();
		const q = String(data.get('query') || '').trim();
		if (!url) return;
		say('');
		submit.disabled = true;
		showSteps(true);
		const res = await call('/api/audit', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url, query: q || null }),
		});
		showSteps(false);
		submit.disabled = false;
		handle(res);
	});

	const m = location.hash.match(/^#audit=([A-Za-z0-9_-]{8,64})$/);
	if (m) {
		call(`/api/audit/${m[1]}`).then((res) => {
			if (!res.ok && res.status === 404) {
				history.replaceState(null, '', location.pathname + location.search);
				say(errorMessage({ error: 'not_found', message: '' }, null));
				form.scrollIntoView({ behavior: 'smooth', block: 'center' });
				return;
			}
			handle(res);
		});
	}
}
