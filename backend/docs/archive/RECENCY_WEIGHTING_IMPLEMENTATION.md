# Recency Weighting Implementation

## Overview

Implemented recency weighting for the retrieval engine to boost recent documents in search results. This feature helps ensure that more recent grant proposals, reports, and other documents are prioritized when relevance scores are similar.

## Implementation Details

### Age-Based Multipliers

Documents are assigned multipliers based on their age:

| Document Age | Multiplier | Effect |
|--------------|-----------|--------|
| Current year | 1.0x | No penalty |
| 1 year old | 0.95x | 5% reduction |
| 2 years old | 0.90x | 10% reduction |
| 3+ years old | 0.85x | 15% reduction |
| Missing year | 0.85x | Assumed old |

### Scoring Formula

The recency-adjusted score uses an interpolation formula:

```python
adjusted_score = original_score * (1 + recency_weight * (age_multiplier - 1))
```

Where:
- `original_score`: Hybrid score from vector + keyword search
- `recency_weight`: Configuration parameter (0-1)
  - 0.0 = no recency adjustment
  - 1.0 = full recency adjustment
- `age_multiplier`: Age-based multiplier (0.85 to 1.0)

### Examples

#### Example 1: Full Recency Weighting (weight=1.0)

```
Document: Grant Proposal from 2020
Original score: 0.92
Age: 5 years → multiplier: 0.85

Adjusted score = 0.92 * (1 + 1.0 * (0.85 - 1))
               = 0.92 * 0.85
               = 0.782
```

#### Example 2: Partial Recency Weighting (weight=0.7, default)

```
Document: Annual Report from 2020
Original score: 0.88
Age: 5 years → multiplier: 0.85

Adjusted score = 0.88 * (1 + 0.7 * (0.85 - 1))
               = 0.88 * (1 + 0.7 * (-0.15))
               = 0.88 * 0.895
               = 0.7876
```

#### Example 3: Current Year Document

```
Document: Budget Narrative from 2025
Original score: 0.85
Age: 0 years → multiplier: 1.0

Adjusted score = 0.85 * (1 + 0.7 * (1.0 - 1))
               = 0.85 * 1.0
               = 0.85  (unchanged)
```

## Configuration

The recency weighting behavior is controlled by the `recency_weight` parameter in `RetrievalConfig`:

```python
config = RetrievalConfig(
    vector_weight=0.7,
    keyword_weight=0.3,
    recency_weight=0.7,  # Default: 0.7 (moderate recency boost)
    max_per_doc=3,
    enable_reranking=False,
    expand_query=True
)
```

### Weight Guidelines

| Weight | Use Case | Effect |
|--------|----------|--------|
| 0.0 | Ignore document age | No recency adjustment |
| 0.3 | Slight recency preference | Minimal age penalty |
| 0.5 | Balanced | Moderate age consideration |
| 0.7 | Moderate recency preference | Notable age penalty (default) |
| 1.0 | Strong recency preference | Maximum age penalty |

## Features

### Core Implementation

✅ **Age Calculation**: Compares document year to current year
✅ **Multiplier Application**: Applies age-based score adjustments
✅ **Re-sorting**: Sorts results by adjusted scores
✅ **Metadata Preservation**: Stores original score and multiplier for analysis

### Edge Case Handling

✅ **Missing Year**: Defaults to 0.85x multiplier (assumes old)
✅ **Future Dates**: Uses 1.0x multiplier (no penalty)
✅ **Zero Weight**: Skips processing for efficiency
✅ **Empty Results**: Returns empty list unchanged

### Metadata Tracking

The implementation adds tracking metadata to results:

```python
{
    "_original_score": 0.92,        # Score before recency adjustment
    "_age_multiplier": 0.85,        # Applied multiplier
    "_recency_adjusted": True,      # Flag indicating adjustment
}
```

## Testing

### Test Coverage

Comprehensive test suite (`test_recency_weighting.py`) with 6 test scenarios:

1. **Basic Recency Weighting**: Verifies multipliers for different ages
2. **Weight Parameter Effect**: Tests weight range from 0.0 to 1.0
3. **Re-sorting**: Confirms results are re-ordered by adjusted scores
4. **Missing Year**: Handles documents without year metadata
5. **Edge Cases**: Empty results, zero weight, future dates
6. **Real-World Scenario**: Mixed documents with realistic scores

