# Design: Open Source Launch Strategy

## Context

E-GEO es una herramienta de GEO (Generative Engine Optimization) que optimiza contenido para AI search engines. Irónicamente, el propio repo debe aplicar los principios E-GEO para posicionarse.

**Stakeholders:**
- Desarrolladores buscando herramientas GEO
- Marketers técnicos
- SaaS founders
- AI/ML community

## Goals / Non-Goals

### Goals
- Alcanzar GitHub Trending en 1-2 semanas post-lanzamiento
- Posicionar en top 5 para búsquedas "GEO tools", "Generative Engine Optimization"
- Conseguir 500+ stars en primer mes
- Establecer autoridad citando research E-GEO

### Non-Goals
- Monetización inmediata (Gumroad viene después)
- Features nuevos (solo polish de documentación)
- Soporte multilenguaje (solo inglés inicial)

## Decisions

### 1. README Structure (GEO-Optimized)

**Decision:** Estructura de README basada en los 10 GEO features + GitHub best practices.

```
# E-GEO - {tagline con keyword principal}

> {One-liner con user intent + differentiation}

{Badges: stars, license, version, last commit}

## ✨ What is E-GEO? (User Intent Alignment)
{Problema + solución en 2-3 oraciones}

## 🚀 Quick Start (Scannability + Urgency)
{3 pasos máximo, copy-paste ready}

## 📊 Results (Social Proof + Authority)
{Métricas, before/after, research citations}

## 🎯 Features (USPs + Competitive Diff)
{Tabla comparativa vs alternativas}

## 📚 Documentation (Scannability)
{Links a docs/}

## 🤝 Contributing (Community signals)
{Link a CONTRIBUTING.md}

## 📜 License + Credits (Authority)
```

**Alternatives considered:**
- README minimalista: Rechazado, no aprovecha GEO
- README extenso: Rechazado, pierde scannability

### 2. GitHub Discoverability

**Decision:** Maximizar signals de GitHub's discovery algorithm.

| Element | Strategy |
|---------|----------|
| **Description** | "Zero-effort GEO: Optimize content for ChatGPT, Perplexity & AI search engines" |
| **Topics** | `geo`, `generative-engine-optimization`, `ai-seo`, `llm`, `claude`, `chatgpt`, `perplexity`, `content-optimization` |
| **About** | URL a landing page o docs |
| **Releases** | v1.0.0 con changelog detallado |

### 3. GitHub Trending Strategy

**Decision:** Optimizar para el algoritmo de Trending.

**Factores conocidos:**
1. **Velocity** (stars/hour en últimas 24-48h)
2. **Recency** (repos nuevos tienen boost)
3. **Engagement** (issues, forks, watchers)

**Tácticas:**
- Lanzar Martes/Miércoles 9am PT (máximo tráfico dev)
- Coordinar 20-30 early stars en primeras 2 horas
- Publicar en r/MachineLearning, HackerNews, Twitter
- Crear 2-3 issues "good first issue" para engagement

### 4. SEO/GEO Keywords

**Decision:** Keywords primarios y secundarios basados en intent.

| Type | Keywords |
|------|----------|
| **Primary** | GEO, Generative Engine Optimization |
| **Secondary** | AI SEO, LLM ranking, content optimization, ChatGPT ranking |
| **Long-tail** | optimize content for AI search, rank higher in ChatGPT, Perplexity SEO |
| **Technical** | Claude Code, MCP, schema markup, JSON-LD |

### 5. Social Proof Strategy

**Decision:** Construir proof sin fabricar (regla E-GEO crítica).

**Proof disponible:**
- "Based on E-GEO research paper (arXiv:2511.20867)" - citar donde sea relevante
- "Average +1.61 rank improvement" (del paper)
- "10 research-backed optimization features"
- GitHub stars counter (badge dinámico)

**AI GEN Banners (REQUIRED):**
- Badge en README: `🤖 AI-Assisted Development`
- Footer en outputs generados: "Generated with AI assistance"
- Transparencia sobre qué partes son AI-generated

**Proof a construir:**
- Screenshots de before/after reales
- Testimonials de early adopters (con permiso)
- Case studies en docs/

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Timing incorrecto de launch | Monitorear GitHub Trending patterns antes |
| Poco engagement inicial | Preparar lista de early adopters pre-launch |
| README muy largo | Mantener above-the-fold conciso, expandir abajo |
| Keywords saturados | Usar long-tail + diferenciación técnica |

## Migration Plan

1. **Pre-launch (1 semana)**
   - Finalizar README, CONTRIBUTING, templates
   - Preparar lista de early adopters
   - Crear assets (screenshots, diagrams)
   - Draft de posts para HN/Reddit/Twitter

2. **Launch day**
   - Push final a main
   - Crear Release v1.0.0
   - Coordinar early stars
   - Publicar en canales

3. **Post-launch (1-2 semanas)**
   - Monitorear Trending
   - Responder issues rápido
   - Iterar README basado en feedback

## Resolved Questions

1. **Landing page**: Solo GitHub por ahora (no externa)
2. **Citas del paper**: Citar E-GEO paper donde sea relevante, no solo en una sección
3. **AI GEN Banners**: MUST incluir banners indicando contenido generado/asistido por AI

## Open Questions

1. ¿Incluir demo video/GIF en README?
