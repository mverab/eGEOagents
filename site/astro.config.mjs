// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';

const globalSchema = JSON.stringify({
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
			editLink: {
				baseUrl: 'https://github.com/mverab/eGEOagents/edit/main/site/',
			},
			head: [
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
						{ label: 'How It Works', slug: 'docs/how-it-works' },
						{ label: 'CLI Reference', slug: 'docs/cli' },
						{ label: 'MCP Server', slug: 'docs/mcp-server' },
						{ label: 'GEO Loop', slug: 'docs/geo-loop' },
						{ label: 'Evaluation Harness', slug: 'docs/evaluation' },
						{ label: 'FAQ', slug: 'docs/faq' },
					],
				},
				{
					label: 'Concepts',
					items: [
						{ label: 'What is GEO?', slug: 'concepts/what-is-geo' },
						{ label: 'What is AEO?', slug: 'concepts/what-is-aeo' },
						{ label: 'GEO vs SEO', slug: 'concepts/geo-vs-seo' },
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
	],
});
