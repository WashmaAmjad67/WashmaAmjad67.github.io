'use strict';
(() => {
 const tabs = [...document.querySelectorAll('[data-filter]')];
 const cards = [...document.querySelectorAll('.portfolio-card')];
 const grid = document.querySelector('.portfolio-grid');
 const panel = document.querySelector('#project-panel');
 const reduced = matchMedia('(prefers-reduced-motion: reduce)');
 const labels = {long:'THE LONGER STORY',short:'SMALL FORMAT. BIG FEELING.',color:'THE FINISHING TOUCHES'};
 let version = 0;
 const observer = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) { entry.target.classList.remove('pending-reveal'); observer.unobserve(entry.target); }
 }), {threshold:.08});
 function observeCards() {
  cards.filter(card => !card.hidden).forEach((card, index) => {
   card.style.setProperty('--card-delay', `${(index % 2) * 100}ms`);
   if (!reduced.matches) card.classList.add('pending-reveal');
   observer.observe(card);
  });
 }
 async function filter(tab) {
  if (tab.getAttribute('aria-selected') === 'true') return;
  const currentVersion = ++version;
  tabs.forEach(item => { const selected = item === tab; item.setAttribute('aria-selected', String(selected)); item.tabIndex = selected ? 0 : -1; });
  grid.getAnimations().forEach(animation => animation.cancel());
  if (!reduced.matches) {
   const exit = grid.animate([{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(6px)'}], {duration:160,easing:'ease-out'});
   await exit.finished.catch(() => {});
  }
  if (currentVersion !== version) return;
  cards.forEach(card => { observer.unobserve(card); card.classList.remove('pending-reveal'); card.hidden = card.dataset.category !== tab.dataset.filter; });
  panel.setAttribute('aria-labelledby',tab.id);
  document.querySelector('#collection-label').textContent = labels[tab.dataset.filter];
  document.querySelector('#filter-status').textContent = `${cards.filter(card=>!card.hidden).length} projects / ${tab.textContent.replace(/\d+\s*$/, '').trim()}`;
  document.querySelector('.portfolio-empty').hidden=cards.some(card=>!card.hidden);
  observeCards();
 }
 tabs.forEach((tab,index) => {
  tab.addEventListener('click',() => filter(tab));
  tab.addEventListener('keydown',event => {
   let next;
   if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
   if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
   if (event.key === 'Home') next = 0;
   if (event.key === 'End') next = tabs.length - 1;
   if (next !== undefined) { event.preventDefault(); tabs[next].focus(); filter(tabs[next]); }
  });
 });
 document.querySelector('.portfolio-empty').hidden=cards.some(card=>!card.hidden);
 document.querySelector('#filter-status').textContent=`${cards.filter(card=>!card.hidden).length} projects / YouTube Long-Form`;
 observeCards();
 const lightbox = document.querySelector('#project-lightbox');
 cards.forEach(card => card.querySelector('button').addEventListener('click',event => {
  const button = event.currentTarget;
  const image = document.querySelector('#lightbox-image');
  image.src = button.dataset.image; image.alt = button.dataset.alt;
  document.querySelector('#lightbox-title').textContent = button.dataset.title;
  document.querySelector('#lightbox-description').textContent = button.dataset.description;
  document.querySelector('#lightbox-category').textContent = button.dataset.categoryLabel;
  lightbox.showModal(); lightbox.scrollTop = 0;
 }));
 document.querySelector('.lightbox-close').addEventListener('click',() => lightbox.close());
 document.querySelector('#lightbox-done').addEventListener('click',() => lightbox.close());
 lightbox.addEventListener('click',event => {
  if (event.target !== lightbox) return;
  const bounds = lightbox.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) lightbox.close();
 });
})();
