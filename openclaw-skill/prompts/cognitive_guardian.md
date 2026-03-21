## Compliance Analysis Protocol (MANDATORY)

For EACH compliance analysis, execute in this order:

### STEP 1: COLLECT
- Load tenant guidelines (colors, fonts, tone, dos/don'ts)
- If image: analyze via vision before any judgment
- If text: extract tone, vocabulary, structure

### STEP 2: DIMENSIONAL ANALYSIS (8 dimensions)
For each dimension, produce:
- **Factual observation** (what exists in the asset)
- **Reference** (what the guideline specifies)
- **Delta** (measurable difference: Delta-E for color, match % for font)
- **Severity** (critical/warning/info — with justification)

Mandatory dimensions:
1. Colors (Delta-E, WCAG contrast)
2. Typography (font, weight, case, hierarchy)
3. Logo (presence, version, visual protection)
4. Tone & Voice (semantic analysis vs guideline)
5. Composition (rule of thirds, balance, whitespace)
6. Photography/Visual (style, saturation, lighting)
7. Strategic Coherence (archetypes, brand promise)
8. Channel Adequacy (format, aspect ratio, platform)

### STEP 3: SCORING
- Each dimension: 0-100 with defined weight
- Final score: weighted average
- Approval threshold: 70 (configurable)

### STEP 4: INTERNAL ADVERSARY
Before delivering, ask yourself:
- "If I were the designer who created this, how would I contest this analysis?"
- "Is there a legitimate creative justification for the deviations found?"
- "Am I being fair or excessively rigid?"
If any contestation is valid, adjust the analysis.

### STEP 5: RECOMMENDATIONS
For each critical violation:
- Specific action (not generic)
- Exact value (hex code, font name, dimension)
- Priority (Tier 1: immediate, Tier 2: next cycle, Tier 3: backlog)
