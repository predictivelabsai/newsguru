# NewsGuru Significance Scoring Rules

## Philosophy

Significance is **objective** — it measures how much an event affects humanity as a whole.
This is different from importance, which is subjective and personal.

The goal is to cut through sensationalist noise and surface only what truly matters.
If nothing significant happens, the feed should be short by design.

## Scoring Factors (7 dimensions)

Each factor is scored 0-10:

### 1. Scale (weight: 4/20)
How broadly does this event affect people?
- 0-2: Affects a single person, family, or small group
- 3-4: Affects a local community or single organization
- 5-6: Affects a region, industry, or country
- 7-8: Affects multiple countries or a large population
- 9-10: Affects the entire world or a significant portion of humanity

### 2. Impact (weight: 4/20)
How strong is the immediate, tangible effect?
- 0-2: Minimal practical consequence
- 3-4: Noticeable effect on daily life for some people
- 5-6: Significant disruption or change to systems/institutions
- 7-8: Major disruption affecting millions
- 9-10: Catastrophic or transformative immediate effect

### 3. Novelty (weight: 3/20)
How unique and unexpected is this event?
- 0-2: Routine, expected, or recurring event
- 3-4: Somewhat unusual but within normal variation
- 5-6: Notably unusual or surprising development
- 7-8: Highly unexpected, breaks established patterns
- 9-10: Unprecedented, first-of-its-kind event

### 4. Potential (weight: 3/20)
How likely is this to shape the future?
- 0-2: No lasting consequences expected
- 3-4: Minor long-term implications
- 5-6: Could influence policy, markets, or social norms
- 7-8: Likely to trigger cascading changes
- 9-10: Will fundamentally alter the trajectory of society

### 5. Legacy (weight: 3/20)
How likely is this to be remembered as a turning point?
- 0-2: Will be forgotten within days
- 3-4: May be referenced occasionally
- 5-6: Likely to appear in year-end retrospectives
- 7-8: Will be studied in textbooks
- 9-10: Will define an era

### 6. Positivity (weight: 1/20)
How positive is this event?
- 0-2: Strongly negative (disasters, wars, crimes)
- 3-4: Mostly negative
- 5: Neutral or mixed
- 6-7: Mostly positive
- 8-10: Strongly positive (breakthroughs, peace, progress)

*This factor has intentionally low weight (1/20). It exists solely to counteract
the negativity bias in news coverage and bring the ratio closer to 50:50 in the
high-significance range.*

### 7. Credibility (weight: 2/20)
How trustworthy and well-sourced is this report?
- 0-2: Unverified rumor, single anonymous source
- 3-4: Single source, limited corroboration
- 5-6: Reported by established outlet, some verification
- 7-8: Confirmed by multiple credible sources
- 9-10: Official statements, verified data, scientific consensus

## Final Score Calculation

```
significance = (
    scale * 4 +
    impact * 4 +
    novelty * 3 +
    potential * 3 +
    legacy * 3 +
    positivity * 1 +
    credibility * 2
) / 20
```

Normalized to 0-10 scale.

## Expected Distribution

- **0-2**: Sports results, entertainment gossip, minor local news (~60% of articles)
- **3-4**: Regional politics, business earnings, routine policy changes (~25%)
- **5-6**: Significant national events, major policy shifts, notable scientific findings (~10%)
- **7-8**: Major world events, landmark decisions, breakthrough discoveries (~4%)
- **9-10**: Once-in-a-decade events, paradigm shifts (~1%)

On a typical day, only 5-15 articles should score above 5.

## Examples

| Event | Scale | Impact | Novelty | Potential | Legacy | Positivity | Credibility | Score |
|-------|-------|--------|---------|-----------|--------|------------|-------------|-------|
| Local sports result | 1 | 1 | 1 | 0 | 0 | 5 | 7 | 1.4 |
| Celebrity gossip | 2 | 1 | 2 | 0 | 0 | 5 | 3 | 1.4 |
| New trade agreement | 6 | 5 | 4 | 6 | 5 | 7 | 8 | 5.6 |
| Major earthquake | 7 | 9 | 5 | 4 | 5 | 0 | 9 | 6.1 |
| AI breakthrough | 8 | 6 | 8 | 9 | 8 | 8 | 7 | 7.6 |
| Start of major war | 9 | 10 | 7 | 9 | 9 | 0 | 8 | 8.2 |
