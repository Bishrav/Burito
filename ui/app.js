const clock=document.querySelector('#clock'),date=document.querySelector('#date'),toast=document.querySelector('#toast');
const form=document.querySelector('#composer'),input=document.querySelector('#message'),conversation=document.querySelector('#conversation');
const status=document.querySelector('#connectionStatus'),connectionMessage=document.querySelector('#connectionMessage');
const tokenMeter=document.querySelector('.token-meter');
let sessionId=null,busy=false;
function tick(){const now=new Date();clock.textContent=now.toLocaleTimeString([],{hour12:false});date.textContent=now.toLocaleDateString([],{year:'numeric',month:'short',day:'2-digit'}).toUpperCase()}tick();setInterval(tick,1000);
document.querySelectorAll('[data-nav]').forEach(button=>button.addEventListener('click',()=>{const target=button.dataset.nav,section=document.getElementById(target);if(section){section.scrollIntoView({behavior:'smooth',block:'start'});document.querySelectorAll('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.nav===target))}else{toast.textContent=`${target.toUpperCase()} view is planned.`;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),2400)}}));
function addMessage(role,text){const row=document.createElement('div');row.className=`chat-message ${role}`;const who=document.createElement('b');who.textContent=role==='user'?'YOU':'BURITO';const body=document.createElement('p');body.textContent=text;row.append(who,body);conversation.append(row);row.scrollIntoView({block:'nearest'})}
function formatTokens(value){return Number.isFinite(value)?new Intl.NumberFormat().format(value):'—'}
function updateTokenMeter(usage){
  if(!usage||!usage.reported||!Number.isFinite(usage.latestRequestTokens)||!Number.isFinite(usage.contextLimit)){
    tokenMeter.dataset.state='unavailable';
    document.querySelector('#tokenState').textContent='USAGE NOT REPORTED';
    document.querySelector('#contextUsed').textContent='—';
    document.querySelector('#contextCapacity').textContent='/ — context tokens';
    document.querySelector('#contextRemaining').textContent='— left';
    document.querySelector('#latestInput').textContent=formatTokens(usage?.latestInput);
    document.querySelector('#latestOutput').textContent=formatTokens(usage?.latestOutput);
    document.querySelector('#sessionTotal').textContent=formatTokens(usage?.sessionTotal);
    document.querySelector('#tokenProgress').style.width='0%';
    document.querySelector('.token-track').setAttribute('aria-valuenow','0');
    document.querySelector('#tokenNote').textContent='The model did not report usable token counts for this turn. Burito will show them when the runtime provides them; it will not invent an estimate.';
    return;
  }
  const used=usage.latestRequestTokens,limit=usage.contextLimit,remaining=usage.estimatedContextRemaining;
  const percent=Math.min(100,Math.round((used/limit)*100));
  tokenMeter.dataset.state='reported';
  document.querySelector('#tokenState').textContent='MODEL USAGE REPORTED';
  document.querySelector('#contextUsed').textContent=formatTokens(used);
  document.querySelector('#contextCapacity').textContent=`/ ${formatTokens(limit)} configured context tokens in the latest model pass`;
  document.querySelector('#contextRemaining').textContent=`~${formatTokens(remaining)} left`;
  document.querySelector('#latestInput').textContent=formatTokens(usage.latestInput);
  document.querySelector('#latestOutput').textContent=formatTokens(usage.latestOutput);
  document.querySelector('#sessionTotal').textContent=formatTokens(usage.sessionTotal);
  document.querySelector('#tokenProgress').style.width=`${percent}%`;
  document.querySelector('.token-track').setAttribute('aria-valuenow',String(percent));
  document.querySelector('#tokenNote').textContent='Counts are reported by the local model runtime. Remaining context is an estimate for the latest model pass; session total accumulates input and output across this chat. This is not an account or billing quota.';
}
async function checkHealth(){try{const response=await fetch('/eve/v1/health');if(!response.ok)throw Error(`HTTP ${response.status}`);const result=await response.json();if(result.status!=='ready')throw Error('not ready');status.textContent='LOCAL RUNTIME READY';connectionMessage.textContent='Connected to Burito’s local Eve runtime. Messages stay on this computer.';input.disabled=false;document.querySelector('.composer button').disabled=false;document.querySelector('.connection-card .pill').className='pill neutral';document.querySelector('.connection-card .pill').textContent='LOCAL READY'}catch(error){status.textContent='RUNTIME OFFLINE';connectionMessage.textContent='Start Burito with the web command in Konsole. The interface will connect automatically.'}}
form.addEventListener('submit',async event=>{event.preventDefault();const text=input.value.trim();if(!text||busy)return;busy=true;input.value='';addMessage('user',text);const bubble=document.createElement('div');bubble.className='chat-message assistant';const who=document.createElement('b');who.textContent='BURITO';const reply=document.createElement('p');reply.textContent='Thinking…';bubble.append(who,reply);conversation.append(bubble);status.textContent='BURITO IS RESPONDING';try{const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,sessionId})});const data=await response.json();if(data.tokenUsage)updateTokenMeter(data.tokenUsage);if(!response.ok||data.status==='failed')throw Error(data.error||`Local chat returned ${response.status}`);sessionId=data.sessionId;reply.textContent=data.reply||'(Burito returned no text. Check the runtime log in Konsole.)';status.textContent='LOCAL RUNTIME READY'}catch(error){reply.textContent=`Could not complete the local chat turn: ${error.message}`;status.textContent='CHAT ERROR'}finally{busy=false;input.focus()}});
checkHealth();
