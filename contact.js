'use strict';
(() => {
 const form = document.querySelector('#enquiry-form');
 const contactEmail=JSON.parse(document.querySelector('#site-state').textContent).settings.email;
 const message = document.querySelector('#message');
 let preparedText = '';
 const invalidateDraft=()=>{if(preparedText){preparedText='';document.querySelector('#draft-result').hidden=true;}};
 form.addEventListener('input',invalidateDraft);
 form.addEventListener('change',invalidateDraft);
 message.addEventListener('input', () => { document.querySelector('#message-count').textContent = `${message.value.length} / 3000`; });
 form.addEventListener('submit', event => {
  event.preventDefault();
  for (const id of ['name','message']) {
   const field = document.getElementById(id);
   field.setCustomValidity(field.value.trim() ? '' : 'Please enter a little more than spaces.');
   field.addEventListener('input', () => field.setCustomValidity(''), {once:true});
  }
  if (!form.reportValidity()) return;
  const fields = new FormData(form);
  const name = fields.get('name').trim();
  const email = fields.get('email').trim();
  const project = fields.get('projectType');
  const budget = fields.get('budget');
  const body = `Hi Washma,\n\nI’d love to discuss a project with you.\n\nName: ${name}\nEmail: ${email}\nProject type: ${project}\nBudget (USD): ${budget}\n\nProject details:\n${message.value.trim()}\n\nThanks,\n${name}`;
  const subject = `Project enquiry: ${project} — ${name}`;
  const mailto = `mailto:${encodeURIComponent(contactEmail)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  preparedText = `To: ${contactEmail}\nSubject: ${subject}\n\n${body}`;
  document.querySelector('#draft-link').href = mailto;
  document.querySelector('#draft-preview').textContent = preparedText;
  form.reset();
  for (const field of form.querySelectorAll('input, textarea, select')) field.setCustomValidity('');
  document.querySelector('#message-count').textContent = `0 / ${message.maxLength}`;
  document.querySelector('#draft-status').textContent = 'Your enquiry was prepared successfully and the form has been reset. Your message has not been sent yet. Choose Open Email Draft to review and send it from your email app, or copy your enquiry below.';
  const result = document.querySelector('#draft-result');
  result.querySelector('details').open = false;
  result.hidden = false;
  result.tabIndex = -1;
  result.querySelector('h3').id = 'draft-confirmation-title';
  result.setAttribute('aria-labelledby', 'draft-confirmation-title');
  result.focus({preventScroll:true});
  result.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block:'center'});
 });
 document.querySelector('#copy-enquiry').addEventListener('click', async () => {
  const status = document.querySelector('#draft-status');
  try {
   if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
   await navigator.clipboard.writeText(preparedText);
   status.textContent = `Enquiry copied. Paste it into an email to ${contactEmail}, then review and send it.`;
  } catch {
   const preview = document.querySelector('#draft-preview');
   preview.closest('details').open = true;
   const range = document.createRange(); range.selectNodeContents(preview);
   const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
   status.textContent = 'Automatic copying isn’t available here. Your prepared message is selected below; copy it and paste it into your email app.';
  }
 });
})();
