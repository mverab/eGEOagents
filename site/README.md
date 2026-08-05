# E-GEO Documentation Site

Astro Starlight site for [egeoagents.com](https://egeoagents.com), deployable to Cloudflare Pages.

## Commands

| Command | Action |
|---|---|
| `npm install` | Install dependencies |
| `npm run dev` | Local dev server at `localhost:4321` |
| `npm run build` | Build production site to `./dist/` |
| `./verify.sh` | Post-build checks (routes, llms.txt, JSON-LD, sitemap) |

Content lives in `src/content/docs/`. `public/llms.txt` and `public/llms-full.txt` follow the [llmstxt.org](https://llmstxt.org/) spec.
