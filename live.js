'use strict';
(() => {
 const initial=JSON.parse(document.querySelector('#site-state').textContent);
 window.siteState=initial;
 let changed=false;
 function update(revision){if(Number(revision)===Number(initial.revision)||changed)return;changed=true;
  // Keep an in-progress enquiry when an administrator publishes an update.
  const form=document.querySelector('#enquiry-form');
  try{if(form){const values={};new FormData(form).forEach((v,k)=>values[k]=v);sessionStorage.setItem('portfolio-enquiry',JSON.stringify(values));}}catch{}
  location.reload();
 }
 let stored=null;try{stored=sessionStorage.getItem('portfolio-enquiry');}catch{}
 if(stored&&document.querySelector('#enquiry-form')){try{const values=JSON.parse(stored);for(const [key,value] of Object.entries(values)){const field=document.querySelector('#enquiry-form').elements.namedItem(key);if(field){field.value=value;field.dispatchEvent(new Event('input',{bubbles:true}));}}}catch{}try{sessionStorage.removeItem('portfolio-enquiry');}catch{}}
 if(window.EventSource){const events=new EventSource('/api/events');events.onmessage=event=>{try{update(JSON.parse(event.data).revision)}catch{}};window.addEventListener('pagehide',()=>events.close());}
 setInterval(async()=>{if(document.hidden)return;try{const response=await fetch('/api/version',{cache:'no-store'});if(response.ok)update((await response.json()).revision)}catch{}},5000);
 document.addEventListener('visibilitychange',async()=>{if(!document.hidden){try{update((await (await fetch('/api/version')).json()).revision)}catch{}}});
})();
