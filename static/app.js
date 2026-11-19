// Filters stay entirely in the browser; every CRUD form still works without JS.
document.querySelectorAll('[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
document.querySelectorAll('[data-records]').forEach(section => {
  const search = section.querySelector('[data-search]');
  const status = section.querySelector('[data-status-filter]');
  const rows = [...section.querySelectorAll('[data-record]')];
  const filter = () => {
    const query = search.value.trim().toLocaleLowerCase();
    let count = 0;
    rows.forEach(row => {
      const matches = row.textContent.toLocaleLowerCase().includes(query) && (!status || !status.value || row.dataset.status === status.value);
      row.hidden = !matches;
      if (matches) count++;
    });
    section.querySelector('[data-result-count]').textContent = `${count} of ${rows.length} records`;
    section.querySelector('[data-no-results]').hidden = count !== 0 || rows.length === 0;
  };
  search.addEventListener('input', filter);
  status?.addEventListener('change', filter);
  filter();
});
const openRecord = () => {
  if (location.hash === '#new-record') {
    const panel = document.getElementById('new-record');
    if (panel) { panel.open = true; panel.querySelector('input,select')?.focus({preventScroll:true}); }
  }
};
window.addEventListener('hashchange', openRecord);
openRecord();
// Decorative artwork moves only; text, controls, and navigation remain still.
const art = document.querySelector('[data-parallax]');
const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
if (art) {
  let scheduled = false;
  const paint = () => {
    art.style.transform = motion.matches ? 'none' : `translateY(${Math.min(window.scrollY, 600) * 0.13}px)`;
    scheduled = false;
  };
  window.addEventListener('scroll', () => {
    if (!scheduled) { scheduled = true; window.requestAnimationFrame(paint); }
  }, {passive:true});
  motion.addEventListener('change', paint);
  paint();
}
