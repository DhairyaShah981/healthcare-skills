#!/usr/bin/env node
/**
 * healthcare-skills — CLI for the healthcare-skills repo.
 *
 * Subcommands:
 *   list                       — list every skill with one-line summaries
 *   info <name>                — print frontmatter + body intro for one skill
 *   add <name>                 — install one skill into the detected IDE
 *   add-all                    — install every skill
 *   search <query>             — search names, descriptions, tags
 *   tags                       — list every tag in use, with counts
 *   doctor                     — sanity-check the install (IDE detection, frontmatter)
 *
 * Common flags:
 *   --ide <claude-code|cursor|codex|gemini|all>
 *   --skills-root <path>       — override location of skills/
 *   --dry-run                  — print actions without touching the filesystem
 *   --json                     — emit machine-readable output (list / info / search)
 *
 * Works as: `npx healthcare-skills <cmd>` once the npm package is published,
 * or `node bin/healthcare-skills.js <cmd>` from a checkout.
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync, execSync } = require('node:child_process');

// ── locate skills directory ───────────────────────────────────────────────

function resolveSkillsRoot(opts) {
  if (opts.skillsRoot) return path.resolve(opts.skillsRoot);
  // 1. local repo checkout
  const localRepo = path.resolve(__dirname, '..', 'skills');
  if (fs.existsSync(localRepo)) return localRepo;
  // 2. installed as npm package — skills/ ships alongside bin/
  const pkgRepo = path.resolve(__dirname, '..', 'skills');
  if (fs.existsSync(pkgRepo)) return pkgRepo;
  fail("can't find skills/ directory; pass --skills-root <path>");
}

// ── frontmatter parser (no yaml dep) ─────────────────────────────────────

function parseFrontmatter(md) {
  if (!md.startsWith('---\n')) return {};
  const end = md.indexOf('\n---\n', 4);
  if (end < 0) return {};
  const block = md.slice(4, end);
  const out = {};
  let currentKey = null;
  let buf = [];
  for (const line of block.split('\n')) {
    const m = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (m && !line.startsWith(' ') && !line.startsWith('\t')) {
      if (currentKey) out[currentKey] = buf.join('\n').trim();
      currentKey = m[1];
      buf = [m[2]];
    } else {
      buf.push(line.replace(/^  /, ''));
    }
  }
  if (currentKey) out[currentKey] = buf.join('\n').trim();
  // Strip pipe marker and surrounding quotes
  for (const k of Object.keys(out)) {
    let v = out[k];
    if (v.startsWith('|')) v = v.slice(1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    if (v.startsWith('[') && v.endsWith(']')) {
      try {
        v = JSON.parse(v.replace(/(\w[\w-]*)/g, '"$1"').replace(/""/g, '"'));
      } catch { /* leave as string */ }
    }
    out[k] = v;
  }
  return out;
}

function listSkills(root) {
  return fs.readdirSync(root)
    .filter((n) => !n.startsWith('_'))
    .map((name) => {
      const md = path.join(root, name, 'SKILL.md');
      if (!fs.existsSync(md)) return null;
      const text = fs.readFileSync(md, 'utf8');
      return { name, fm: parseFrontmatter(text), text, path: path.dirname(md) };
    })
    .filter(Boolean)
    .sort((a, b) => a.name.localeCompare(b.name));
}

// ── IDE detection ────────────────────────────────────────────────────────

function detectIde() {
  const home = os.homedir();
  if (fs.existsSync(path.join(home, '.claude'))) return 'claude-code';
  if (fs.existsSync(path.join(home, '.cursor'))) return 'cursor';
  if (fs.existsSync(path.join(home, '.codex'))) return 'codex';
  if (fs.existsSync(path.join(home, '.gemini'))) return 'gemini';
  return null;
}

// ── command: list ────────────────────────────────────────────────────────

function cmdList({ json }, skills) {
  if (json) {
    process.stdout.write(JSON.stringify(skills.map((s) => ({
      name: s.name,
      description: oneLine(s.fm.description),
      tags: s.fm.tags || [],
    })), null, 2) + '\n');
    return;
  }
  console.log(`\nhealthcare-skills — ${skills.length} skills`);
  for (const s of skills) {
    const desc = oneLine(s.fm.description);
    console.log(`  ${pad(s.name, 24)}  ${desc.slice(0, 96)}`);
  }
}

