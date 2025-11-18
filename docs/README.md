# Documentation Directory

This directory contains technical documentation for the Org Archivist project, including architecture decisions, troubleshooting guides, and lessons learned during development.

## Contents

### Essential Documentation for Maintainability

This documentation is actively maintained and essential for understanding, maintaining, and extending the Org Archivist application.

### Getting Started & Deployment

- **[docker-deployment.md](docker-deployment.md)** - Docker deployment guide for production and development environments
- **[user-management.md](user-management.md)** - User account creation and management guide
- **[auto-migrations.md](auto-migrations.md)** - Database migration setup and workflow
- **[database-schema.md](database-schema.md)** - Complete database schema documentation

### Frontend Development (Nuxt 4)

**Start here:** **[frontend-quick-start.md](frontend-quick-start.md)** - Quick start guide for frontend developers

**Essential documentation:**
- **[nuxt4-setup.md](nuxt4-setup.md)** - Nuxt 4 framework setup and configuration
- **[nuxt-ui-component-guide.md](nuxt-ui-component-guide.md)** - Nuxt UI component patterns, type-safe usage, and common pitfalls
- **[nuxt4-implementation-risks.md](nuxt4-implementation-risks.md)** - Important risks and considerations for Nuxt 4 development
- **[backend-api-guide.md](backend-api-guide.md)** - Complete backend API reference for frontend integration

See also: **[/context/frontend-requirements.md](../context/frontend-requirements.md)** for detailed frontend specifications.

### Backend Architecture & Configuration

- **[retrieval-engine-recency-weighting.md](retrieval-engine-recency-weighting.md)** - Recency weighting implementation for the retrieval engine
- **[embedding-configuration.md](embedding-configuration.md)** - Embedding model configuration and provider setup
- **[rate-limiting.md](rate-limiting.md)** - API rate limiting configuration
- **[log-management.md](log-management.md)** - Logging configuration and best practices
- **[security-improvements.md](security-improvements.md)** - Security hardening and best practices

## Documentation Organization

### Active Documentation (This Directory)
Essential, actively maintained documentation for:
- Production deployment and operations
- Frontend development (Nuxt 4)
- Backend architecture and configuration
- Database management

### Archived Documentation
Historical documentation from completed development phases is in **[archive/](archive/README.md)**:
- Development-specific guides (authentication strategy, Streamlit migration)
- Testing and validation reports
- Technical issue investigations
- Architecture decisions (now superseded)

### Project Context
Core project specifications in **[/context/](../context/)**:
- **[project-context.md](../context/project-context.md)** - Problem statement and use cases
- **[requirements.md](../context/requirements.md)** - Functional and non-functional requirements
- **[architecture.md](../context/architecture.md)** - System architecture and design
- **[frontend-requirements.md](../context/frontend-requirements.md)** - Frontend specifications

## Purpose

This documentation serves:

1. **Onboarding** - Get new team members productive quickly
2. **Frontend Development** - Enable Nuxt 4 frontend implementation
3. **Operations** - Deploy and maintain the application in production
4. **Architecture** - Understand system design and technical decisions
5. **Troubleshooting** - Resolve issues using established patterns

## Documentation Standards

When adding new documents to this directory:

1. **Use descriptive filenames** - kebab-case with clear topic indication
2. **Include dates** - Document when the issue occurred or decision was made
3. **Provide context** - Explain the problem, investigation, and solution
4. **Add examples** - Include code snippets and test cases where relevant
5. **Link to code** - Reference specific files and line numbers when applicable
6. **Update this README** - Add your document to the Contents section above

## Document Types

### Issue Reports
Document unexpected behavior, bugs, or limitations discovered during development:
- Problem description
- Investigation process
- Root cause analysis
- Solution implementation
- Testing validation
- Recommendations

### Architecture Decisions
Record significant architectural choices:
- Context and requirements
- Options considered
- Decision made and rationale
- Consequences and trade-offs
- Implementation notes

### Lessons Learned
Capture insights from development experience:
- What worked well
- What didn't work
- What we'd do differently
- Tips for future development

## Related Documentation

- **[/context/architecture.md](../context/architecture.md)** - System architecture and design
- **[/context/requirements.md](../context/requirements.md)** - Functional and non-functional requirements
- **[/DEVELOPMENT.md](../DEVELOPMENT.md)** - Development environment setup
- **[/README.md](../README.md)** - Project overview and getting started
- **[/CLAUDE.md](../CLAUDE.md)** - Instructions for Claude Code

## Contributing

When you encounter a significant issue or make an important technical decision:

1. Create a new markdown document in this directory
2. Follow the documentation standards above
3. Update this README with a link to your document
4. Commit with a descriptive message: `docs: add documentation for [topic]`

## Questions?

If you have questions about existing documentation or need clarification on any technical decisions, please:

1. Review the relevant document first
2. Check the referenced code files
3. Consult with the team
4. Update the documentation if you discover gaps or errors
