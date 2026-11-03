// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';
import { readFile, writeFile } from 'node:fs/promises';

const ogImage = 'https://egeoagents.com/og-image.png';

// Free URL audit (openspec add-public-url-audit): the landing form, the docs page,
// its sidebar entry and its llms.txt line ship only when the API is live.
// .github/workflows/site.yml sets the flag; src/content.config.ts drops the page.
const auditEnabled = process.env.PUBLIC_AUDIT_ENABLED === 'true';
const AUDIT_DOCS_PATH = '/docs/url-audit/';

/** Removes the audit docs line from the built llms.txt while the audit is off. */
const auditLlmsTxt = {
	name: 'egeo-audit-llms-txt',
	hooks: {
		'astro:build:done': async ({ dir }) => {
			if (auditEnabled) return;
			const file = new URL('llms.txt', dir);
			const text = await readFile(file, 'utf8');
			const kept = text.split('\n').filter((line) => !line.includes(AUDIT_DOCS_PATH));
			await writeFile(file, kept.join('\n'));
		},
	},
};

const globalSchema =JSON.stringify({
	'@context': 'https://schema.org',
	'@type': 'Organization',
	name: 'E-GEO',
	url: 'https://egeoagents.com',
	sameAs: [
		'https://github.com/mverab/eGEOagents',
		'https://arxiv.org/abs/2511.20867',
	],
	founder: {
		'@type': 'Person',
		name: 'Miguel Vera',
		sameAs: ['https://github.com/mverab'],
	},
});

export default defineConfig({
	site: 'https://egeoagents.com',
	integrations: [
		starlight({
			title: 'E-GEO',
			description:
				'E-GEO — open-source Generative Engine Optimization (GEO) & Answer Engine Optimization (AEO) toolkit (Python CLI + Claude Code skills), based on published GEO research (arXiv:2511.20867).',
			social: [
				{
					icon: 'github',
					label: 'GitHub',
					href: 'https://github.com/mverab/eGEOagents',
				},
			],
			components: {
				Footer: './src/components/Footer.astro',
			},
			editLink: {
				baseUrl: 'https://github.com/mverab/eGEOagents/edit/main/site/',
			},
			head: [
				{ tag: 'meta', attrs: { property: 'og:image', content: ogImage } },
				{ tag: 'meta', attrs: { property: 'og:image:width', content: '1200' } },
				{ tag: 'meta', attrs: { property: 'og:image:height', content: '630' } },
				{ tag: 'meta', attrs: { name: 'twitter:image', content: ogImage } },
				{
					tag: 'script',
					attrs: { type: 'application/ld+json' },
					content: globalSchema,
				},
			],
			sidebar: [
				{
					label: 'Documentation',
					items: [
						{ label: 'Getting Started', slug: 'docs/getting-started' },
						...(auditEnabled ? [{ label: 'Free URL Audit', slug: 'docs/url-audit' }] : []),
						{ label: 'How It Works', slug: 'docs/how-it-works' },
						{ label: 'CLI Reference', slug: 'docs/cli' },
						{ label: 'MCP-Based Validation', slug: 'docs/mcp-server' },
						{ label: 'GEO Loop', slug: 'docs/geo-loop' },
						{ label: 'Evaluation Harness', slug: 'docs/evaluation' },
						{ label: 'FAQ', slug: 'docs/faq' },
						{ label: 'Research', slug: 'research' },
					],
				},
				{
					label: 'Concepts',
					items: [
						{ label: 'What is GEO?', slug: 'concepts/what-is-geo' },
						{ label: 'What is AEO?', slug: 'concepts/what-is-aeo' },
						{ label: 'GEO vs SEO', slug: 'concepts/geo-vs-seo' },
						{ label: 'What is llms.txt?', slug: 'concepts/what-is-llms-txt' },
						{ label: 'The 10 GEO Features', slug: 'concepts/geo-features' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Rank in ChatGPT Search', slug: 'guides/rank-in-chatgpt-search' },
						{ label: 'Get Cited by Perplexity', slug: 'guides/rank-in-perplexity' },
						{ label: 'Track AI Citations', slug: 'guides/track-ai-citations' },
					],
				},
				{
					label: 'Compare',
					items: [
						{
							label: 'E-GEO vs geo-optimizer-skill',
							slug: 'compare/e-geo-vs-geo-optimizer-skill',
						},
						{ label: 'Open-Source GEO Tools in 2026', slug: 'compare/geo-tools-2026' },
					],
				},
			],
		}),
		sitemap(),
		auditLlmsTxt,
	],
});