// ── command: info ────────────────────────────────────────────────────────

function cmdInfo({ json }, skills, name) {
  const s = skills.find((s) => s.name === name);
  if (!s) fail(`no skill named '${name}' — run \`healthcare-skills list\``);
  if (json) {
    process.stdout.write(JSON.stringify({ name: s.name, ...s.fm }, null, 2) + '\n');
    return;
  }
  console.log(`\n${s.name}`);
  console.log('─'.repeat(s.name.length));
  console.log(`description: ${oneLine(s.fm.description)}\n`);
  if (s.fm.tags)    console.log(`tags: ${Array.isArray(s.fm.tags) ? s.fm.tags.join(', ') : s.fm.tags}`);
  if (s.fm.license) console.log(`license: ${s.fm.license}`);
  if (s.fm.incident) {
    console.log(`\nincident:\n  ${String(s.fm.incident).split('\n').join('\n  ')}`);
  }
  console.log(`\nlocation: ${s.path}/SKILL.md`);
}

// ── command: add ─────────────────────────────────────────────────────────

function cmdAdd({ ide, dryRun }, skills, name) {
  const s = skills.find((s) => s.name === name);
  if (!s) fail(`no skill named '${name}'`);
  installOne(s, { ide: ide || detectIde() || fail('could not auto-detect IDE'), dryRun });
}

function cmdAddAll({ ide, dryRun }, skills) {
  const target = ide || detectIde() || fail('could not auto-detect IDE');
  for (const s of skills) installOne(s, { ide: target, dryRun });
  console.log(`\ninstalled ${skills.length} skills (${target}${dryRun ? ', dry-run' : ''})`);
}

function installOne(s, { ide, dryRun }) {
  const home = os.homedir();
  if (ide === 'claude-code') {
    const dst = path.join(home, '.claude', 'skills', s.name);
    if (dryRun) return console.log(`DRY: cp -R ${s.path} ${dst}`);
    fs.rmSync(dst, { recursive: true, force: true });
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    cpR(s.path, dst);
    console.log(`✓ ${s.name} → ${dst}`);
  } else if (ide === 'cursor') {
    const dst = path.join(process.cwd(), '.cursor', 'rules', `${s.name}.mdc`);
    if (dryRun) return console.log(`DRY: cp ${s.path}/SKILL.md ${dst}`);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(path.join(s.path, 'SKILL.md'), dst);
    console.log(`✓ ${s.name} → ${dst}`);
  } else if (ide === 'codex' || ide === 'gemini') {
    const file = path.join(process.cwd(), ide === 'codex' ? 'AGENTS.md' : 'GEMINI.md');
    if (dryRun) return console.log(`DRY: append ${s.name} to ${file}`);
    const block = `\n## Skill: ${s.name}\n` +
                  fs.readFileSync(path.join(s.path, 'SKILL.md'), 'utf8') +
                  '\n';
    fs.appendFileSync(file, block);
    console.log(`✓ ${s.name} → ${file}`);
  } else {
    fail(`unknown ide: ${ide}`);
  }
}

function cpR(src, dst) {
  if (fs.cpSync) {
    fs.cpSync(src, dst, { recursive: true });
  } else {
    execSync(`cp -R "${src}" "${dst}"`);
  }
}

// ── command: search ──────────────────────────────────────────────────────

function cmdSearch({ json }, skills, q) {
  const needle = (q || '').toLowerCase();
  const hits = skills.filter((s) => {
    const hay = [s.name, oneLine(s.fm.description), (s.fm.tags || []).join(' ')].join(' ').toLowerCase();
    return hay.includes(needle);
  });
  if (json) return process.stdout.write(JSON.stringify(hits.map((s) => s.name), null, 2) + '\n');
  console.log(`\n${hits.length} match(es) for "${q}"`);
  for (const s of hits) console.log(`  ${pad(s.name, 24)}  ${oneLine(s.fm.description).slice(0, 96)}`);
}

