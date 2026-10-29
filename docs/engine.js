// Model-Detector engine: runs in the browser (GitHub Pages) and in Node (tools/).
// Layers: (1) character forensics + hidden-payload decoders, (2) stylometric features,
// (3) hand rules, (4) a trainable naive-Bayes fingerprint over words, bigrams and style tokens.
import { FAMILIES, FAMILY_IDS, LEXICON } from "./reference.js";

// ------------------------------------------------------------------ 1. Unicode forensics
export const INVISIBLE = {
  0x200B: "ZERO WIDTH SPACE", 0x200C: "ZERO WIDTH NON-JOINER", 0x200D: "ZERO WIDTH JOINER",
  0x200E: "LEFT-TO-RIGHT MARK", 0x200F: "RIGHT-TO-LEFT MARK", 0x2060: "WORD JOINER",
  0x2061: "FUNCTION APPLICATION", 0x2062: "INVISIBLE TIMES", 0x2063: "INVISIBLE SEPARATOR", 0x2064: "INVISIBLE PLUS",
  0x2066: "LEFT-TO-RIGHT ISOLATE", 0x2067: "RIGHT-TO-LEFT ISOLATE", 0x2068: "FIRST STRONG ISOLATE", 0x2069: "POP DIRECTIONAL ISOLATE",
  0x202A: "LEFT-TO-RIGHT EMBEDDING", 0x202B: "RIGHT-TO-LEFT EMBEDDING", 0x202C: "POP DIRECTIONAL FORMATTING",
  0x202D: "LEFT-TO-RIGHT OVERRIDE", 0x202E: "RIGHT-TO-LEFT OVERRIDE", 0xFEFF: "ZERO WIDTH NO-BREAK SPACE (BOM)",
  0x00AD: "SOFT HYPHEN", 0x034F: "COMBINING GRAPHEME JOINER", 0x180E: "MONGOLIAN VOWEL SEPARATOR", 0x061C: "ARABIC LETTER MARK",
  0x115F: "HANGUL CHOSEONG FILLER", 0x1160: "HANGUL JUNGSEONG FILLER", 0x3164: "HANGUL FILLER", 0xFFA0: "HALFWIDTH HANGUL FILLER",
};
export const SPACE_VARIANTS = {
  0x00A0: "NO-BREAK SPACE", 0x202F: "NARROW NO-BREAK SPACE", 0x2000: "EN QUAD", 0x2001: "EM QUAD", 0x2002: "EN SPACE",
  0x2003: "EM SPACE", 0x2004: "THREE-PER-EM SPACE", 0x2005: "FOUR-PER-EM SPACE", 0x2006: "SIX-PER-EM SPACE", 0x2007: "FIGURE SPACE",
  0x2008: "PUNCTUATION SPACE", 0x2009: "THIN SPACE", 0x200A: "HAIR SPACE", 0x205F: "MEDIUM MATHEMATICAL SPACE",
  0x3000: "IDEOGRAPHIC SPACE", 0x1680: "OGHAM SPACE MARK",
};
const DASHES = { 0x2010: "HYPHEN", 0x2011: "NON-BREAKING HYPHEN", 0x2012: "FIGURE DASH", 0x2013: "EN DASH", 0x2014: "EM DASH", 0x2015: "HORIZONTAL BAR", 0x2212: "MINUS SIGN", 0x2E3A: "TWO-EM DASH", 0xFE58: "SMALL EM DASH", 0xFF0D: "FULLWIDTH HYPHEN-MINUS" };
const QUOTES = { 0x2018: "LEFT SINGLE QUOTATION MARK", 0x2019: "RIGHT SINGLE QUOTATION MARK", 0x201A: "SINGLE LOW-9 QUOTATION MARK", 0x201C: "LEFT DOUBLE QUOTATION MARK", 0x201D: "RIGHT DOUBLE QUOTATION MARK", 0x201E: "DOUBLE LOW-9 QUOTATION MARK", 0x00AB: "LEFT-POINTING DOUBLE ANGLE QUOTATION MARK", 0x00BB: "RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK", 0x2039: "SINGLE LEFT-POINTING ANGLE QUOTATION MARK", 0x203A: "SINGLE RIGHT-POINTING ANGLE QUOTATION MARK", 0x02BC: "MODIFIER LETTER APOSTROPHE" };
const SYMBOLS = { 0x00D7: "MULTIPLICATION SIGN", 0x00F7: "DIVISION SIGN", 0x00B1: "PLUS-MINUS SIGN", 0x2264: "LESS-THAN OR EQUAL TO", 0x2265: "GREATER-THAN OR EQUAL TO", 0x2260: "NOT EQUAL TO", 0x2248: "ALMOST EQUAL TO", 0x2192: "RIGHTWARDS ARROW", 0x2190: "LEFTWARDS ARROW", 0x21D2: "RIGHTWARDS DOUBLE ARROW", 0x2194: "LEFT RIGHT ARROW", 0x2713: "CHECK MARK", 0x2714: "HEAVY CHECK MARK", 0x2717: "BALLOT X", 0x2022: "BULLET", 0x25E6: "WHITE BULLET", 0x2023: "TRIANGULAR BULLET", 0x25AA: "BLACK SMALL SQUARE", 0x2026: "HORIZONTAL ELLIPSIS", 0x00B0: "DEGREE SIGN", 0x2103: "DEGREE CELSIUS", 0x2109: "DEGREE FAHRENHEIT", 0x00B2: "SUPERSCRIPT TWO", 0x00B3: "SUPERSCRIPT THREE", 0x00BD: "VULGAR FRACTION ONE HALF", 0x2122: "TRADE MARK SIGN", 0x00A9: "COPYRIGHT SIGN", 0x00AE: "REGISTERED SIGN", 0x20AC: "EURO SIGN", 0x00A3: "POUND SIGN", 0x00A5: "YEN SIGN" };

const inRange = (cp, lo, hi) => cp >= lo && cp <= hi;
const isEmoji = (cp) => inRange(cp, 0x1F300, 0x1FAFF) || inRange(cp, 0x2600, 0x27BF) || inRange(cp, 0x1F1E6, 0x1F1FF) || inRange(cp, 0x2B00, 0x2BFF) || inRange(cp, 0x1F000, 0x1F02F);
const isVS = (cp) => inRange(cp, 0xFE00, 0xFE0F) || inRange(cp, 0xE0100, 0xE01EF);
const isTag = (cp) => inRange(cp, 0xE0000, 0xE007F);
const isPUA = (cp) => inRange(cp, 0xE000, 0xF8FF) || inRange(cp, 0xF0000, 0xFFFFD) || inRange(cp, 0x100000, 0x10FFFD);
const isMathAlnum = (cp) => inRange(cp, 0x1D400, 0x1D7FF);
const isFullwidth = (cp) => inRange(cp, 0xFF01, 0xFF5E);

export function classifyCodepoint(cp) {
  if (cp < 0x80) return "ascii";
  if (INVISIBLE[cp]) return "invisible";
  if (isTag(cp)) return "tag_char";
  if (isVS(cp)) return "variation_selector";
  if (SPACE_VARIANTS[cp]) return "space_variant";
  if (DASHES[cp]) return "dash";
  if (QUOTES[cp]) return "quote";
  if (SYMBOLS[cp]) return "symbol";
  if (isEmoji(cp)) return "emoji";
  if (isPUA(cp)) return "private_use";
  if (isMathAlnum(cp)) return "math_alnum";
  if (isFullwidth(cp)) return "fullwidth";
  const ch = String.fromCodePoint(cp);
  if (/\p{L}/u.test(ch)) return "letter_nonascii";
  if (/\p{M}/u.test(ch)) return "combining_mark";
  if (/\p{Cf}/u.test(ch)) return "invisible";
  if (/\p{C}/u.test(ch)) return "control";
  if (/\p{Z}/u.test(ch)) return "space_variant";
  if (/\p{P}/u.test(ch)) return "punct_nonascii";
  if (/\p{S}/u.test(ch)) return "symbol";
  return "other";
}
const HIDDEN_CLASSES = new Set(["invisible", "tag_char", "variation_selector", "space_variant", "private_use", "control"]);
export const cpName = (cp) => INVISIBLE[cp] || SPACE_VARIANTS[cp] || DASHES[cp] || QUOTES[cp] || SYMBOLS[cp] || (isTag(cp) ? `TAG ${cp >= 0xE0020 && cp <= 0xE007E ? JSON.stringify(String.fromCharCode(cp - 0xE0000)) : cp.toString(16)}` : isVS(cp) ? `VARIATION SELECTOR-${cp <= 0xFE0F ? cp - 0xFE00 + 1 : cp - 0xE0100 + 17}` : isEmoji(cp) ? "emoji" : isPUA(cp) ? "PRIVATE USE" : isMathAlnum(cp) ? "MATHEMATICAL ALPHANUMERIC" : `U+${cp.toString(16).toUpperCase().padStart(4, "0")}`);
const hex = (cp) => "U+" + cp.toString(16).toUpperCase().padStart(4, "0");

