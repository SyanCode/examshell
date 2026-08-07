// Port of examshell/compiler.py's forbidden-function grep: strip comments and
// string/char literals, then look for calls to blacklisted libc functions
// that the exercise doesn't explicitly allow.

export const BLACKLIST = [
  "printf", "fprintf", "sprintf", "snprintf", "vprintf",
  "puts", "putchar", "putc", "fputs", "fputc",
  "malloc", "calloc", "realloc", "free",
  "strlen", "strcpy", "strncpy", "strcat", "strncat",
  "strcmp", "strncmp", "strdup", "strchr", "strrchr", "strstr",
  "memcpy", "memmove", "memset", "memcmp",
  "atoi", "atol", "exit", "abort", "system",
];

export function stripCommentsAndStrings(src) {
  let out = "";
  let i = 0;
  const n = src.length;
  while (i < n) {
    const two = src.slice(i, i + 2);
    if (two === "/*") {
      const end = src.indexOf("*/", i + 2);
      i = end === -1 ? n : end + 2;
      continue;
    }
    if (two === "//") {
      const end = src.indexOf("\n", i + 2);
      i = end === -1 ? n : end;
      continue;
    }
    const c = src[i];
    if (c === '"') {
      let j = i + 1;
      while (j < n && src[j] !== '"') {
        if (src[j] === "\\") j += 1;
        j += 1;
      }
      i = j + 1;
      continue;
    }
    if (c === "'") {
      let j = i + 1;
      while (j < n && src[j] !== "'") {
        if (src[j] === "\\") j += 1;
        j += 1;
      }
      i = j + 1;
      continue;
    }
    out += c;
    i += 1;
  }
  return out;
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function findForbiddenCalls(source, allowedFunctions) {
  const cleaned = stripCommentsAndStrings(source);
  const allowed = new Set(allowedFunctions || []);
  const banned = BLACKLIST.filter((f) => !allowed.has(f));
  const hits = [];
  for (const func of banned) {
    const re = new RegExp(`\\b${escapeRegExp(func)}\\s*\\(`);
    if (re.test(cleaned)) hits.push(func);
  }
  return hits;
}
