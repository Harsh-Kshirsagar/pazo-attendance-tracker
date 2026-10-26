(() => {
  const table = document.getElementById('attendance-table');
  if (!table) return;

  const selects = Array.from(table.querySelectorAll('[data-attendance-select]'));
  const rows = Array.from(table.querySelectorAll('[data-attendance-row]'));
  const statusLabels = { P: 'present', A: 'absent', L: 'leave', H: 'halfday', '': 'blank' };

  const recount = () => {
    const daily = {};
    const grand = { P: 0, A: 0, L: 0, H: 0, marked: 0 };

    rows.forEach((row) => {
      const counts = { P: 0, A: 0, L: 0, H: 0, marked: 0 };
      row.querySelectorAll('[data-attendance-select]').forEach((select) => {
        const value = select.value;
        select.classList.remove('status-p', 'status-a', 'status-l', 'status-h', 'status-blank');
        select.classList.add(`status-${statusLabels[value] || 'blank'}`);
        if (value) {
          counts[value] += 1;
          counts.marked += 1;
          grand[value] += 1;
          grand.marked += 1;
          const datePart = select.name.slice(select.name.lastIndexOf('_') + 1);
          daily[datePart] = (daily[datePart] || 0) + 1;
        }
      });
      ['P', 'A', 'L', 'H', 'marked'].forEach((key) => {
        const target = row.querySelector(`[data-total="${key}"]`);
        if (target) target.textContent = counts[key];
      });
    });

    table.querySelectorAll('[data-day-total]').forEach((cell) => {
      cell.textContent = daily[cell.dataset.dayTotal] || '—';
    });
    const targets = { P: 'grand-p', A: 'grand-a', H: 'grand-h', L: 'grand-l', marked: 'grand-marked' };
    Object.entries(targets).forEach(([key, id]) => {
      const target = document.getElementById(id);
      if (target) target.textContent = grand[key];
    });
  };

  selects.forEach((select) => select.addEventListener('change', recount));
  const markAll = document.getElementById('fill-present');
  if (markAll) markAll.addEventListener('click', () => {
    if (!window.confirm('Mark every date for every active person as present? This overwrites existing marks in this month.')) return;
    selects.forEach((select) => { select.value = 'P'; });
    recount();
  });
  const clear = document.getElementById('clear-attendance');
  if (clear) clear.addEventListener('click', () => {
    if (!window.confirm('Clear every selected mark in this month? The changes will take effect only after you save.')) return;
    selects.forEach((select) => { select.value = ''; });
    recount();
  });

  recount();
})();