function scriptOf(ch) {
  if (/\p{Script=Latin}/u.test(ch)) return "LATIN";
  if (/\p{Script=Cyrillic}/u.test(ch)) return "CYRILLIC";
  if (/\p{Script=Greek}/u.test(ch)) return "GREEK";
  if (/\p{Script=Armenian}/u.test(ch)) return "ARMENIAN";
  return null;
}

function countRe(text, re) { const m = text.match(re); return m ? m.length : 0; }

export function scanUnicode(text) {
  const r = {
    total_chars: 0, non_ascii_chars: 0, hits: [], invisible_count: 0, tag_char_count: 0, variation_selector_count: 0,
    private_use_count: 0, space_variant_count: 0, narrow_nbsp_count: 0, nbsp_count: 0, soft_hyphen_count: 0, zero_width_count: 0,
    bidi_control_count: 0, mixed_script_words: [], math_alnum_count: 0, fullwidth_count: 0, emoji_count: 0,
    straight_double_quotes: 0, curly_double_quotes: 0, straight_apostrophes: 0, curly_apostrophes: 0, em_dash: 0, en_dash: 0,
    minus_sign: 0, spaced_em_dash: 0, unspaced_em_dash: 0, spaced_hyphen_as_dash: 0, double_hyphen: 0, ellipsis_char: 0,
    ellipsis_dots: 0, multiplication_sign: 0, arrows: 0, bullet_char: 0, crlf_lines: 0, lf_lines: 0, trailing_whitespace_lines: 0,
    tab_count: 0, double_space_after_period: 0, multiple_consecutive_spaces: 0, words: 0, hidden_char_contexts: [], space_variant_contexts: [],
  };
  const counter = new Map();
  const cps = Array.from(text);
  r.total_chars = cps.length;
  const ctx = (i) => {
    const lo = Math.max(0, i - 18), hi = Math.min(cps.length, i + 19);
    return cps.slice(lo, hi).map((c) => { const cp = c.codePointAt(0); return (cp >= 0x80 && HIDDEN_CLASSES.has(classifyCodepoint(cp))) ? `[${hex(cp)}]` : c === "\n" ? "\\n" : c; }).join("");
  };
  cps.forEach((c, i) => {
    const cp = c.codePointAt(0);
    if (cp < 0x80) return;
    r.non_ascii_chars++;
    counter.set(cp, (counter.get(cp) || 0) + 1);
    const k = classifyCodepoint(cp);
    if (k === "invisible") {
      r.invisible_count++;
      if ([0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF].includes(cp)) r.zero_width_count++;
      if (cp === 0x00AD) r.soft_hyphen_count++;
      if ([0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x061C].includes(cp)) r.bidi_control_count++;
      if (r.hidden_char_contexts.length < 12) r.hidden_char_contexts.push(ctx(i));
    } else if (k === "tag_char") { r.tag_char_count++; if (r.hidden_char_contexts.length < 12) r.hidden_char_contexts.push(ctx(i)); }
    else if (k === "variation_selector") {
      r.variation_selector_count++;
      const prev = i > 0 ? cps[i - 1].codePointAt(0) : 0;
      const attached = prev && (isEmoji(prev) || classifyCodepoint(prev) === "symbol" || isVS(prev) && i > 1 && isEmoji(cps[i - 2].codePointAt(0)));
      if (!attached && r.hidden_char_contexts.length < 12) r.hidden_char_contexts.push(ctx(i));
    }
    else if (k === "private_use") { r.private_use_count++; if (r.hidden_char_contexts.length < 12) r.hidden_char_contexts.push(ctx(i)); }
    else if (k === "space_variant") { r.space_variant_count++; if (cp === 0x202F) r.narrow_nbsp_count++; else if (cp === 0x00A0) r.nbsp_count++; if (r.space_variant_contexts.length < 12) r.space_variant_contexts.push(ctx(i)); }
    else if (k === "math_alnum") r.math_alnum_count++;
    else if (k === "fullwidth") r.fullwidth_count++;
    else if (k === "emoji") r.emoji_count++;
  });
  r.hits = [...counter.entries()].sort((a, b) => b[1] - a[1]).map(([cp, n]) => ({ codepoint: hex(cp), char: String.fromCodePoint(cp), name: cpName(cp), klass: classifyCodepoint(cp), count: n }));
  r.straight_double_quotes = countRe(text, /"/g);
  r.curly_double_quotes = countRe(text, /[\u201C\u201D]/g);
  r.straight_apostrophes = countRe(text, /[A-Za-z]'[A-Za-z]/g);
  r.curly_apostrophes = countRe(text, /[A-Za-z]\u2019[A-Za-z]/g);
  r.em_dash = countRe(text, /\u2014/g);
  r.en_dash = countRe(text, /\u2013/g);
  r.minus_sign = countRe(text, /\u2212/g);
  r.spaced_em_dash = countRe(text, /\s\u2014\s/g);
  r.unspaced_em_dash = countRe(text, /\S\u2014\S/g);
  r.spaced_hyphen_as_dash = countRe(text, /(?<=[A-Za-z0-9,.)]) - (?=[A-Za-z0-9(])/g);
  r.double_hyphen = countRe(text, /(?<!-)--(?!-)/g);
  r.ellipsis_char = countRe(text, /\u2026/g);
  r.ellipsis_dots = countRe(text, /(?<!\.)\.\.\.(?!\.)/g);
  r.multiplication_sign = countRe(text, /\u00D7/g);
  r.arrows = countRe(text, /\u2192|\u2190|\u21D2|\u2194|->|=>/g);
  r.bullet_char = countRe(text, /\u2022/g);
  r.crlf_lines = countRe(text, /\r\n/g);
  r.lf_lines = countRe(text, /\n/g) - r.crlf_lines;
  r.trailing_whitespace_lines = text.split(/\r?\n/).filter((l) => /[ \t]$/.test(l)).length;
  r.tab_count = countRe(text, /\t/g);
  r.double_space_after_period = countRe(text, /[.!?]  +[A-Z]/g);
  r.multiple_consecutive_spaces = countRe(text, /(?<=\S)  +(?=\S)/g);
  r.words = countRe(text, /\b\w+\b/g);
  const seen = new Set();
  for (const w of text.match(/[\p{L}\p{M}]+/gu) || []) {
    const scripts = new Set();
    for (const ch of w) { const s = scriptOf(ch); if (s) scripts.add(s); }
    if (scripts.size > 1 && !seen.has(w)) { seen.add(w); if (r.mixed_script_words.length < 20) r.mixed_script_words.push(w); }
  }
  return r;
}

export function unicodeFindings(r) {
  const out = [];
  if (r.zero_width_count) out.push(["HIGH", `${r.zero_width_count} zero-width character(s) (U+200B/200C/200D/2060/FEFF): classic invisible-payload carrier`]);
  if (r.tag_char_count) out.push(["HIGH", `${r.tag_char_count} Unicode TAG character(s) (U+E0000-E007F): invisible ASCII payload carrier`]);
  if (r.private_use_count) out.push(["HIGH", `${r.private_use_count} private-use code point(s)`]);
  if (r.soft_hyphen_count) out.push(["HIGH", `${r.soft_hyphen_count} soft hyphen(s) (U+00AD), invisible in most renderers`]);
  if (r.bidi_control_count) out.push(["HIGH", `${r.bidi_control_count} bidirectional control character(s)`]);
  if (r.variation_selector_count && r.hidden_char_contexts.some((c) => /\[U\+FE0|\[U\+E01/.test(c))) out.push(["HIGH", `variation selector(s) not attached to an emoji: byte-smuggling carrier`]);
  if (r.narrow_nbsp_count) out.push(["MEDIUM", `${r.narrow_nbsp_count} NARROW NO-BREAK SPACE (U+202F): documented quirk of OpenAI o3/o4-mini/GPT-5 output (OpenAI says it is a training artefact, not a watermark)`]);
  if (r.nbsp_count) out.push(["LOW", `${r.nbsp_count} NO-BREAK SPACE (U+00A0): typographic habit or copy artefact`]);
  if (r.mixed_script_words.length) out.push(["HIGH", `mixed-script words (homoglyphs?): ${r.mixed_script_words.slice(0, 8).join(", ")}`]);
  if (r.math_alnum_count) out.push(["MEDIUM", `${r.math_alnum_count} mathematical-alphanumeric letters (fake bold/italic fonts)`]);
  if (r.fullwidth_count) out.push(["LOW", `${r.fullwidth_count} fullwidth ASCII variant(s)`]);
  if (r.crlf_lines && r.lf_lines) out.push(["LOW", `mixed line endings: ${r.crlf_lines} CRLF vs ${r.lf_lines} LF`]);
  if (r.trailing_whitespace_lines) out.push(["LOW", `${r.trailing_whitespace_lines} line(s) with trailing whitespace (possible whitespace steganography)`]);
  if (r.double_space_after_period) out.push(["LOW", `${r.double_space_after_period} double space(s) after sentence end`]);
  if (!out.length) out.push(["NONE", "no hidden or anomalous characters: any deliberate watermark here would be statistical (token-choice) and unreadable without the provider's key"]);
  return out;
}

// --- Hidden-payload decoders (steganographic schemes people actually use) ---
const printableRatio = (s) => s.length ? [...s].filter((c) => /[\x20-\x7E\n\t]/.test(c)).length / [...s].length : 0;
function bitsToText(bits) {
  let s = "";
  for (let i = 0; i + 8 <= bits.length; i += 8) s += String.fromCharCode(parseInt(bits.slice(i, i + 8), 2));
  return s;
}
export function decodeHidden(text) {
  const out = [];
  const cps = Array.from(text).map((c) => c.codePointAt(0));
  // 1. TAG characters -> ASCII
  const tags = cps.filter(isTag);
  if (tags.length) {
    const s = tags.map((cp) => (cp >= 0xE0020 && cp <= 0xE007E) ? String.fromCharCode(cp - 0xE0000) : (cp === 0xE007F ? "\u2404" : "?")).join("");
    out.push({ scheme: "Unicode TAG characters (U+E0000 block) decoded as ASCII", count: tags.length, decoded: s, printable: printableRatio(s) });
  }
  // 2. Variation selectors -> bytes (FE00-FE0F = 0..15, E0100-E01EF = 16..255)
  const vsRuns = [];
  let run = [];
  cps.forEach((cp, i) => {
    if (isVS(cp) && !(i > 0 && isEmoji(cps[i - 1]) && cp === 0xFE0F && run.length === 0)) run.push(cp <= 0xFE0F ? cp - 0xFE00 : cp - 0xE0100 + 16);
    else { if (run.length >= 2) vsRuns.push(run); run = []; }
  });
  if (run.length >= 2) vsRuns.push(run);
  for (const bytes of vsRuns) {
    let decoded = "";
    try { decoded = new TextDecoder("utf-8", { fatal: false }).decode(new Uint8Array(bytes)); } catch { decoded = String.fromCharCode(...bytes); }
    out.push({ scheme: "Variation-selector byte smuggling (VS1-VS256 = 0-255)", count: bytes.length, hex: bytes.map((b) => b.toString(16).padStart(2, "0")).join(" "), decoded, printable: printableRatio(decoded) });
  }
  // 3. Zero-width binary (several common alphabets)
  const zw = cps.filter((cp) => [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF].includes(cp));
  if (zw.length >= 8) {
    const schemes = [["U+200B=0, U+200C=1", { 0x200B: "0", 0x200C: "1" }], ["U+200B=0, U+200D=1", { 0x200B: "0", 0x200D: "1" }], ["U+200C=0, U+200D=1", { 0x200C: "0", 0x200D: "1" }], ["U+2060=0, U+200B=1", { 0x2060: "0", 0x200B: "1" }], ["U+200B=0, U+FEFF=1", { 0x200B: "0", 0xFEFF: "1" }]];
    let best = null;
    for (const [name, map] of schemes) {
      const bits = zw.filter((cp) => map[cp] !== undefined).map((cp) => map[cp]).join("");
      if (bits.length < 8) continue;
      const s = bitsToText(bits);
      const pr = printableRatio(s);
      if (!best || pr > best.printable) best = { scheme: `Zero-width binary (${name})`, count: zw.length, bits: bits.slice(0, 256), decoded: s, printable: pr };
    }
    if (best) out.push(best);
    // 2-bit alphabet: ZWSP ZWNJ ZWJ WJ
    const map4 = { 0x200B: "00", 0x200C: "01", 0x200D: "10", 0x2060: "11" };
    const bits4 = zw.filter((cp) => map4[cp]).map((cp) => map4[cp]).join("");
    if (bits4.length >= 8) { const s = bitsToText(bits4); out.push({ scheme: "Zero-width 2-bit alphabet (ZWSP/ZWNJ/ZWJ/WJ)", count: zw.length, bits: bits4.slice(0, 256), decoded: s, printable: printableRatio(s) }); }
  }
  // 4. Trailing whitespace per line (space=0, tab=1) and double-space word gaps
  const lines = text.split(/\r?\n/);
  const trailing = lines.map((l) => (l.match(/[ \t]+$/) || [""])[0]).filter((t) => t);
  if (trailing.length >= 4) {
    const bits = trailing.join("").replace(/ /g, "0").replace(/\t/g, "1");
    const s = bitsToText(bits);
    out.push({ scheme: "Trailing-whitespace steganography (space=0, tab=1)", count: trailing.length, bits: bits.slice(0, 256), decoded: s, printable: printableRatio(s) });
  }
  const gaps = text.match(/(?<=\S)( {1,2})(?=\S)/g) || [];
  if (gaps.length >= 16 && gaps.some((g) => g.length === 2) && gaps.filter((g) => g.length === 2).length >= 4) {
    const bits = gaps.map((g) => (g.length === 2 ? "1" : "0")).join("");
    const s = bitsToText(bits);
    out.push({ scheme: "Word-gap steganography (single space=0, double space=1)", count: gaps.length, bits: bits.slice(0, 256), decoded: s, printable: printableRatio(s) });
  }
  // 5. Homoglyph bits (Latin=0, confusable Cyrillic/Greek=1) over confusable letters
  const CONFUSABLE = "\u0430\u0435\u043E\u0440\u0441\u0443\u0445\u0456\u0458\u04BB\u0501\u051B\u0455\u0410\u0412\u0415\u041A\u041C\u041D\u041E\u0420\u0421\u0422\u0425\u03BF\u0391\u0392\u0395\u0396\u0397\u0399\u039A\u039C\u039D\u039F\u03A1\u03A4\u03A5\u03A7";
  const conf = [...text].filter((c) => CONFUSABLE.includes(c));
  if (conf.length) out.push({ scheme: "Confusable (homoglyph) letters present", count: conf.length, decoded: conf.join(""), printable: 0, note: "a Latin/Cyrillic swap per letter can carry one bit; mapping is scheme-specific" });
  return out;
}

export function annotate(text) {
  const segs = [];
  let buf = "";
  for (const c of text) {
    const cp = c.codePointAt(0);
    const k = cp < 0x80 ? "ascii" : classifyCodepoint(cp);
    if (HIDDEN_CLASSES.has(k)) { if (buf) { segs.push({ text: buf }); buf = ""; } segs.push({ text: c, hidden: true, label: hex(cp), klass: k }); }
    else if (k === "quote" || k === "dash" || k === "symbol" || k === "letter_nonascii" || k === "math_alnum" || k === "fullwidth") { if (buf) { segs.push({ text: buf }); buf = ""; } segs.push({ text: c, mark: true, label: `${hex(cp)} ${cpName(cp)}`, klass: k }); }
    else buf += c;
  }
  if (buf) segs.push({ text: buf });
  return segs;
}

// ------------------------------------------------------------------ 2. Stylometric features
const CODE_FENCE_RE = /```[^\n]*\n[\s\S]*?```/g;
const INLINE_CODE_RE = /`[^`\n]+`/g;
const HEADER_RE = /^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$/gm;
const BOLD_RE = /\*\*([^*\n][^*\n]*?)\*\*|__([^_\n][^_\n]*?)__/g;
const ITALIC_RE = /(?<![*\w])\*(?!\*)([^*\n]+?)\*(?!\*)|(?<![_\w])_(?!_)([^_\n]+?)_(?!_)/g;
const BULLET_RE = /^([ \t]*)([-*+\u2022\u2013\u2014\u25E6\u25AA\u2023])[ \t]+(.*)$/gm;
const NUMBERED_RE = /^([ \t]*)(\d+)([.)])[ \t]+(.*)$/gm;
const TABLE_SEP_RE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/m;
const TABLE_ROW_RE = /^\s*\|.*\|\s*$/gm;
const HR_RE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/gm;
const BLOCKQUOTE_RE = /^\s*>\s?/gm;
const WORD_RE = /[A-Za-z][A-Za-z'\u2019-]*/g;
const EMOJI_RE = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
const SUMMARY_RE = /^(?:#{1,6}\s*)?(?:\*\*)?\s*(?:summary|key takeaways?|tl;?dr|bottom line|in summary|conclusion|final thoughts|wrap[- ]?up|quick recap|recap|the short version|overview|next steps|what this means)\b/im;

export const OPENERS = [
  ["certainly", /^\s*certainly[!,.]/i], ["sure", /^\s*sure[!,.]/i], ["absolutely", /^\s*absolutely[!,.]/i], ["of_course", /^\s*of course[!,.]/i],
  ["great_question", /^\s*(great|good|excellent|fantastic|interesting) question/i], ["heres", /^\s*(here'?s|here is|here are)\b/i],
  ["happy_to", /^\s*i('d| would) be (happy|glad) to|^\s*i'?m happy to/i], ["okay_alright", /^\s*(okay|ok|alright|all right)[!,.]/i],
  ["lets", /^\s*let'?s\b/i], ["youre_right", /^\s*you'?re (absolutely |completely |totally )?right/i], ["greeting", /^\s*(hi|hello|hey)\b/i],
  ["title_or_header", /^\s*(#{1,6}\s|\*\*[^*]+\*\*\s*$)/], ["direct", /^\s*[A-Z][a-z]/],
];
export const CLOSERS = [
  ["offer_would_you_like", /would you like( me)?\b/i], ["offer_want_me_to", /\b(want|like) me to\b|\bdo you want me\b|\bshall i\b|\bshould i\b/i],
  ["offer_if_youd_like", /\bif you('d| would) like\b|\bif you want\b|\bif you need\b|\bif you'?re interested\b/i], ["let_me_know", /\blet me know\b/i],
  ["feel_free", /\bfeel free\b/i], ["hope_this_helps", /\bhope (this|that|it) helps\b/i], ["happy_to_help", /\bhappy to (help|assist|elaborate|dive|go)\b/i],
  ["any_other_questions", /\bany (other|further|more) questions\b/i], ["ends_with_question", /\?\s*$/], ["emoji_signoff", /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]\s*$/u],
];
export const RHETORIC = {
  antithesis_not_but: [/\b(?:is|it'?s|that'?s|this is|was|are|were|isn'?t|aren'?t|wasn'?t|not)\s+(?:just|only|merely|simply|about|really)?\s*[^.!?;:\n]{2,70}?(?:\u2014|\u2013|,|;|\.)\s*(?:it'?s|but|rather|that'?s)\b/gi],
  not_x_period_its_y: [/\b(?:Not|Isn'?t|It isn'?t)\b[^.!?\n]{2,60}[.!]\s+(?:It'?s|That'?s)\b/g],
  tricolon_fragments: [/\b(?:No|Not)\s[^.!?\n]{1,40}[.!]\s+(?:No|Not)\s[^.!?\n]{1,40}[.!]\s+(?:Just|Only|Simply)\b/g],
  the_catch_question: [/\b(?:The|Your|My)\s+(?:catch|result|kicker|upshot|twist|problem|answer|takeaway|bottom line|short version|good news|bad news|key|trick|difference|reason|cost|risk|downside|upside)\?/g],
  heres_the_thing: [/\bhere'?s (?:the thing|why|how|what|where|the catch|the deal|the kicker|a quick|the short version|the breakdown|the gist)\b/gi],
  think_of_it: [/\b(?:think of (?:it|this|them) (?:like|as)|imagine (?:you|a|that|this|if))\b/gi],
  break_it_down: [/\b(?:let'?s|i'?ll)?\s*break (?:it|this|that|things) down\b/gi],
  in_other_words: [/\bin other words\b/gi],
  bottom_line: [/\b(?:bottom line|the takeaway|key takeaways?|tl;?dr|in short|in summary|in a nutshell|to sum up|in essence|at its core|at the end of the day|put simply|simply put|long story short)\b/gi],
  worth_noting: [/\b(?:it'?s worth (?:noting|mentioning|remembering)|note that|keep in mind|it'?s important to (?:note|remember|understand)|importantly|notably|crucially|that said|that being said|with that said)\b/gi],
  dash_aside: [/\s\u2014\s[^\u2014\n]{3,60}\s\u2014\s/g],
  rhetorical_q_then_answer: [/\?\s+(?:Because|Yes|No|Not|It|That|Simple|Exactly|Absolutely|Well)\b/g],
  sentence_initial_and_but: [/(?:^|[.!?]\s+)(?:And|But|So|Because|Which|Or)\s+[a-z]/gm],
  one_word_sentence: [/(?:^|[.!?]\s+)[A-Z][a-z]{1,12}[.!]/gm],
  parenthetical: [/\([^()\n]{3,80}\)/g],
  second_person_you: [/\byou(?:'re|'ll|'ve|'d|r)?\b/gi],
  first_person_i: [/\bI(?:'m|'d|'ll|'ve)?\b/g],
  we_us: [/\b(?:we|us|our)\b/gi],
  exclamations: [/!/g], questions: [/\?/g], semicolons: [/;/g], colons_in_prose: [/[A-Za-z]:\s/g],
  quoted_phrases: [/["\u201C][^"\u201D\n]{2,60}["\u201D]/g],
  numbers_with_units: [/\b\d+(?:[.,]\d+)?\s?(?:%|km|mi|kg|lb|ms|s|m|cm|mm|\u00B0[CF]?|px|GB|MB|KB|TB|Hz|kHz|MHz|GHz|W|kW|V|A|mAh)\b/g],
  contractions: [/\b\w+(?:n't|'re|'ve|'ll|'d|'m|'s)\b|\b\w+(?:n\u2019t|\u2019re|\u2019ve|\u2019ll|\u2019d|\u2019m|\u2019s)\b/gi],
};

export function stripCode(text) { return text.replace(CODE_FENCE_RE, "\n").replace(INLINE_CODE_RE, " "); }
const rate = (n, words) => (words ? Math.round((1000 * n / words) * 100) / 100 : 0);
const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
const pstdev = (a) => { const m = mean(a); return a.length ? Math.sqrt(mean(a.map((x) => (x - m) ** 2))) : 0; };

export function sentencesOf(prose) {
  const cleaned = prose.replace(/^\s*(?:#{1,6}\s+|[-*+\u2022]\s+|\d+[.)]\s+|>\s*)/gm, "").replace(/\*\*|__/g, "");
  return cleaned.split(/(?<=[.!?])\s+(?=[A-Z"'\u201C(\[])|\n{2,}/).map((s) => s.trim()).filter((s) => s && (s.match(WORD_RE) || []).length >= 1);
}

function isTitleCase(t) {
  t = t.replace(/[*_`#:]/g, "").trim();
  const stop = new Set(["a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "vs", "at", "by", "is", "as"]);
  const ws = t.split(/\s+/).filter((w) => /^[A-Za-z]+$/.test(w));
  if (ws.length < 2) return false;
  const rest = ws.slice(1).filter((w) => !stop.has(w.toLowerCase()));
  if (!rest.length) return false;
  return rest.filter((w) => /^[A-Z]/.test(w)).length / rest.length >= 0.7;
}

export function extractFeatures(text) {
  const f = {};
  const raw = text;
  const prose = stripCode(raw);
  const lower = prose.toLowerCase();
  const words = prose.match(WORD_RE) || [];
  const nw = words.length;
  f.n_chars = raw.length; f.n_words = nw;
  const lines = raw.split(/\r?\n/);
  f.n_lines = lines.length;
  const paragraphs = raw.trim().split(/\n\s*\n/).filter((p) => p.trim());
  f.n_paragraphs = paragraphs.length;
  const paraLens = paragraphs.map((p) => (p.match(WORD_RE) || []).length);
  f.para_words_mean = Math.round(mean(paraLens) * 10) / 10 || 0;
  f.para_words_max = paraLens.length ? Math.max(...paraLens) : 0;
  f.share_one_line_paragraphs = paragraphs.length ? Math.round(100 * paragraphs.filter((p, i) => !p.trim().includes("\n") && paraLens[i] < 25).length / paragraphs.length) / 100 : 0;
  // markdown
  const headers = [...raw.matchAll(HEADER_RE)];
  f.headers_total = headers.length;
  for (const l of [1, 2, 3, 4]) f[`headers_h${l}`] = headers.filter((h) => h[1].length === l).length;
  const ht = headers.map((h) => h[2]);
  f.headers_title_case_share = ht.length ? Math.round(100 * ht.filter(isTitleCase).length / ht.length) / 100 : 0;
  f.headers_with_colon = ht.filter((t) => t.trimEnd().endsWith(":")).length;
  f.headers_with_emoji = ht.filter((t) => EMOJI_RE.test(t)).length;
  f.bold_spans = countRe(raw, BOLD_RE);
  f.bold_rate = rate(f.bold_spans, nw);
  f.bold_whole_line = countRe(raw, /^\s*\*\*[^*\n]+\*\*:?\s*$/gm);
  f.italic_spans = countRe(prose, ITALIC_RE);
  const bullets = [...raw.matchAll(BULLET_RE)];
  f.bullet_lines = bullets.length;
  const mk = (m) => bullets.filter((b) => b[2] === m).length;
  f.bullet_dash = mk("-"); f.bullet_star = mk("*"); f.bullet_plus = mk("+"); f.bullet_dot = mk("\u2022"); f.bullet_endash = mk("\u2013") + mk("\u2014");
  f.bullet_nested = bullets.filter((b) => b[1].replace(/\t/g, "    ").length >= 2).length;
  const numbered = [...raw.matchAll(NUMBERED_RE)];
  f.numbered_lines = numbered.length;
  f.numbered_paren_style = numbered.filter((n) => n[3] === ")").length;
  f.list_items_total = f.bullet_lines + f.numbered_lines;
  f.list_share_of_lines = Math.round(100 * f.list_items_total / Math.max(1, lines.filter((l) => l.trim()).length)) / 100;
  f.bold_colon_inside = countRe(raw, /^\s*(?:[-*\u2022]|\d+[.)])\s+\*\*[^*\n]{1,60}:\*\*/gm);
  f.bold_colon_outside = countRe(raw, /^\s*(?:[-*\u2022]|\d+[.)])\s+\*\*[^*\n:]{1,60}\*\*:/gm);
  f.bold_lead_in_items = countRe(raw, /^\s*(?:[-*\u2022]|\d+[.)])\s+\*\*[^*\n]{1,60}\*\*\s*[:\u2014\u2013-]/gm) + f.bold_colon_inside;
  f.table_rows = countRe(raw, TABLE_ROW_RE);
  f.has_table = TABLE_SEP_RE.test(raw) ? 1 : 0;
  f.code_fences = countRe(raw, CODE_FENCE_RE);
  f.inline_code = countRe(raw, INLINE_CODE_RE);
  f.horizontal_rules = countRe(raw, HR_RE);
  f.blockquotes = countRe(raw, BLOCKQUOTE_RE);
  f.summary_section = SUMMARY_RE.test(raw) ? 1 : 0;
  f.emoji_line_starts = countRe(raw, /^\s*[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2705}\u{274C}]/gmu);
  // sentences
  const sents = sentencesOf(prose);
  const sl = sents.map((s) => (s.match(WORD_RE) || []).length);
  f.n_sentences = sents.length;
  f.sent_len_mean = Math.round(mean(sl) * 10) / 10 || 0;
  f.sent_len_std = sl.length > 1 ? Math.round(pstdev(sl) * 10) / 10 : 0;
  f.sent_len_max = sl.length ? Math.max(...sl) : 0;
  f.share_short_sentences = sl.length ? Math.round(100 * sl.filter((n) => n <= 6).length / sl.length) / 100 : 0;
  f.share_long_sentences = sl.length ? Math.round(100 * sl.filter((n) => n >= 30).length / sl.length) / 100 : 0;
  f.type_token_ratio = nw ? Math.round(1000 * new Set(words.map((w) => w.toLowerCase())).size / nw) / 1000 : 0;
  f.avg_word_len = nw ? Math.round(100 * words.reduce((a, w) => a + w.length, 0) / nw) / 100 : 0;
  f.share_long_words = nw ? Math.round(1000 * words.filter((w) => w.length >= 9).length / nw) / 1000 : 0;
  // openers / closers
  const first = lines.find((l) => l.trim()) || "";
  f.opener = (OPENERS.find(([, re]) => re.test(first)) || ["other"])[0];
  f.first_words = first.split(/\s+/).slice(0, 8).join(" ");
  const tail = prose.slice(-400);
  for (const [name, re] of CLOSERS) f[`closer_${name}`] = re.test(tail) ? 1 : 0;
  f.last_words = prose.trim().split(/\s+/).slice(-12).join(" ");
  // rhetoric
  for (const [name, [re]] of Object.entries(RHETORIC)) { const n = countRe(prose, re); f[`rh_${name}`] = n; f[`rh_${name}_rate`] = rate(n, nw); }
  // character habits
  const u = scanUnicode(raw);
  f.em_dash_rate = rate(u.em_dash, nw); f.en_dash_rate = rate(u.en_dash, nw);
  f.spaced_em_dash = u.spaced_em_dash; f.unspaced_em_dash = u.unspaced_em_dash;
  f.spaced_hyphen_dash_rate = rate(u.spaced_hyphen_as_dash, nw); f.double_hyphen = u.double_hyphen;
  const dq = u.curly_double_quotes + u.straight_double_quotes, ap = u.curly_apostrophes + u.straight_apostrophes;
  f.curly_quote_share = dq ? Math.round(100 * u.curly_double_quotes / dq) / 100 : -1;
  f.curly_apostrophe_share = ap ? Math.round(100 * u.curly_apostrophes / ap) / 100 : -1;
  f.ellipsis_char = u.ellipsis_char; f.ellipsis_dots = u.ellipsis_dots; f.multiplication_sign = u.multiplication_sign; f.arrows = u.arrows;
  f.emoji_count = u.emoji_count; f.emoji_rate = rate(u.emoji_count, nw);
  f.narrow_nbsp = u.narrow_nbsp_count; f.nbsp = u.nbsp_count; f.zero_width = u.zero_width_count;
  f.hidden_total = u.invisible_count + u.tag_char_count + u.private_use_count;
  f.bullet_char_unicode = u.bullet_char;
  // lexicon
  for (const [fam, list] of Object.entries(LEXICON)) {
    for (const ph of list) {
      const core = ph.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/ /g, "\\s+");
      const re = new RegExp((/[a-z0-9]/i.test(ph[0]) ? "\\b" : "") + core + (/[a-z0-9]/i.test(ph[ph.length - 1]) ? "\\b" : ""), "g");
      const n = countRe(lower, re);
      if (n) f[`lex:${fam}:${ph}`] = n;
    }
  }
  return f;
}

