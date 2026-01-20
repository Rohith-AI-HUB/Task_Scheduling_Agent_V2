Good — now we’re talking with **actual constraints**, not abstractions. I’ll translate this into **operational guidance** you can act on immediately.

---

## First: decode what these limits *really* mean

### Key terms (quick, precise)

* **RPM**: Requests per minute → burst control
* **RPD**: Requests per day → daily hard cap
* **TPM**: Tokens per minute → sustained throughput
* **TPD**: Tokens per day → total daily budget

Your real bottlenecks are **RPD** and **TPM**, not RPM.

---

## Model-by-model reality check

### 1️⃣ `llama-3.1-8b-instant`

**RPM 30 | RPD 14.4k | TPM 6k**

**This is your workhorse.**

* High daily request budget
* Low TPM → keep prompts short
* Excellent for:

  * Test cases
  * CRUD code
  * JSON transforms
  * Summaries
  * Task metadata generation

**Constraint:**
You cannot dump long context or large files repeatedly.

**Verdict:**
✅ Default model (80% of traffic)

---

### 2️⃣ `llama-4-scout-17b-16e-instruct`

**RPM 30 | RPD 1k | TPM 30k**

This is a **scarce strategic asset**.

* High TPM → long reasoning, deep context
* Brutally low RPD → only 1,000 calls/day
* Best for:

  * Agent planning
  * Architecture decisions
  * Complex workflows
  * Multi-step reasoning

**Verdict:**
⚠️ Escalation-only model (≤10–15% of traffic)

Burn this quota carelessly and your system dies midday.

---

### 3️⃣ `llama-guard-4-12b`

**RPM 30 | RPD 14.4k | TPM 15k**

This is **not optional** if you’re serious.

* Fast enough
* High RPD
* Use for:

  * Output validation
  * Safety checks
  * Policy enforcement
  * Schema sanity checks

**Verdict:**
🛡 Always-on guardrail (cheap insurance)

---

### 4️⃣ `llama-prompt-guard-2-86m`

**RPM 30 | RPD 14.4k | TPM 15k**

Ultra-light, ultra-fast.

* Use before generation
* Detect:

  * Prompt injection
  * Tool misuse
  * Malformed intent

**Verdict:**
🛡 First gate in the pipeline

---

## The ONLY architecture that makes sense

Here is the **quota-aware routing model** you should implement:

```
Incoming Request
   ↓
Prompt Guard (2-86m)   ← cheap, always
   ↓
Rule-based Intent Classifier
   ↓
┌─────────────────────────────────────┐
│ Simple / Structured / Repetitive     → llama-3.1-8b-instant
│ Complex / Multi-step / Agent logic   → llama-4-scout-17b
└─────────────────────────────────────┘
   ↓
Output Guard (12b)
   ↓
Persist / Execute
```

No exceptions.

---

## Hard rules to survive the quotas

### Rule 1 — NEVER send raw user text to Scout

Normalize first. Always.

Scout calls should receive:

* Clean task schema
* Minimal noise
* No chat history unless required

---

### Rule 2 — Cache aggressively

If input hash repeats → reuse output.

This alone can cut usage **30–50%**.

---

### Rule 3 — Template > LLM

For your Task_Scheduling App:

* 60–70% of test cases should come from templates
* LLM fills gaps only

This preserves TPM and RPD.

---

### Rule 4 — Scout escalation must be explicit

Example criteria:

* Prompt length > 2k tokens
* Multi-agent planning required
* Task has dependencies + retries + conditions

Everything else stays on 8B.

---

## Capacity planning (real numbers)

If done right, per day you can handle roughly:

* **~10k lightweight tasks/day** (8B)
* **~500–800 complex tasks/day** (Scout)
* With full safety coverage

That’s solid for an MVP to early-scale product.

---

## Bottom line (no sugarcoating)

* You **cannot** treat these models equally
* Scout is rare fuel — burn it wisely
* 8B is your daily engine
* Guard models are mandatory, not “nice to have”
* Routing logic matters more than model size

If you want next:

* I can give you a **ready-made router function**
* A **Scout escalation policy**
* Or a **prompt compression strategy** to stretch TPM

You’re now operating at **system-design level**, which is exactly where you should be.

  3. Build Features (choose one)

  We can now implement any of these on top of the infrastructure:

  - Test Case Generation (most immediate value)
  - LLM Grading (enhance existing evaluation)
  - Smart Deadline Suggestions
  - Problem Statement Quality Checker
  - Student Hint System
  - Grade Insights

  Which feature would you like me to implement first? I recommend Test Case Generation since it's a teacher-facing feature that immediately demonstrates value.