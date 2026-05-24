(() => {
  'use strict';

  const qInput = document.getElementById('q');
  const tagBar = document.getElementById('tag-bar');
  const listEl = document.getElementById('skills');
  const statusEl = document.getElementById('status');
  const resetBtn = document.getElementById('reset');
  const countEl = document.getElementById('count');

  let SKILLS = [];
  let activeTags = new Set();
  let activeQuery = '';

  fetch('skills.json')
    .then((r) => r.json())
    .then((data) => {
      SKILLS = data.skills;
      countEl.textContent = SKILLS.length.toString();
      document.title = `healthcare-skills — ${SKILLS.length} skills for healthcare engineering`;
      buildTagBar();
      render();
    })
    .catch((err) => {
      statusEl.textContent = 'Failed to load skills.json: ' + err.message;
    });

  function buildTagBar() {
    const counts = {};
    for (const s of SKILLS) for (const t of (s.tags || [])) counts[t] = (counts[t] || 0) + 1;
    const top = Object.entries(counts)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 14);
    for (const [tag, n] of top) {
      const btn = document.createElement('button');
      btn.className = 'tag-pill';
      btn.type = 'button';
      btn.dataset.tag = tag;
      btn.textContent = `${tag} (${n})`;
      btn.addEventListener('click', () => {
        if (activeTags.has(tag)) activeTags.delete(tag);
        else activeTags.add(tag);
        btn.classList.toggle('active');
        resetBtn.hidden = !(activeTags.size || activeQuery);
        render();
      });
      tagBar.appendChild(btn);
    }
  }

  qInput.addEventListener('input', (e) => {
    activeQuery = e.target.value.trim().toLowerCase();
    resetBtn.hidden = !(activeTags.size || activeQuery);
    render();
  });

  resetBtn.addEventListener('click', () => {
    activeQuery = '';
    activeTags.clear();
    qInput.value = '';
    for (const el of tagBar.querySelectorAll('.tag-pill.active')) el.classList.remove('active');
    resetBtn.hidden = true;
    render();
  });

  function matches(s) {
    if (activeTags.size && !s.tags.some((t) => activeTags.has(t))) return false;
    if (activeQuery) {
      const hay = (s.name + ' ' + s.description + ' ' + (s.incident || '') + ' ' + s.tags.join(' ')).toLowerCase();
      if (!hay.includes(activeQuery)) return false;
    }
    return true;
  }

  function render() {
    const filtered = SKILLS.filter(matches);
    filtered.sort((a, b) => a.tier - b.tier || a.name.localeCompare(b.name));

    statusEl.textContent = filtered.length === SKILLS.length
      ? `Showing all ${SKILLS.length} skills.`
      : `Showing ${filtered.length} of ${SKILLS.length} skills.`;

    listEl.innerHTML = '';
    for (const s of filtered) listEl.appendChild(card(s));
  }

  function card(s) {
    const li = document.createElement('li');
    li.className = 'card';
    li.dataset.skill = s.name;

    const head = document.createElement('div');
    head.className = 'card-head';

    const name = document.createElement('div');
    name.className = 'card-name';
    const a = document.createElement('a');
    a.href = s.github_url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = s.name;
    name.appendChild(a);

    const tier = document.createElement('span');
    tier.className = 'tier-pill tier-' + s.tier;
    tier.textContent = 'tier ' + s.tier;

    head.appendChild(name);
    head.appendChild(tier);

    if (s.has_script) {
      const flag = document.createElement('span');
      flag.className = 'has-flag';
      flag.textContent = 'py';
      flag.title = 'has runnable Python helper';
      head.appendChild(flag);
    }
    if (s.has_typescript) {
      const flag = document.createElement('span');
      flag.className = 'has-flag';
      flag.textContent = 'ts';
      flag.title = 'has TypeScript reference impl';
      head.appendChild(flag);
    }

    const desc = document.createElement('p');
    desc.className = 'card-desc';
    desc.textContent = s.description;

    li.appendChild(head);
    li.appendChild(desc);

    if (s.incident) {
      const inc = document.createElement('p');
      inc.className = 'card-incident';
      inc.textContent = s.incident;
      li.appendChild(inc);
    }

    if (s.tags && s.tags.length) {
      const tags = document.createElement('div');
      tags.className = 'card-tags';
      for (const t of s.tags) {
        const tag = document.createElement('span');
        tag.className = 'card-tag';
        tag.textContent = t;
        tags.appendChild(tag);
      }
      li.appendChild(tags);
    }

    return li;
  }
})();