// ------------------------------------------------------------------ 3. Hand rules (free text)
const W = (o) => o;
export function rulesScore(f, u) {
  const ev = [];
  const nw = Math.max(1, f.n_words || 1);
  const long = nw > 150;
  if (u.narrow_nbsp_count > 0) ev.push(["narrow_nbsp", `${u.narrow_nbsp_count} U+202F narrow no-break space(s): documented quirk of OpenAI o3/o4-mini/GPT-5 output`, W({ openai: 3.0, anthropic: -1, google: -1, meta: -1, xai: -0.5, deepseek: -0.5, alibaba: -0.5, mistral: -0.5, human: -1.5 })]);
  if (u.zero_width_count || u.tag_char_count || u.soft_hyphen_count || u.private_use_count) ev.push(["hidden_chars", "zero-width / tag / soft-hyphen / private-use characters present: a character-level mark (no major LLM provider documents one; a third-party tool or the pasting path is the usual source)", W({})]);
  const cas = f.curly_apostrophe_share, cqs = f.curly_quote_share;
  if (cas >= 0.6 || cqs >= 0.6) ev.push(["curly_quotes", `typographic quotes/apostrophes dominate (apostrophe share ${cas}, quote share ${cqs}): ChatGPT habit (also word processors)`, W({ openai: 1.5, anthropic: -0.8, google: -0.4, meta: -0.8, deepseek: -0.6, alibaba: -0.6, mistral: -0.6, xai: -0.3, human: 0.3 })]);
  else if (cas >= 0 && cas <= 0.2 && nw > 80) ev.push(["straight_quotes", "straight ASCII quotes/apostrophes throughout", W({ openai: -0.8, anthropic: 0.4, google: 0.3, meta: 0.3, deepseek: 0.3, alibaba: 0.3, mistral: 0.3, xai: 0.3 })]);
  const emr = f.em_dash_rate;
  if (emr >= 10) ev.push(["em_dash_heavy", `em-dash rate ${emr}/1000 words (heavy)`, W({ openai: 1.0, anthropic: 0.8, google: 0.1, xai: 0.3, meta: -0.8, deepseek: -0.3, alibaba: -0.5, mistral: -0.6, human: -0.8 })]);
  else if (emr >= 3) ev.push(["em_dash_some", `em-dash rate ${emr}/1000 words`, W({ openai: 0.4, anthropic: 0.4, google: 0.1, xai: 0.2, meta: -0.4, mistral: -0.3, human: -0.2 })]);
  else if (long) ev.push(["em_dash_none", "no em dashes in a long sample", W({ openai: -0.8, anthropic: -0.6, meta: 0.5, mistral: 0.4, alibaba: 0.3, deepseek: 0.2, google: 0.1, human: 0.5 })]);
  if (f.spaced_hyphen_dash_rate >= 3) ev.push(["spaced_hyphen_dash", "uses ' - ' spaced hyphens as dashes", W({ meta: 0.6, mistral: 0.5, alibaba: 0.4, deepseek: 0.3, google: 0.3, openai: -0.4, anthropic: -0.3, human: 0.4 })]);
  if (f.ellipsis_char > 0 && f.ellipsis_dots === 0) ev.push(["ellipsis_char", "uses the single-character ellipsis (U+2026)", W({ openai: 0.6, google: 0.2, anthropic: -0.3 })]);
  if (f.multiplication_sign > 0) ev.push(["mult_sign", "uses the U+00D7 multiplication sign", W({ openai: 0.3, google: 0.3, deepseek: 0.2, anthropic: 0.1, human: -0.3 })]);
  if (f.headers_total >= 2) {
    ev.push(["headers", `${f.headers_total} markdown headers (h2=${f.headers_h2}, h3=${f.headers_h3})`, W({ google: 0.6, openai: 0.5, anthropic: 0.4, deepseek: 0.4, alibaba: 0.4, meta: -0.2, xai: 0.1, mistral: 0.1, human: -0.8 })]);
    if (f.headers_h3 > f.headers_h2) ev.push(["h3_preference", "prefers ### headers", W({ openai: 0.5, deepseek: 0.3, alibaba: 0.3, anthropic: -0.2 })]);
    if (f.headers_h2 > f.headers_h3) ev.push(["h2_preference", "prefers ## headers", W({ anthropic: 0.4, google: 0.4, openai: -0.1 })]);
    if (f.headers_with_emoji) ev.push(["emoji_headers", "emoji in headers", W({ google: 0.8, openai: 0.6, xai: 0.6, deepseek: 0.4, anthropic: -1.0, human: -0.5 })]);
  } else if (long) ev.push(["no_headers", "no markdown headers in a long sample", W({ anthropic: 0.4, meta: 0.3, mistral: 0.3, xai: 0.3, openai: -0.2, google: -0.3, human: 0.5 })]);
  if (f.bold_whole_line >= 2) ev.push(["bold_pseudo_headers", "bold lines used as section headers", W({ openai: 0.6, meta: 0.5, google: 0.3, alibaba: 0.3, anthropic: -0.3, human: -0.5 })]);
  if (f.bold_rate >= 25) ev.push(["bold_heavy", `bold rate ${f.bold_rate}/1000 words (heavy)`, W({ google: 0.6, openai: 0.4, deepseek: 0.4, alibaba: 0.4, meta: 0.3, anthropic: -0.6, xai: 0.2, human: -0.8 })]);
  else if (f.bold_rate === 0 && long) ev.push(["no_bold", "no bold at all in a long sample", W({ anthropic: 0.6, mistral: 0.3, meta: 0.1, openai: -0.5, google: -0.6, human: 0.6 })]);
  if (f.has_table) ev.push(["table", "uses a markdown table", W({ openai: 1.0, google: 0.5, deepseek: 0.4, alibaba: 0.3, anthropic: -0.4, meta: -0.5, xai: 0.2, mistral: -0.3, human: -0.8 })]);
  if (f.bullet_lines && f.bullet_star > f.bullet_dash) ev.push(["star_bullets", "uses '*' bullets", W({ google: 1.2, meta: 0.4, mistral: 0.3, openai: -0.6, anthropic: -0.8, deepseek: -0.3 })]);
  if (f.bullet_dot) ev.push(["dot_bullets", "uses '\u2022' bullets", W({ meta: 0.5, mistral: 0.3, openai: 0.1, anthropic: -0.3, google: -0.2, human: 0.3 })]);
  if (f.numbered_paren_style) ev.push(["paren_numbering", "uses '1)' numbering", W({ meta: 0.3, mistral: 0.3, xai: 0.2, openai: -0.2, anthropic: -0.2, human: 0.3 })]);
  if (f.bold_colon_inside >= 2 && f.bold_colon_outside === 0) ev.push(["bold_colon_inside", "'**Term:** text' list items (colon inside bold)", W({ openai: 0.4, google: 0.4, deepseek: 0.3, alibaba: 0.3, anthropic: 0.1, human: -0.5 })]);
  if (f.bold_colon_outside >= 2 && f.bold_colon_inside === 0) ev.push(["bold_colon_outside", "'**Term**: text' list items (colon outside bold)", W({ anthropic: 0.5, meta: 0.3, mistral: 0.3, xai: 0.2, openai: -0.3, human: -0.3 })]);
  if (f.emoji_line_starts >= 2 || (f.emoji_rate >= 8 && f.emoji_count >= 3)) ev.push(["emoji_heavy", `emoji-heavy formatting (${f.emoji_count} emoji)`, W({ google: 0.8, openai: 0.5, xai: 0.7, deepseek: 0.6, alibaba: 0.5, anthropic: -1.2, meta: 0.2, mistral: -0.2, human: -0.3 })]);
  else if (f.emoji_count === 0 && long) ev.push(["no_emoji", "no emoji", W({ anthropic: 0.4, mistral: 0.2, meta: 0.1, google: -0.3, xai: -0.2, deepseek: -0.2, human: 0.3 })]);
  if (f.horizontal_rules >= 1) ev.push(["horizontal_rules", "uses --- horizontal rules", W({ openai: 0.7, google: 0.3, deepseek: 0.3, alibaba: 0.3, anthropic: -0.4, meta: -0.2, human: -0.5 })]);
  if (f.summary_section) ev.push(["summary_section", "ends with a summary/takeaways section", W({ google: 0.5, openai: 0.4, deepseek: 0.4, alibaba: 0.4, meta: 0.3, anthropic: -0.2, human: -0.4 })]);
  if (f.share_one_line_paragraphs >= 0.5 && f.n_paragraphs >= 6 && f.list_share_of_lines < 0.4) ev.push(["one_line_paragraphs", `${Math.round(100 * f.share_one_line_paragraphs)}% of paragraphs are single short lines (punchy GPT-5 style)`, W({ openai: 1.0, xai: 0.4, anthropic: -0.2, google: -0.3, meta: -0.4, human: -0.3 })]);
  const rh = f.rh_antithesis_not_but + f.rh_not_x_period_its_y + 2 * f.rh_tricolon_fragments + f.rh_the_catch_question + f.rh_heres_the_thing;
  if (rh >= 3) ev.push(["gpt5_rhetoric", `${rh} antithesis / tricolon / 'the catch?' / 'here's the thing' constructions`, W({ openai: 1.6, anthropic: 0.3, xai: 0.4, google: -0.3, meta: -0.6, mistral: -0.5, alibaba: -0.4, deepseek: -0.3, human: -0.8 })]);
  else if (rh >= 1) ev.push(["some_rhetoric", `${rh} antithesis / tricolon construction(s)`, W({ openai: 0.6, anthropic: 0.3, xai: 0.2, meta: -0.3, human: -0.2 })]);
  if (f.rh_sentence_initial_and_but_rate >= 8) ev.push(["conjunction_starts", "many sentences start with And/But/So", W({ openai: 0.5, xai: 0.5, anthropic: 0.3, meta: -0.3, google: -0.2, human: 0.2 })]);
  if (f.rh_think_of_it) ev.push(["think_of_it", "'think of it like' / 'imagine' analogy framing", W({ openai: 0.4, google: 0.5, xai: 0.3, anthropic: 0.1, human: -0.3 })]);
  if (f.rh_worth_noting >= 2) ev.push(["worth_noting", "'worth noting / keep in mind / that said' hedges", W({ google: 0.4, openai: 0.3, anthropic: 0.3, deepseek: 0.2, human: -0.3 })]);
  if (f.rh_bottom_line) ev.push(["bottom_line", "'bottom line / in short / key takeaway' phrasing", W({ openai: 0.4, google: 0.4, xai: 0.3, deepseek: 0.2, human: -0.3 })]);
  if (f.rh_parenthetical_rate >= 10) ev.push(["parentheticals", "frequent parenthetical asides", W({ anthropic: 0.4, openai: 0.2, xai: 0.2, google: -0.2, human: 0.3 })]);
  if (f.rh_contractions_rate >= 25) ev.push(["contractions", "contraction-heavy, conversational register", W({ openai: 0.3, anthropic: 0.4, xai: 0.5, meta: -0.2, deepseek: -0.4, alibaba: -0.5, mistral: -0.3, human: 0.3 })]);
  else if (f.rh_contractions_rate <= 5 && long) ev.push(["no_contractions", "formal register, almost no contractions", W({ deepseek: 0.5, alibaba: 0.5, mistral: 0.3, google: 0.2, meta: 0.2, openai: -0.3, anthropic: -0.4, xai: -0.5 })]);
  if (f.rh_exclamations_rate >= 8) ev.push(["exclamations", "exclamation-heavy", W({ google: 0.4, meta: 0.5, xai: 0.5, alibaba: 0.4, deepseek: 0.4, openai: 0.1, anthropic: -0.5, human: 0.2 })]);
  const openerW = {
    certainly: { openai: 0.5, alibaba: 1.2, deepseek: 1.2, google: 0.5, anthropic: -1.0, xai: -0.5, human: -1.0 }, sure: { openai: 0.5, mistral: 0.6, alibaba: 0.5, deepseek: 0.4, google: 0.3, anthropic: -0.3, human: -0.5 },
    absolutely: { openai: 0.6, google: 0.8, xai: 0.3, anthropic: -0.3, human: -0.5 }, of_course: { google: 0.7, mistral: 0.5, alibaba: 0.5, anthropic: -0.3, human: -0.5 },
    great_question: { google: 0.6, openai: 0.5, meta: 0.4, anthropic: -0.4, human: -0.8 }, heres: { anthropic: 0.4, openai: 0.4, google: 0.3, deepseek: 0.2, human: -0.5 },
    happy_to: { anthropic: 0.6, meta: 0.6, alibaba: 0.3, human: -0.6 }, okay_alright: { xai: 1.0, meta: 0.3, openai: 0.2 }, lets: { xai: 0.5, openai: 0.4, google: 0.4, human: -0.2 },
    youre_right: { anthropic: 1.0, human: -0.5 }, greeting: { meta: 0.5, alibaba: 0.3, google: 0.3, human: 0.2 }, title_or_header: { google: 0.5, openai: 0.4, deepseek: 0.4, alibaba: 0.3, anthropic: 0.2, human: -0.5 }, direct: { anthropic: 0.2, openai: 0.1, mistral: 0.1, human: 0.3 },
  };
  if (openerW[f.opener]) ev.push(["opener", `opens with '${f.first_words}' (${f.opener})`, W(openerW[f.opener])]);
  if (f.closer_offer_would_you_like || f.closer_offer_want_me_to) ev.push(["closer_offer", `ends with an offer to do more: '...${f.last_words}'`, W({ openai: 1.6, google: 0.4, anthropic: 0.2, xai: 0.2, meta: -0.6, mistral: -0.4, deepseek: -0.2, alibaba: -0.2, human: -1.5 })]);
  if (f.closer_let_me_know || f.closer_hope_this_helps || f.closer_any_other_questions || f.closer_feel_free) ev.push(["closer_assistant", `ends with 'let me know / hope this helps / feel free': '...${f.last_words}'`, W({ meta: 1.2, alibaba: 0.9, deepseek: 0.9, mistral: 0.7, google: 0.4, xai: 0.3, openai: -0.3, anthropic: -0.3, human: -1.0 })]);
  if (f.closer_emoji_signoff) ev.push(["emoji_signoff", "signs off with an emoji", W({ deepseek: 1.5, alibaba: 1.2, google: 0.4, xai: 0.4, openai: -0.3, anthropic: -1.2, human: 0 })]);
  if (f.closer_ends_with_question && !(f.closer_offer_would_you_like || f.closer_offer_want_me_to)) ev.push(["ends_question", "ends with a question", W({ openai: 0.4, xai: 0.4, google: 0.3, anthropic: 0.2 })]);
  const lex = {};
  for (const [k, v] of Object.entries(f)) if (k.startsWith("lex:")) { const [, fam, ph] = k.split(":"); (lex[fam] ||= []).push(v > 1 ? `${ph}\u00D7${v}` : ph); }
  for (const [fam, hits] of Object.entries(lex)) ev.push([`lexicon:${fam}`, "phrases: " + hits.slice(0, 8).join(", "), W({ [fam]: Math.min(1.5, 0.3 * hits.length), human: -Math.min(0.6, 0.1 * hits.length) })]);
  if (nw >= 700) ev.push(["very_long", `${nw} words`, W({ google: 0.4, openai: 0.3, deepseek: 0.3, alibaba: 0.3, anthropic: -0.2 })]);
  // LLM-ness aggregate: very low tell count on a long plain text favours "human"
  const tells = ev.filter(([id]) => !["straight_quotes", "em_dash_none", "no_headers", "no_bold", "no_emoji", "hidden_chars", "spaced_hyphen_dash", "dot_bullets", "paren_numbering", "parentheticals", "contractions", "conjunction_starts"].includes(id)).length;
  if (long && tells === 0) ev.push(["no_ai_tells", "long text with none of the usual assistant tells", W({ human: 1.5, openai: -0.4, google: -0.4, anthropic: -0.2 })]);
  if (/\b(?:teh|recieve|definately|alot|seperate|occured|wich|becuase)\b/i.test(f.first_words + " " + f.last_words) || (f.n_words > 60 && /\b[a-z]+\b\s{2,}[a-z]/.test("")))
    ev.push(["typos", "common human misspellings", W({ human: 1.0 })]);
  const scores = Object.fromEntries(FAMILY_IDS.map((k) => [k, 0]));
  for (const [, , w] of ev) for (const [k, v] of Object.entries(w)) if (k in scores) scores[k] += v;
  return { scores, evidence: ev.map(([rule, detail, weights]) => ({ rule, detail, weights })), tells };
}

