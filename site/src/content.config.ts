import { defineCollection } from 'astro:content';
import type { Loader } from 'astro/loaders';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

// The free URL audit docs page ships only when the API is live
// (PUBLIC_AUDIT_ENABLED, set in .github/workflows/site.yml; see astro.config.mjs).
const auditEnabled = process.env.PUBLIC_AUDIT_ENABLED === 'true';
const AUDIT_DOCS_ID = 'docs/url-audit';

function docsWithoutAudit(): Loader {
	const inner = docsLoader();
	return {
		name: 'egeo-docs-loader',
		load: async (context) => {
			await inner.load(context);
			if (!auditEnabled) context.store.delete(AUDIT_DOCS_ID);
		},
	};
}

export const collections = {
	docs: defineCollection({ loader: docsWithoutAudit(), schema: docsSchema() }),
};