### Test Results

All tests passing:
- ✅ Age multipliers calculated correctly
- ✅ Weight parameter controls effect strength
- ✅ Results properly re-sorted
- ✅ Missing year defaults to 0.85x
- ✅ Edge cases handled gracefully
- ✅ Real-world scenario: current year doc boosted from 3rd to 1st

### Example Test Output

```
Real-World Scenario (weight=0.7):

Original ranking (by relevance score):
  1. 2020 Grant Proposal            score=0.9200  year=2020
  2. 2023 Annual Report             score=0.8800  year=2023
  3. 2025 Budget Narrative          score=0.8500  year=2025
  4. 2021 Letter of Intent          score=0.9000  year=2021
  5. 2024 Impact Report             score=0.8700  year=2024

After recency weighting (weight=0.7):
  1. 2025 Budget Narrative          score=0.8500 (was 0.8500)  age=0yr
  2. 2024 Impact Report             score=0.8396 (was 0.8700)  age=1yr
  3. 2020 Grant Proposal            score=0.8234 (was 0.9200)  age=5yr
  4. 2023 Annual Report             score=0.8184 (was 0.8800)  age=2yr
  5. 2021 Letter of Intent          score=0.8055 (was 0.9000)  age=4yr
```

**Insight**: The 2025 document moved from 3rd to 1st place, while the 2020 document (highest original score) dropped to 3rd place due to age penalty.

## Usage

### In Retrieval Pipeline

The recency weighting is automatically applied in the `retrieve()` method:

```python
engine = RetrievalEngine(
    vector_store=vector_store,
    embedding_model=embedding_model,
    config=RetrievalConfig(recency_weight=0.7)
)

results = await engine.retrieve(
    query="grant proposals for education programs",
    top_k=5,
    filters=None,
    recency_weight=None  # Use config default (0.7)
)
```

### Override Recency Weight Per Query

You can override the recency weight for individual queries:

```python
# Disable recency weighting for this query
results = await engine.retrieve(
    query="historical funding patterns",
    top_k=10,
    recency_weight=0.0  # Ignore document age
)

# Strong recency preference for this query
results = await engine.retrieve(
    query="latest program outcomes",
    top_k=5,
    recency_weight=1.0  # Maximum recency boost
)
```

## Integration with Hybrid Search

Recency weighting is applied **after** hybrid scoring (vector + keyword) and **before** diversification:

```
Pipeline Order:
1. Vector search (semantic similarity)
2. Keyword search (BM25)
3. Hybrid combination (weighted scores)
4. ✅ Recency weighting (age-based adjustment)
5. Diversification (limit chunks per doc)
6. Re-ranking (optional)
7. Return top-k results
```

This ensures that:
- Recency adjusts the combined relevance score
- Recent documents can overtake older documents with higher relevance
- Diversification still prevents single-document dominance
- Final ranking reflects both relevance and recency

## Performance Considerations

### Computational Complexity

- **Time**: O(n) where n = number of results
- **Space**: O(n) for adjusted results

### Optimization

- Zero weight check skips processing entirely
- Single pass through results (no additional iterations)
- Metadata extraction is efficient (dict lookup)
- Sorting is only done once after adjustment

### Memory

- Adds 3 metadata fields per result (~24 bytes)
- No caching or index building required
- Results are re-created, not mutated in-place

## Future Enhancements

Potential improvements for future iterations:

1. **Custom Multiplier Curves**: Allow configurable age-to-multiplier mapping
2. **Domain-Specific Decay**: Different decay rates for different document types
3. **Exponential Decay**: Smooth exponential decay instead of step function
4. **Date-Based Weighting**: Use specific dates instead of just years
5. **Recency Boost Logging**: Detailed analytics on recency impact
6. **A/B Testing**: Compare different recency strategies

## Related Files

- **Implementation**: `backend/app/services/retrieval_engine.py:598-700`
- **Tests**: `backend/test_recency_weighting.py`
- **Configuration**: `backend/app/services/retrieval_engine.py:45-53` (RetrievalConfig)
- **Documentation**: `backend/HYBRID_SCORING_IMPLEMENTATION.md` (hybrid search)

## References

- Task: 34388d1a-50f5-4267-95cc-e8488b87d845
- Feature: Retrieval Engine
- Related: Hybrid Search, Vector Search, BM25 Keyword Search