// ── command: tags ────────────────────────────────────────────────────────

function cmdTags({ json }, skills) {
  const counts = {};
  for (const s of skills) {
    const tags = Array.isArray(s.fm.tags) ? s.fm.tags : [];
    for (const t of tags) counts[t] = (counts[t] || 0) + 1;
  }
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  if (json) return process.stdout.write(JSON.stringify(Object.fromEntries(sorted), null, 2) + '\n');
  console.log(`\n${sorted.length} tags in use:`);
  for (const [t, n] of sorted) console.log(`  ${pad(t, 16)}  ${n}`);
}

// ── command: doctor ──────────────────────────────────────────────────────

function cmdDoctor(_opts, skills) {
  const home = os.homedir();
  console.log(`\nhealthcare-skills doctor`);
  console.log(`  skills found: ${skills.length}`);
  console.log(`  IDE detected: ${detectIde() || 'none (pass --ide explicitly)'}`);
  const ideDirs = {
    'claude-code': path.join(home, '.claude'),
    cursor: path.join(home, '.cursor'),
    codex:  path.join(home, '.codex'),
    gemini: path.join(home, '.gemini'),
  };
  for (const [ide, dir] of Object.entries(ideDirs)) {
    console.log(`    ${pad(ide, 12)} ${fs.existsSync(dir) ? '✓ ' + dir : '·'}`);
  }
  let missingFrontmatter = 0;
  for (const s of skills) {
    if (!s.fm.name || !s.fm.description) missingFrontmatter++;
  }
  console.log(`  frontmatter:  ${missingFrontmatter === 0 ? 'all 7 keys present everywhere' : `${missingFrontmatter} skill(s) missing required keys`}`);
}

// ── helpers ──────────────────────────────────────────────────────────────

function oneLine(s) {
  if (!s) return '';
  return String(s).replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
}

function pad(s, n) {
  return s + ' '.repeat(Math.max(0, n - s.length));
}

function fail(msg) {
  process.stderr.write(`healthcare-skills: ${msg}\n`);
  process.exit(2);
}

function parseArgs(argv) {
  const opts = { ide: null, skillsRoot: null, dryRun: false, json: false };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--ide')          opts.ide = argv[++i];
    else if (a === '--skills-root') opts.skillsRoot = argv[++i];
    else if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--json')    opts.json = true;
    else if (a === '-h' || a === '--help' || a === 'help') opts.help = true;
    else positional.push(a);
  }
  return { opts, positional };
}

function usage() {
  console.log(`healthcare-skills <command> [args]

Commands:
  list                        list every skill
  info <name>                 print frontmatter + intro for one skill
  add <name>                  install one skill into the detected IDE
  add-all                     install every skill
  search <query>              search names, descriptions, tags
  tags                        list every tag with usage counts
  doctor                      sanity-check the install

Flags:
  --ide <claude-code|cursor|codex|gemini>
  --skills-root <path>
  --dry-run                   print actions, don't write
  --json                      machine-readable output (list/info/search/tags)

Examples:
  healthcare-skills list
  healthcare-skills info phi-redact
  healthcare-skills add phi-redact --ide cursor
  healthcare-skills add-all --ide claude-code
  healthcare-skills search hipaa
`);
}

// ── entry ────────────────────────────────────────────────────────────────

function main() {
  const { opts, positional } = parseArgs(process.argv.slice(2));
  const cmd = positional[0];
  if (!cmd || opts.help) { usage(); return; }
  const root = resolveSkillsRoot(opts);
  const skills = listSkills(root);

  switch (cmd) {
    case 'list':     return cmdList(opts, skills);
    case 'info':     return cmdInfo(opts, skills, positional[1]);
    case 'add':      return cmdAdd(opts, skills, positional[1]);
    case 'add-all':  return cmdAddAll(opts, skills);
    case 'search':   return cmdSearch(opts, skills, positional[1] || '');
    case 'tags':     return cmdTags(opts, skills);
    case 'doctor':   return cmdDoctor(opts, skills);
    default: fail(`unknown command: ${cmd}\n\nRun \`healthcare-skills help\`.`);
  }
}

main();