// ------------------------------------------------------------------ 4. Token bag + naive Bayes
const bucket = (x, edges) => { let i = 0; while (i < edges.length && x >= edges[i]) i++; return i; };
// Function words carry style, not topic; used by the "style" tokenizer mode.
export const FUNCTION_WORDS = new Set(("a an the and or but so yet nor for of to in on at by with from into onto over under about above below between through during before after " +
  "is are was were be been being am do does did done have has had having will would can could should may might must shall ought " +
  "i me my mine we us our ours you your yours he him his she her hers it its they them their theirs this that these those who whom whose which what where when why how " +
  "not no yes if then than as because while although though whether either neither both each every all any some few many much more most less least very really quite rather just only even also too " +
  "here there now then once again still already ever never always often sometimes usually generally actually basically essentially simply literally honestly genuinely probably likely maybe perhaps " +
  "first second next last finally overall however therefore thus hence otherwise instead meanwhile anyway besides moreover furthermore additionally plus " +
  "one two three four five ten few lot lots bit little big small good bad best worst better worse great real sure okay ok right well like get got make made go going want need think know say said let " +
  "it's that's there's here's i'm i'd i'll i've you're you'll you've we're they're isn't aren't wasn't weren't don't doesn't didn't won't wouldn't can't couldn't shouldn't haven't hasn't hadn't " +
  "something anything nothing everything someone anyone everyone thing things way ways kind sort stuff").split(/\s+/));
