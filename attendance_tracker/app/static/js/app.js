// Small progressive-enhancement helpers shared by all pages.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('click', (event) => {
      if (!window.confirm(element.dataset.confirm || 'Continue?')) event.preventDefault();
    });
  });
});
