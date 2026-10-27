'use strict';
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
menuButton.addEventListener('click', () => { const open = menuButton.getAttribute('aria-expanded') !== 'true'; menuButton.setAttribute('aria-expanded', String(open)); navigation.classList.toggle('open', open); });
navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', () => { navigation.classList.remove('open'); menuButton.setAttribute('aria-expanded', 'false'); }));
document.addEventListener('keydown', e => { if (e.key === 'Escape') { navigation.classList.remove('open'); menuButton.setAttribute('aria-expanded', 'false'); } });
const revealObserver = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('visible'); revealObserver.unobserve(entry.target); } }), { threshold: .1 });
document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));
const counterObserver = new IntersectionObserver(entries => entries.forEach(entry => { if (!entry.isIntersecting) return; const el = entry.target, target = Number(el.dataset.count), decimals = Number(el.dataset.decimals || 0); counterObserver.unobserve(el); if (reducedMotion || !Number.isFinite(target)) return; const start = performance.now(); const step = time => { const progress = Math.min((time - start) / 1500, 1); el.textContent = (target * (1 - Math.pow(1 - progress, 3))).toFixed(decimals); if (progress < 1) requestAnimationFrame(step); }; requestAnimationFrame(step); }), { threshold: .8 });
document.querySelectorAll('[data-count]').forEach(el => counterObserver.observe(el));
if (document.querySelector('.testimonial-track')) {
let slide = 0, paused = reducedMotion, hovered = false, focused = false, carouselVisible = false;
const track = document.querySelector('.testimonial-track'), carousel = document.querySelector('.testimonial-window'), pause = document.querySelector('#pause');
function showSlide(value) { slide = (value + 3) % 3; track.style.transform = `translateX(-${slide * 100}%)`; document.querySelector('#slide-status').textContent = `0${slide + 1} / 03`; track.querySelectorAll('.quote').forEach((el, i) => el.setAttribute('aria-hidden', String(i !== slide))); }
function updatePause() { const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',paused?'M9 5 19 12 9 19Z':'M8 5v14M16 5v14');path.setAttribute('fill',paused?'currentColor':'none');path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','1.8');svg.append(path);pause.replaceChildren(svg); pause.setAttribute('aria-label', paused ? 'Play automatic testimonials' : 'Pause automatic testimonials'); }
document.querySelector('#next').addEventListener('click', () => { showSlide(slide + 1); paused = true; updatePause(); });
document.querySelector('#previous').addEventListener('click', () => { showSlide(slide - 1); paused = true; updatePause(); });
pause.addEventListener('click', () => { paused = !paused; updatePause(); });
const testimonialSection = document.querySelector('#testimonials');
testimonialSection.addEventListener('mouseenter', () => { hovered = true; }); testimonialSection.addEventListener('mouseleave', () => { hovered = false; });
testimonialSection.addEventListener('focusin', () => { focused = true; }); testimonialSection.addEventListener('focusout', e => { focused = testimonialSection.contains(e.relatedTarget); });
new IntersectionObserver(entries => { carouselVisible = entries[0].isIntersecting; }).observe(carousel);
setInterval(() => { if (!paused && !hovered && !focused && !document.hidden && carouselVisible) showSlide(slide + 1); }, 6000); showSlide(0); updatePause();
}
const dialog = document.querySelector('#detail-dialog');
function showDialog(title, description, label = 'A LITTLE MORE DETAIL') { document.querySelector('#dialog-title').textContent = title; document.querySelector('#dialog-description').textContent = description; document.querySelector('#dialog-label').textContent = label; dialog.showModal(); }
document.querySelector('.dialog-close').addEventListener('click', () => dialog.close()); document.querySelector('.dialog-done').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', e => { if (e.target === dialog) { const rect = dialog.getBoundingClientRect(); if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) dialog.close(); } });
const featuredData=JSON.parse(document.querySelector('#site-state').textContent).featured;
document.querySelectorAll('[data-featured]').forEach(button=>button.addEventListener('click',()=>{const item=featuredData[Number(button.dataset.featured)];showDialog(item.title,item.description,item.category)}));
document.querySelectorAll('[data-social]').forEach(button => button.addEventListener('click', () => showDialog(`${button.dataset.social} is coming soon.`, `The direct profile URL has not been added yet. Email ${JSON.parse(document.querySelector('#site-state').textContent).settings.email} to request the link, or use the Contact page to start a conversation.`, 'STAY CONNECTED')));
document.querySelector('#year').textContent = new Date().getFullYear();
const sections = [...document.querySelectorAll('main section[id]')]; const navigationObserver = new IntersectionObserver(entries => { entries.forEach(entry => { if (!entry.isIntersecting) return; const id = entry.target.id; if (!navigation.querySelector(`a[href="#${id}"]`)) return; navigation.querySelectorAll('a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${id}`)); }); }, { rootMargin: '-15% 0px -65% 0px' }); sections.forEach(section => navigationObserver.observe(section));

matchMedia('(min-width: 761px)').addEventListener('change',event=>{if(event.matches){navigation.classList.remove('open');menuButton.setAttribute('aria-expanded','false');}});