export function tokenize(text, f, { mode = "all" } = {}) {
  f = f || extractFeatures(text);
  const bag = new Map();
  const add = (t, n = 1) => bag.set(t, (bag.get(t) || 0) + n);
  const prose = stripCode(text).toLowerCase().replace(/[\u2019\u2018]/g, "'");
  const words = prose.match(/[a-z][a-z']*/g) || [];
  if (mode === "all") {
    for (let i = 0; i < words.length; i++) { add(words[i]); if (i + 1 < words.length) add(words[i] + "_" + words[i + 1]); }
  } else if (mode === "style") {
    // function-word unigrams and bigrams only (topic words replaced by a placeholder in bigrams)
    const fw = words.map((w) => (FUNCTION_WORDS.has(w) ? w : "_"));
    for (let i = 0; i < fw.length; i++) { if (fw[i] !== "_") add(fw[i]); if (i + 1 < fw.length && (fw[i] !== "_" || fw[i + 1] !== "_")) add(fw[i] + "_" + fw[i + 1]); }
  }
  const S = 2; // style tokens weigh double
  const style = {
    "§h1": f.headers_h1, "§h2": f.headers_h2, "§h3": f.headers_h3, "§bold": f.bold_spans, "§bold_line": f.bold_whole_line, "§italic": f.italic_spans,
    "§bullet_dash": f.bullet_dash, "§bullet_star": f.bullet_star, "§bullet_dot": f.bullet_dot, "§numbered": f.numbered_lines, "§numbered_paren": f.numbered_paren_style,
    "§bold_colon_in": f.bold_colon_inside, "§bold_colon_out": f.bold_colon_outside, "§table_row": f.table_rows, "§hr": f.horizontal_rules, "§code_fence": f.code_fences,
    "§inline_code": f.inline_code, "§blockquote": f.blockquotes, "§emoji": f.emoji_count, "§emoji_line": f.emoji_line_starts, "§emdash_spaced": f.spaced_em_dash,
    "§emdash_unspaced": f.unspaced_em_dash, "§endash": Math.round(f.en_dash_rate), "§spaced_hyphen": Math.round(f.spaced_hyphen_dash_rate), "§ellipsis_char": f.ellipsis_char,
    "§ellipsis_dots": f.ellipsis_dots, "§mult": f.multiplication_sign, "§arrow": f.arrows, "§nnbsp": f.narrow_nbsp, "§nbsp": f.nbsp, "§zw": f.zero_width, "§paren": f.rh_parenthetical,
    "§semicolon": f.rh_semicolons, "§exclaim": f.rh_exclamations, "§question": f.rh_questions, "§antithesis": f.rh_antithesis_not_but, "§not_x_its_y": f.rh_not_x_period_its_y,
    "§tricolon": f.rh_tricolon_fragments, "§catch_q": f.rh_the_catch_question, "§heres_thing": f.rh_heres_the_thing, "§think_of_it": f.rh_think_of_it, "§bottom_line": f.rh_bottom_line,
    "§worth_noting": f.rh_worth_noting, "§dash_aside": f.rh_dash_aside, "§conj_start": f.rh_sentence_initial_and_but, "§one_word_sent": f.rh_one_word_sentence,
    "§curly_dquote": f.curly_quote_share > 0.5 ? 1 : 0, "§straight_dquote": f.curly_quote_share >= 0 && f.curly_quote_share <= 0.5 ? 1 : 0,
    "§curly_apos": f.curly_apostrophe_share > 0.5 ? 1 : 0, "§straight_apos": f.curly_apostrophe_share >= 0 && f.curly_apostrophe_share <= 0.5 ? 1 : 0,
    "§summary_section": f.summary_section, "§has_table": f.has_table,
  };
  for (const [t, n] of Object.entries(style)) if (n > 0) add(t, Math.min(n, 12) * S);
  add(`§opener_${f.opener}`, S);
  for (const [name] of CLOSERS) if (f[`closer_${name}`]) add(`§closer_${name}`, S);
  add(`§len_${bucket(f.n_words, [80, 200, 400, 800])}`, S);
  add(`§sentlen_${bucket(f.sent_len_mean, [10, 15, 20, 26])}`, S);
  add(`§short_sent_${bucket(f.share_short_sentences, [0.1, 0.25, 0.4])}`, S);
  add(`§list_share_${bucket(f.list_share_of_lines, [0.1, 0.3, 0.6])}`, S);
  add(`§oneliners_${bucket(f.share_one_line_paragraphs, [0.2, 0.5, 0.8])}`, S);
  add(`§contr_${bucket(f.rh_contractions_rate, [5, 15, 30])}`, S);
  add(`§ttr_${bucket(f.type_token_ratio, [0.45, 0.55, 0.65])}`, S);
  return bag;
}

export function trainNB(samples, { minDf = 1, level = "family" } = {}) {
  const classes = {};
  const df = new Map();
  const bg = {};
  for (const s of samples) {
    const label = level === "model" ? s.model : s.family;
    if (!label) continue;
    const bag = s.bag || tokenize(s.text);
    const c = (classes[label] ||= { docs: 0, total: 0, counts: {} });
    c.docs++;
    for (const [t, n] of bag) { c.counts[t] = (c.counts[t] || 0) + n; c.total += n; df.set(t, (df.get(t) || 0) + 1); bg[t] = (bg[t] || 0) + n; }
  }
  const vocab = [...df.entries()].filter(([, d]) => d >= minDf).map(([t]) => t).sort();
  const vset = new Set(vocab);
  for (const c of Object.values(classes)) { c.total = 0; for (const t of Object.keys(c.counts)) { if (!vset.has(t)) delete c.counts[t]; else c.total += c.counts[t]; } }
  let bgTotal = 0;
  for (const t of Object.keys(bg)) { if (!vset.has(t)) delete bg[t]; else bgTotal += bg[t]; }
  return { level, vocab_size: vocab.length, n_docs: samples.length, alpha: 0.5, lambda: 0.3, classes, background: { counts: bg, total: bgTotal } };
}

export function nbScore(bag, model, { temperature = null } = {}) {
  if (!model || !model.classes || !Object.keys(model.classes).length) return null;
  const V = Math.max(1, model.vocab_size), a = model.alpha ?? 0.5, lam = model.lambda ?? 0.3;
  const names = Object.keys(model.classes);
  const totalDocs = names.reduce((s, k) => s + model.classes[k].docs, 0);
  const bg = model.background || { counts: {}, total: 0 };
  // Jelinek-Mercer smoothing against the corpus background: tokens unseen in a class fall back
  // to the same background probability for every class, so class size does not bias the score.
  const pbg = (t) => ((bg.counts[t] || 0) + a) / (bg.total + a * V);
  const ll = {}, contrib = {};
  let nTok = 0;
  for (const [, n] of bag) nTok += n;
  for (const k of names) {
    const c = model.classes[k];
    let s = Math.log(c.docs / totalDocs);
    const parts = [];
    for (const [t, n] of bag) {
      const pc = c.total ? (c.counts[t] || 0) / c.total : 0;
      const lp = Math.log((1 - lam) * pc + lam * pbg(t));
      s += n * lp; parts.push([t, n * lp, n]);
    }
    ll[k] = s; contrib[k] = parts;
  }
  const tau = temperature ?? Math.min(1, 120 / Math.max(1, nTok));
  const best = Math.max(...Object.values(ll));
  const logodds = Object.fromEntries(names.map((k) => [k, (ll[k] - best) * tau]));
  return { logodds, raw: ll, n_tokens: nTok, tau, contrib, docs: Object.fromEntries(names.map((k) => [k, model.classes[k].docs])) };
}

export function topTokens(nb, a, b, k = 12) {
  // tokens that most favour class a over class b (sum over occurrences)
  if (!nb || !nb.contrib[a] || !nb.contrib[b]) return [];
  const mb = new Map(nb.contrib[b].map(([t, v]) => [t, v]));
  return nb.contrib[a].map(([t, v, n]) => [t, v - (mb.get(t) || 0), n]).sort((x, y) => y[1] - x[1]).slice(0, k).map(([t, d, n]) => ({ token: t, delta: Math.round(d * 100) / 100, n }));
}

export function softmax(scores) {
  const mx = Math.max(...Object.values(scores));
  const ex = Object.fromEntries(Object.entries(scores).map(([k, v]) => [k, Math.exp(v - mx)]));
  const z = Object.values(ex).reduce((a, b) => a + b, 0);
  return Object.fromEntries(Object.entries(ex).map(([k, v]) => [k, v / z]));
}

// ------------------------------------------------------------------ 5. Full analysis
export function analyze(text, model) {
  const u = scanUnicode(text);
  const findings = unicodeFindings(u);
  const hidden = decodeHidden(text);
  const f = extractFeatures(text);
  const rules = rulesScore(f, u);
  const bag = tokenize(text, f, { mode: (model && model.features) || "all" });
  const fam = model && model.family ? nbScore(bag, model.family) : null;
  const combined = {};
  for (const k of FAMILY_IDS) combined[k] = FAMILIES[k].prior + rules.scores[k];
  let nbWeight = 0;
  if (fam) {
    const present = Object.keys(fam.logodds);
    const neutral = present.reduce((s, k) => s + fam.logodds[k], 0) / present.length;
    const minDocs = Math.min(...present.map((k) => fam.docs[k]));
    nbWeight = Math.min(1.0, Math.max(0, (minDocs - 1) / 4)); // 0 with 1 doc/class, full at 5+ docs/class
    for (const k of FAMILY_IDS) combined[k] += nbWeight * (k in fam.logodds ? fam.logodds[k] : neutral);
  }
  const probs = softmax(combined);
  const ranked = [...FAMILY_IDS].sort((a, b) => combined[b] - combined[a]);
  const top = ranked[0], second = ranked[1];
  const margin = combined[top] - combined[second];
  const shortText = f.n_words < 40;
  const confidence = shortText ? "low" : probs[top] >= 0.85 && margin >= 2.5 ? "high" : probs[top] >= 0.6 ? "medium" : "low";
  // model-level refinement inside the top family
  let modelLevel = null;
  if (model && model.models) {
    const sub = { ...model.models, classes: Object.fromEntries(Object.entries(model.models.classes).filter(([, c]) => c.family === top)) };
    if (Object.keys(sub.classes).length >= 2) {
      const ms = nbScore(bag, sub);
      const p = softmax(ms.logodds);
      modelLevel = Object.entries(p).sort((a, b) => b[1] - a[1]).map(([name, pr]) => ({ model: name, p: Math.round(pr * 1000) / 1000, docs: ms.docs[name] }));
    } else if (Object.keys(sub.classes).length === 1) modelLevel = [{ model: Object.keys(sub.classes)[0], p: null, docs: Object.values(sub.classes)[0].docs, note: "only reference model for this family" }];
  }
  const strength = Math.min(1, (rules.tells + (fam ? Math.min(3, Math.abs(fam.logodds[second] || 0)) : 0)) / 8);
  return {
    text_stats: { chars: f.n_chars, words: f.n_words, sentences: f.n_sentences },
    unicode: u, findings, hidden, features: f, rules, nb: fam, nb_weight: nbWeight, combined, probs, ranked, top, second, margin: Math.round(margin * 100) / 100,
    confidence, fingerprint_strength: Math.round(strength * 100) / 100, model_level: modelLevel,
    top_tokens: fam ? topTokens(fam, top, second) : [],
  };
}
