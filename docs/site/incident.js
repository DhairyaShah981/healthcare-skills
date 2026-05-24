(() => {
  'use strict';

  const params = new URLSearchParams(window.location.search);
  const skillName = params.get('skill') || '';

  const $ = (id) => document.getElementById(id);

  fetch('skills.json')
    .then((r) => r.json())
    .then((data) => {
      const s = data.skills.find((x) => x.name === skillName);
      if (!s) {
        document.title = 'Skill not found — healthcare-skills';
        $('title').textContent = 'Skill not found';
        $('desc').textContent = '';
        $('not-found-section').hidden = false;
        $('incident').remove();
        for (const id of ['github-link', 'install-cmd']) $(id).remove();
        return;
      }
      document.title = `${s.name} — incident — healthcare-skills`;
      $('title').textContent = s.name;
      $('desc').textContent = s.description;
      $('incident').textContent = s.incident_full || '(no incident recorded)';

      const wt = $('when-to-use');
      wt.innerHTML = '';
      (s.when_to_use || []).forEach((line) => {
        const li = document.createElement('li');
        li.textContent = line;
        wt.appendChild(li);
      });
      if (!wt.children.length) {
        const li = document.createElement('li');
        li.textContent = '(see SKILL.md on GitHub)';
        li.style.color = 'var(--muted)';
        wt.appendChild(li);
      }

      $('meta-tier').innerHTML = `<span class="tier-pill tier-${s.tier}">tier ${s.tier}</span>`;
      $('meta-tags').textContent = (s.tags || []).join(', ') || '—';
      $('meta-license').textContent = s.license || 'MIT';
      const codes = [];
      if (s.has_script) codes.push('Python');
      if (s.has_typescript) codes.push('TypeScript');
      $('meta-code').textContent = codes.length ? codes.join(' + ') : 'prompt-only';

      const link = $('github-link');
      link.href = s.github_url;
      link.textContent = 'View SKILL.md on GitHub';

      $('install-cmd').textContent = `npx healthcare-skills add ${s.name}`;
    })
    .catch((err) => {
      $('title').textContent = 'Failed to load';
      $('desc').textContent = err.message;
    });
})();
