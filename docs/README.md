# Documentation Directory

This directory contains technical documentation for the Org Archivist project, including architecture decisions, troubleshooting guides, and lessons learned during development.

## Contents

### Technical Issues & Solutions

- **[bm25-okapi-zero-idf-issue.md](bm25-okapi-zero-idf-issue.md)** - Documents the BM25Okapi IDF calculation bug discovered during keyword search implementation and the solution (switching to BM25L)

## Purpose

This documentation serves multiple purposes:

1. **Knowledge Preservation** - Capture important technical decisions and their rationale
2. **Troubleshooting** - Document issues and solutions for future reference
3. **Onboarding** - Help new team members understand why certain choices were made
4. **Maintenance** - Provide context for library upgrades and refactoring
5. **Learning** - Share lessons learned during development

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
