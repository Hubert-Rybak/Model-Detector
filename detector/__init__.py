"""Model-Detector: extract and analyze provider/model fingerprints from LLM output.

Three layers of evidence are collected from text an unknown LLM produced:

1. Character-level forensics (``unicode_scan``): invisible or unusual code
   points, typographic punctuation habits, whitespace anomalies.
2. Stylometric / formatting features (``features``): markdown habits, lexical
   markers, rhetorical constructions, sentence statistics.
3. Behavioural probe answers (``probes``): self-report, knowledge cutoff,
   random-choice biases, tokenizer-sensitive tasks, system-prompt quoting.

``scorer`` combines them against the signature knowledge base in
``signatures`` and ``report`` renders a ranked verdict with the evidence.
"""

__version__ = "0.1.0"
