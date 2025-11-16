# Backend Documentation Archive

## Purpose

This directory contains archived implementation documentation for completed backend features. These documents captured implementation details during development but are no longer actively maintained.

## Archived Implementation Docs

### Alembic Migration Setup
- **ALEMBIC_SETUP_COMPLETE.md** - Documentation of the migration from SQL init scripts to pure Alembic migrations (October 2025)
- See current migration docs: `/docs/auto-migrations.md`

### AI/ML Feature Implementations
- **CLAUDE_API_INTEGRATION.md** - Claude API integration implementation details
- **EMBEDDING_GENERATION_IMPLEMENTATION.md** - Document embedding generation implementation
- **HYBRID_SCORING_IMPLEMENTATION.md** - Hybrid search scoring (vector + keyword) implementation
- **RECENCY_WEIGHTING_IMPLEMENTATION.md** - Recency weighting for search results implementation
- See current docs: `/docs/retrieval-engine-recency-weighting.md` and `/docs/embedding-configuration.md`

### Testing Documentation
- **E2E_TEST_SUMMARY.md** - End-to-end testing implementation summary
- See current test docs: `/backend/tests/README.md`

## When to Reference

Reference these documents when:
- Investigating historical implementation decisions
- Understanding the evolution of features
- Debugging related issues
- Learning from past implementation patterns

## Active Backend Documentation

For current backend documentation, see:
- **[/backend/README.md](../../README.md)** - Backend overview and setup
- **[/backend/docs/](../)** - Active implementation guides
- **[/docs/backend-api-guide.md](../../../docs/backend-api-guide.md)** - API reference for frontend integration

Last Updated: 2025-11-16
