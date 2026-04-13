# EmoGift Furin -- UGC Realism Verification Checklist

> **Expert 2**: Skin & Face Realism Specialist
> **Expert 3**: Hand & Object Expert
> **Pipeline**: 6 shots, 30 seconds total, Kling 2.1 / Sora
> **Date**: 2026-04-13
> **Rule**: Every shot must meet its MINIMUM PASS SCORE or it is REJECTED.

---

## SCORING RUBRIC

Each criterion is scored **0** (fail) or **1** (pass). No partial credit.

| Shot | Category | Total Criteria | Minimum Pass Score | Pass % |
|------|----------|----------------|--------------------|--------|
| 1    | Hands + Object | 14 | 11 | 79% |
| 2    | Hands + Object | 16 | 13 | 81% |
| 3    | Face + Skin | 18 | 15 | 83% |
| 4    | Face + Skin + Hands + Object | 38 | 33 | 87% |
| 5    | Face + Skin + Hands + Object | 20 | 17 | 85% |
| 6    | Object only (no person) | 8 | 6 | 75% |

Shot 4 has the highest threshold because it is the emotional anchor of the entire video. A single uncanny-valley tell will destroy viewer immersion.

---

## SHOT 1 -- Gift Wrapping (0-5 s)

### Expert 2 -- Skin (Hands Only, No Face)

_Face criteria: N/A (hands-only POV shot)._

Skin on hands must not look synthetic:
- [ ] **S1-SK1**: Slight color variation across fingers and palm (knuckles slightly redder than fingertips)
- [ ] **S1-SK2**: Visible skin texture grain on finger pads (not smooth rubber)
- [ ] **S1-SK3**: No airbrushed glow or uniform skin tone across both hands

### Expert 3 -- Hands & Object

**Young Hands (age 25-30):**

- [ ] **S1-H1**: Five fingers per hand, correct proportions (middle finger longest, pinky shortest)
- [ ] **S1-H2**: Three visible knuckle creases per finger when bent
- [ ] **S1-H3**: Nail beds show natural pink-to-white gradient at free edge
- [ ] **S1-H4**: Chipped dark-red nail polish -- chips must be irregular, not symmetrical across nails
- [ ] **S1-H5**: Cuticles slightly ragged, visible on at least 3 nails
- [ ] **S1-H6**: Thin silver ring on right index finger -- ring must show minor scratches or dullness, not mirror-perfect
- [ ] **S1-H7**: Some veins faintly visible on dorsal hand (subtle, age-appropriate -- not prominent)
- [ ] **S1-H8**: Slight natural tremor in the wrapping hand (phone held in one hand creates instability)
- [ ] **S1-H9**: Fingers indent the washi paper where they press -- no hovering or phasing through

**Object Interaction:**

- [ ] **S1-O1**: Washi paper crinkles and deforms naturally under finger pressure
- [ ] **S1-O2**: Paper has memory -- creases stay where fingers fold them
- [ ] **S1-O3**: Furin glass has irregular reflections (not uniform specular highlight)
- [ ] **S1-O4**: Tape adheres to paper realistically (slight stretch, visible adhesive contact)
- [ ] **S1-O5**: No object clipping -- fingers do not pass through paper, tape, or furin

**REJECTION TRIGGERS (any one = instant reject):**
- Wrong finger count (extra or missing fingers)
- Nails perfectly uniform in shape, length, or polish coverage
- Fingers look rubbery, boneless, or taper unnaturally
- Paper does not deform when touched
- Skin has a waxy or plastic sheen

**Total criteria: 14 | Minimum pass: 11**

### Re-prompt Strategy (Shot 1 failures)

If hands look too smooth: add `"visible skin texture on fingers, tiny wrinkles on knuckles, imperfect cuticles"`
If nail polish too perfect: add `"chipped nail polish with uneven wear, some nails more chipped than others, not freshly painted"`
If paper interaction fails: add `"paper crinkles and bends where fingers press, physical contact deformation visible"`

---

## SHOT 2 -- Mother Unwraps Gift (5-10 s)

### Expert 2 -- Skin (Hands Only, No Face)

_Face criteria: N/A (hands-only shot from daughter's POV)._

- [ ] **S2-SK1**: Skin on hands appears dry, slightly rough -- not moisturized or dewy
- [ ] **S2-SK2**: Visible skin thinning on back of hand (slightly translucent quality near veins)
- [ ] **S2-SK3**: Knuckle skin shows deepened creases consistent with age 55+
- [ ] **S2-SK4**: Slight redness or irritation around cuticle edges (real hands, not pampered)

### Expert 3 -- Hands & Object

**Mature Hands (age 55-60):**

- [ ] **S2-H1**: Five fingers per hand, correct proportions
- [ ] **S2-H2**: Prominent dorsal hand veins -- at least 3-4 visible, branching naturally
- [ ] **S2-H3**: Visible tendons on back of hand when fingers grip or extend
- [ ] **S2-H4**: Two to three brown age spots (liver spots) near knuckles or back of hand -- irregular shapes, not circles
- [ ] **S2-H5**: Short unpainted nails with slight vertical ridges
- [ ] **S2-H6**: Nail beds slightly yellowed or uneven compared to a younger person
- [ ] **S2-H7**: Gold wedding band on left ring finger -- slightly worn, not shiny-new, slight indentation on finger skin beneath it
- [ ] **S2-H8**: Wedding band slightly loose (real wedding bands on older women often are after weight fluctuation)
- [ ] **S2-H9**: Finger joint proportions show slight thickening at knuckles (early age-related joint changes)

**Object Interaction:**

- [ ] **S2-O1**: Fingers indent washi paper as they unwrap it
- [ ] **S2-O2**: Paper tears naturally where pulled (not a clean geometric tear)
- [ ] **S2-O3**: Furin glass shows inconsistent environmental reflections (ceiling light, tablecloth color bleed)

**REJECTION TRIGGERS (any one = instant reject):**
- Hands look younger than 45 (no veins, no age spots, smooth knuckles)
- Fingers appear rubbery, boneless, or have wrong number of joints
- Wedding band looks like a 3D render (mirror-perfect reflections, no wear)
- No visible veins on the back of either hand
- Nails are manicured, long, or polished
- Skin has uniform tone without any age spots or discoloration

**Total criteria: 16 | Minimum pass: 13**

### Re-prompt Strategy (Shot 2 failures)

If hands look too young: add `"elderly woman's hands showing prominent blue-green veins, brown age spots, thinning dry skin, visible tendons, knuckle wrinkles -- hands that have worked for 55 years"`
If wedding band too perfect: add `"old gold wedding band, slightly dull, micro-scratches, worn smooth on the edges from decades of wear, skin slightly indented underneath"`
If veins missing: add `"dorsal hand veins clearly visible as raised blue-green lines under thin aging skin"`

---

## SHOT 3 -- Daughter Records Video Message (10-15 s)

### Expert 2 -- Skin & Face Realism

**Skin (Young Woman, 25):**

- [ ] **S3-SK1**: Visible pores on nose and forehead (T-zone), especially noticeable due to harsh overhead sunlight
- [ ] **S3-SK2**: Slightly uneven skin tone -- cheeks slightly different shade from forehead
- [ ] **S3-SK3**: Small blemish on chin (pimple or healed spot) -- not symmetrically placed
- [ ] **S3-SK4**: No foundation, no concealer -- raw skin with natural minor redness around nostrils
- [ ] **S3-SK5**: Front-camera characteristic: slightly softer skin texture than rear camera would produce, but pores still visible
- [ ] **S3-SK6**: Harsh midday sun creates visible texture on skin surface (micro-bumps, peach fuzz catch light)

**Facial Structure & Asymmetry:**

- [ ] **S3-FA1**: Eyes are not perfectly symmetrical -- one eye very slightly narrower or positioned marginally different
- [ ] **S3-FA2**: Eyebrows are natural (not shaped), slightly different in arch or thickness
- [ ] **S3-FA3**: Nostrils are not perfectly symmetrical
- [ ] **S3-FA4**: Smile is asymmetric -- one side lifts slightly higher than the other
- [ ] **S3-FA5**: Front-camera barrel distortion: nose appears very slightly wider, chin very slightly narrower than in reality

**Expression Authenticity:**

- [ ] **S3-EX1**: Nervous smile transitions -- not a held static smile, muscles fluctuate
- [ ] **S3-EX2**: Micro-expressions between words: lip press, eye dart, slight brow furrow
- [ ] **S3-EX3**: Lips slightly trembling when she pauses between phrases
- [ ] **S3-EX4**: No ring light catchlights in eyes -- natural diffuse light reflections only
- [ ] **S3-EX5**: Blink rate appears natural (not too few, not too many -- roughly 15-20 blinks per minute)

**Hair:**

- [ ] **S3-HR1**: Messy, partly pulled back, loose strands across forehead -- flyaways visible
- [ ] **S3-HR2**: Slight frizz from humidity (individual strands catching light)

**REJECTION TRIGGERS (any one = instant reject):**
- Skin is uniformly smooth with no visible pores anywhere
- Perfectly symmetrical face or features
- Ring light reflections visible in both eyes (twin circular catchlights)
- Beauty-filter look: softened jawline, enlarged eyes, narrowed nose
- Static held expression that doesn't shift or fluctuate
- Teeth are perfectly straight, perfectly white, identical in size
- Hair looks styled or salon-fresh

**Total criteria: 18 | Minimum pass: 15**

### Re-prompt Strategy (Shot 3 failures)

If skin too smooth: add `"visible pores on nose and forehead, slight skin texture, no beauty filter, no skin smoothing, raw unedited front camera quality"`
If too symmetrical: add `"naturally asymmetric face, one eye slightly different from the other, imperfect smile, human facial asymmetry"`
If expression looks performed: add `"genuine nervousness, micro-expression changes, lip tremor, not an actress, not confident, shy and emotional"`
If ring light reflections appear: add `"no ring light, no studio light, harsh overhead sun only, diffuse natural light reflections in eyes"`

---

## SHOT 4 -- Mother Watches Video, Emotion Transition (15-20 s) -- CRITICAL SHOT

This is the make-or-break shot. Every criterion matters. Generate 20-25 variations minimum. Reject aggressively.

### Expert 2 -- Skin & Face Realism (15+ Specific Markers)

**Skin Texture (Mature Woman, 55-60):**

- [ ] **S4-SK1**: Crow's feet visible at rest, DEEPENING visibly when emotion hits and eyes squint with tears
- [ ] **S4-SK2**: Nasolabial folds (nose-to-mouth lines) -- deep, casting micro-shadows, more pronounced on one side
- [ ] **S4-SK3**: Forehead lines -- horizontal, at least 2-3 distinct creases, visible even at rest
- [ ] **S4-SK4**: Neck skin texture: slight crepiness, horizontal neck lines, skin not taut
- [ ] **S4-SK5**: Ear lobes visible -- slightly elongated (as happens with age), one potentially with a piercing indent from years of earring wear
- [ ] **S4-SK6**: Skin around mouth shows fine vertical lip lines (smoker's lines or age lines)
- [ ] **S4-SK7**: Under-eye area: puffy, slight purple-gray discoloration, thin skin showing blood vessels faintly
- [ ] **S4-SK8**: No makeup whatsoever -- no foundation, no mascara, no lip color
- [ ] **S4-SK9**: Slight redness on nose tip and around nostrils (intensifying when crying begins)
- [ ] **S4-SK10**: Dry lips with slight chapping, not glossy or moisturized-looking

**Facial Structure & Asymmetry:**

- [ ] **S4-FA1**: Eyebrows are asymmetric -- different arch, one slightly higher than the other
- [ ] **S4-FA2**: One eye appears very slightly smaller or more hooded than the other
- [ ] **S4-FA3**: Small dark mole on left cheek near jawline -- irregular edge, not a perfect circle, slightly raised
- [ ] **S4-FA4**: Gray roots showing at hairline (2-3 cm of gray growth into dark brown dyed hair) -- not evenly distributed
- [ ] **S4-FA5**: Jawline is not sharp -- slight jowling or softening on both sides, one side slightly more than the other
- [ ] **S4-FA6**: Teeth (if visible when mouth opens): not perfectly aligned, slight yellowing, possibly one tooth slightly overlapping another

**Crying Realism (The Critical Sequence):**

- [ ] **S4-CR1**: Emotion is INVOLUNTARY -- starts from neutral, builds gradually, she does NOT start the shot already crying
- [ ] **S4-CR2**: Recognition phase: eyebrows rise, eyes widen slightly, mouth opens a fraction -- a 0.5-1 second beat of surprise
- [ ] **S4-CR3**: Chin dimpling: the mentalis muscle contracts creating "orange peel" texture on the chin as she holds back a sob
- [ ] **S4-CR4**: Lip compression: lower lip presses against upper lip, then trembles as control breaks
- [ ] **S4-CR5**: Tear track path: a single tear forms in the INNER CORNER of the right eye, travels down along the nose-cheek crease, not straight down the cheek -- tears follow facial topology
- [ ] **S4-CR6**: Tears do NOT fall symmetrically -- one eye tears before the other (right eye first per the prompt)
- [ ] **S4-CR7**: Nose tip reddens as crying intensifies (blood flow increases to nasal area during emotional crying)
- [ ] **S4-CR8**: Eyes become glassy/wet BEFORE the tear falls -- moisture buildup visible on the lower eyelid
- [ ] **S4-CR9**: Brow contracts medially (inner eyebrows pull together and upward) -- the "grief brow" or Duchenne display
- [ ] **S4-CR10**: Nostril flare -- slight nostril widening when she takes a shaky breath between sobs
- [ ] **S4-CR11**: Jaw clench visible -- masseter muscle tightens as she tries to control the emotion

**Phone Screen Under-lighting Effect:**

- [ ] **S4-LT1**: Phone screen casts a cool-blue glow on the underside of her chin, nose, and cheeks
- [ ] **S4-LT2**: The under-lighting from the phone creates unflattering shadows that go upward (opposite of natural overhead light) -- this is key to realism

### Expert 3 -- Hands & Object (Shot 4)

- [ ] **S4-H1**: Both hands grip the phone -- consistent with Shot 2 hand aging (veins, spots, dry skin)
- [ ] **S4-H2**: Knuckles whitening from grip intensity as emotion rises
- [ ] **S4-H3**: Veins on hand become more prominent with tightened grip
- [ ] **S4-H4**: Wedding band visible, consistent with Shot 2 (same worn gold band)
- [ ] **S4-H5**: Fingers wrapped around phone edges naturally -- no phasing, no extra joints
- [ ] **S4-H6**: Phone is held slightly tilted, not perfectly perpendicular to her face (natural grip)

**REJECTION TRIGGERS (any one = instant reject):**
- Skin is smooth or poreless anywhere on the face
- Perfectly symmetrical crying (both eyes tear simultaneously and identically)
- "Movie crying" -- photogenic tears rolling down flawless cheeks
- Missing mole on left cheek near jawline
- No gray roots visible at hairline
- Chin is smooth during crying (no mentalis contraction / dimpling)
- Teeth look perfect (straight, white, uniform)
- Tear track goes straight down instead of following facial contours
- Ring light or studio catchlights in eyes
- Hands look younger than the face
- Emotion starts immediately (no neutral-to-crying transition)
- Skin has any "glow" or "luminosity" that suggests a filter
- Neck skin is smooth and taut (contradicts age)
- Under-eye area is smooth and un-puffy

**Total criteria: 38 | Minimum pass: 33**

### Re-prompt Strategy (Shot 4 failures)

If crying looks performed: add `"involuntary emotional response, NOT an actress, emotion catches her off guard, she tries to hold it back but fails, chin trembles, jaw clenches, she fights the tears before they come"`
If skin too smooth: add `"55-year-old woman with no makeup, deep wrinkles around eyes and mouth, nasolabial folds casting shadows, forehead creases, neck skin showing age, puffy under-eyes with slight discoloration, dry chapped lips"`
If tears unrealistic: add `"single tear forming slowly in inner corner of right eye, rolling down along the nose-cheek crease following facial contour, eyes become glassy and wet before the tear falls, asymmetric crying"`
If gray roots missing: add `"dark brown dyed hair with clearly visible gray/white roots growing out 2-3cm at the hairline and part line"`
If chin dimpling absent: add `"chin muscles contracting creating dimpled orange-peel texture as she suppresses sobs, mentalis muscle visible"`
If hands inconsistent: add `"same mature hands from Shot 2: prominent veins, age spots, worn gold wedding band, dry skin, short nails"`
If under-lighting missing: add `"phone screen casting cool blue-white glow upward onto her chin and under-nose, creating unflattering upward shadows on her face"`

---

## SHOT 5 -- Voyeuristic Medium Shot, Mother Crying (20-25 s)

### Expert 2 -- Skin & Face Realism

**Continuity with Shot 4 (Critical):**

- [ ] **S5-SK1**: Same crow's feet depth and pattern as Shot 4
- [ ] **S5-SK2**: Same nasolabial fold depth as Shot 4
- [ ] **S5-SK3**: Same mole on left cheek near jawline -- same size, same position
- [ ] **S5-SK4**: Gray roots still visible, same distribution as Shot 4
- [ ] **S5-SK5**: Skin redness from crying is still present (especially nose tip, around eyes)
- [ ] **S5-SK6**: Eyes are reddened and puffy from crying (post-cry state, not fresh crying)
- [ ] **S5-SK7**: Tear residue visible on cheek(s) -- slight wet sheen or dried track
- [ ] **S5-SK8**: No makeup (consistent with Shot 4)

**Digital Zoom Degradation Effect on Skin:**

- [ ] **S5-SK9**: Skin texture is slightly softer / less sharp than Shot 4 due to 2-3x digital zoom
- [ ] **S5-SK10**: Fine details (individual pores, tiny wrinkles) are less distinct but major wrinkles and features still clear
- [ ] **S5-SK11**: Slight compression artifacts visible in shadow areas of face

**Expression:**

- [ ] **S5-EX1**: Quiet crying, not dramatic -- hand pressed to mouth
- [ ] **S5-EX2**: Shoulders slightly hunched or curved inward (grief posture)

### Expert 3 -- Hands & Object (Shot 5)

- [ ] **S5-H1**: One hand holds phone, other hand pressed to mouth -- same aging as Shots 2 and 4
- [ ] **S5-H2**: Wedding band visible on the hand holding the phone
- [ ] **S5-H3**: Veins and age spots consistent with previous shots
- [ ] **S5-H4**: Fingers pressing mouth show natural compression of lip tissue (not hovering)

**Object on Table:**

- [ ] **S5-O1**: Unwrapped furin visible on table -- glass reflects overhead fluorescent light (cool, not warm)
- [ ] **S5-O2**: Torn washi paper scattered naturally, not arranged
- [ ] **S5-O3**: Small torn paper pieces on floor (gravity-consistent placement)

**REJECTION TRIGGERS (any one = instant reject):**
- Face details inconsistent with Shot 4 (mole missing, wrong wrinkle pattern, gray roots gone)
- Image is razor-sharp despite supposed 2-3x digital zoom
- Hands look different from Shots 2 and 4
- Woman appears aware of the camera (looking toward it, posing)
- Crying looks dramatic or performative rather than quiet and private
- Skin shows beauty-filter smoothing

**Total criteria: 20 | Minimum pass: 17**

### Re-prompt Strategy (Shot 5 failures)

If continuity fails: add `"same woman from previous shots: dark mole on left cheek near jawline, gray roots in dark brown hair, deep nasolabial folds, crow's feet, puffy under-eyes, no makeup, worn beige cardigan"`
If image too sharp: add `"shot through doorway at 3 meters with 2-3x digital zoom, slight image softness, visible compression artifacts in shadows, not razor-sharp"`
If crying too dramatic: add `"quiet private crying, hand pressed to mouth, not wailing or dramatic, soft shoulders, hunched posture, unaware she is being observed"`

---

## SHOT 6 -- Furin Hanging, Breeze, Prismatic Light (25-30 s)

### Expert 2 -- Skin & Face

_No person in this shot. All skin/face criteria: N/A._

### Expert 3 -- Object Realism

- [ ] **S6-O1**: Furin glass is handcrafted-looking -- slightly irregular thickness, not machine-perfect
- [ ] **S6-O2**: Glass reflections are inconsistent (different parts of the glass catch light at different intensities depending on curvature)
- [ ] **S6-O3**: Prismatic light reflections on wall/window frame are small, scattered, and move with the swaying -- not a dramatic rainbow arc
- [ ] **S6-O4**: Tanzaku (paper strip) shows natural paper texture, not plastic-looking, flutters with visible weight
- [ ] **S6-O5**: String/cord suspending the furin shows slight fraying or wear
- [ ] **S6-O6**: Glass surface shows minor dust or fingerprint smudges (it has been handled)
- [ ] **S6-O7**: Swaying motion is pendular with slight irregularity from breeze gusts, not a perfect sine wave
- [ ] **S6-O8**: Clapper (zetsu) inside the furin moves with a slight delay relative to the glass body (different mass)

**REJECTION TRIGGERS (any one = instant reject):**
- Furin looks like a CGI render (perfect geometry, uniform reflections, no imperfections)
- Prismatic reflections are over-the-top (full rainbow, lens flare, fantasy lighting)
- Paper strip looks rigid or plastic rather than soft paper
- Glass has no dust, no smudges, no signs of being a real physical object

**Total criteria: 8 | Minimum pass: 6**

### Re-prompt Strategy (Shot 6 failures)

If glass too perfect: add `"handcrafted Japanese glass wind chime, slightly irregular in thickness, minor bubbles in glass, fingerprint smudge, thin dust"`
If prismatic effects too dramatic: add `"subtle small prismatic light reflections, not dramatic rainbows, tiny dancing spots of colored light, natural and understated"`

---

## GLOBAL REJECTION RULES (Apply to ALL Shots)

These are instant-reject conditions regardless of the shot's score:

1. **Wrong finger count**: Any hand with more or fewer than 5 fingers = REJECT
2. **Uncanny valley face**: Any face that triggers an instinctive "something is wrong" reaction = REJECT
3. **Symmetry**: Any perfectly symmetrical face, hand pair, or object arrangement = REJECT
4. **AI glow**: Any skin that has a luminous, poreless, filtered appearance = REJECT
5. **Object clipping**: Any finger, hand, or object passing through another solid object = REJECT
6. **Temporal inconsistency**: Any body part that changes shape, size, or features between frames within the same shot = REJECT
7. **Ring light eyes**: Circular or geometric catchlight reflections in eyes = REJECT
8. **Perfect teeth**: Uniform, bright white, perfectly aligned teeth = REJECT
9. **Plastic hair**: Hair that moves as a single mass rather than individual strands = REJECT
10. **Gravity violations**: Tears, paper, or objects that defy gravity = REJECT

---

## CROSS-SHOT CONTINUITY CHECKLIST

Before final assembly, verify these continuity requirements across shots:

| Element | Shots to Compare | Criterion |
|---------|-----------------|-----------|
| Young woman's hands | 1 vs 3 | Same skin tone, same chipped polish, same ring |
| Mother's hands | 2 vs 4 vs 5 | Same veins, same age spots, same wedding band, same nail ridges |
| Mother's face | 4 vs 5 | Same mole, same wrinkle pattern, same gray roots, same skin tone |
| Mother's clothing | 4 vs 5 | Same faded beige cardigan with same knit pull |
| Furin appearance | 1 vs 2 vs 5 vs 6 | Same glass color/shape (allow for different lighting) |
| Washi paper | 1 vs 2 vs 5 | Same cream color, similar crinkle texture |

**Continuity failure between shots = REJECT the non-matching shot and regenerate.**

---

## REVIEW WORKFLOW

1. **Generate** the batch of variations for a shot
2. **First pass**: Apply GLOBAL REJECTION RULES -- eliminate obvious failures
3. **Second pass**: Score each surviving variation against the shot-specific checklist
4. **Third pass**: Verify CROSS-SHOT CONTINUITY against already-approved shots
5. **Select** the highest-scoring variation that passes all three stages
6. **If no variation passes**: Apply the RE-PROMPT STRATEGY and generate a new batch
7. **Maximum re-prompt cycles**: 3 per shot before escalating to alternate model or post-production fixes

---

## POST-PRODUCTION FIXES (Last Resort)

If a shot scores within 2 points of the minimum but has specific fixable issues:

| Issue | Post-Production Fix | Acceptable? |
|-------|-------------------|-------------|
| Skin slightly too smooth | Add grain/noise overlay matching iPhone sensor noise | Yes |
| Missing compression artifacts (Shot 5) | Apply light JPEG compression + slight blur | Yes |
| Autofocus hunting absent | Manual focus pull in editing software | Yes |
| Tears too symmetrical | Mask and remove tear from one eye | Caution -- may look worse |
| Veins not prominent enough | NOT fixable in post -- must regenerate | No |
| Wrong finger count | NOT fixable in post -- must regenerate | No |
| Expression looks performed | NOT fixable in post -- must regenerate | No |
| Mole missing (Shot 4/5) | Can be painted in, but risky | Last resort only |
| Gray roots missing | NOT fixable in post -- must regenerate | No |

**Rule**: Post-production should fix TECHNICAL issues (noise, focus, compression). It must NEVER be used to fix ANATOMICAL or EXPRESSION issues. If the body is wrong, regenerate.
