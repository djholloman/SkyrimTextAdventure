let pyodide, game;
const $ = id => document.getElementById(id);
// Convert Python return values into ordinary JavaScript values before rendering
// or passing them to browser APIs. Destroy temporary PyProxy objects afterwards.
function fromPython(proxy, options){
  try{
    return proxy.toJs(options || {dict_converter:Object.fromEntries});
  }finally{
    if(proxy && typeof proxy.destroy === "function") proxy.destroy();
  }
}
const stageTitles = {
  helgen_choice:"Escape from Helgen", bear_choice:"The Bear in the Tunnels",
  riverwood:"Riverwood", shop:"Alvor's Blacksmith", trader:"The Golden Claw",
  barrow_intro:"Bleak Falls Barrow", combat:"Battle", branching:"Choose Your Destiny",
  brotherhood_choice:"The Abandoned Shack", paarthurnax:"The Throat of the World",
  sovngarde:"Sovngarde", ending:"The Saga Is Written", game_over:"Your Saga Ends"
};
const raceNotes = {
  "Nord":"Nords begin with greater health and defense.",
  "High Elf":"High Elves begin with greater magicka and spell power.",
  "Khajiit":"Khajiit begin with sharper attacks and a pouch of Skooma."
};
function toast(message){const el=$("toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2200)}
function appendLines(lines){
  const log=$("storyLog");
  for(const line of (lines||[])){
    const p=document.createElement("p");
    if(/^LEVEL UP|^THE SAGA IS WRITTEN/.test(line))p.className="system";
    p.textContent=line;log.appendChild(p);
  }
  log.scrollTop=log.scrollHeight;
}
function render(data, append=true){
  const s=data.state;
  if(append)appendLines(data.lines);
  $("sceneTitle").textContent=stageTitles[s.stage]||"The Adventure";
  $("location").textContent=(s.location||"Skyrim").toUpperCase();
  $("charName").textContent=s.name;
  $("charMeta").textContent=`${s.race} · ${s.character_class}`;
  $("level").textContent=s.level;$("xp").textContent=s.xp;$("xpNeeded").textContent=s.xp_needed;
  $("xpBar").style.width=Math.min(100,100*s.xp/s.xp_needed)+"%";
  $("hpText").textContent=`${s.hp} / ${s.max_hp}`;
  $("hpBar").style.width=Math.max(0,100*s.hp/s.max_hp)+"%";
  $("manaText").textContent=`${s.mana} / ${s.max_mana}`;
  $("manaBar").style.width=Math.max(0,100*s.mana/s.max_mana)+"%";
  $("attack").textContent=s.attack;$("spell").textContent=s.spell;
  $("defense").textContent=s.defense;$("gold").textContent=s.gold;
  $("inventoryList").innerHTML="";
  (s.inventory||[]).forEach(item=>{const li=document.createElement("li");li.textContent=item;$("inventoryList").appendChild(li)});
  $("magicList").textContent=[...(s.spells||[]),...(s.shouts||[])].join(" · ")||"None";
  $("companion").textContent=s.companion||"None";
  const ep=$("enemyPanel");
  if(s.enemy){
    ep.classList.remove("hidden");$("enemyName").textContent=s.enemy.name;
    $("enemyHpText").textContent=`${Math.max(0,s.enemy.hp)} / ${s.enemy.max_hp}`;
    $("enemyHpBar").style.width=Math.max(0,100*s.enemy.hp/s.enemy.max_hp)+"%";
  }else ep.classList.add("hidden");
  const choices=$("choices");choices.innerHTML="";
  (data.options||[]).forEach(option=>{
    const b=document.createElement("button");b.className="choice";
    const strong=document.createElement("strong");strong.textContent=option.label;
    const small=document.createElement("small");small.textContent=option.detail||"";
    b.append(strong,small);b.addEventListener("click",()=>act(option.id));choices.appendChild(b);
  });
  if(s.stage==="ending"||s.stage==="game_over"){
    $("endingPanel").classList.remove("hidden");
    const title=s.ending_title||(s.stage==="game_over"?"GAME OVER":"THE SAGA IS WRITTEN");
    $("endingPanel").innerHTML="";
    const h=document.createElement("h3");h.textContent=title;$("endingPanel").appendChild(h);
  }else $("endingPanel").classList.add("hidden");
  $("saveBtn").disabled=false;$("loadBtn").disabled=false;
}
function handle(data){render(data)}
function act(action){
  if(!game)return;
  if(action==="restart"){
    game=pyodide.runPython("game.Game()");
    $("game").classList.add("hidden");$("setup").classList.remove("hidden");
    $("storyLog").innerHTML="";$("playerName").value="Dragonborn";
    toast("A new saga awaits.");return;
  }
  const data=fromPython(game.act(action));handle(data);
}
async function boot(){
  try{
    $("loadStatus").textContent="Downloading Pyodide runtime...";
    pyodide=await loadPyodide();
    $("loadStatus").textContent="Loading the Python adventure...";
    const response=await fetch("game.py");
    if(!response.ok)throw new Error("Could not load game.py ("+response.status+")");
    const source=await response.text();
    pyodide.FS.writeFile("game.py",source);
    await pyodide.runPythonAsync("import game");
    $("loading").classList.add("hidden");
    $("setup").classList.remove("hidden");
    // Allow an existing local save to be loaded before creating a new character.
    $("loadBtn").disabled=false;
  }catch(err){
    $("loadStatus").textContent="Unable to load the game engine.";
    $("loading").querySelector("p").textContent=err.message+" — check your connection and GitHub Pages deployment.";
    console.error(err);
  }
}
$("race").addEventListener("change",e=>$("raceNote").textContent=raceNotes[e.target.value]);
$("beginBtn").addEventListener("click",()=>{
  if(!pyodide){toast("The Python engine is still loading.");return}
  const name=$("playerName").value.trim()||"Dragonborn";
  const race=$("race").value, cls=$("class").value;
  game=pyodide.runPython("game.Game()");
  const data=fromPython(game.start(name,race,cls));
  $("setup").classList.add("hidden");$("game").classList.remove("hidden");
  $("storyLog").innerHTML="";handle(data);
});
$("saveBtn").addEventListener("click",()=>{
  if(!game)return;
  const saved=fromPython(game.export_state(),{});
  localStorage.setItem("skyrimDragonbornSave",saved);
  toast("Your saga has been saved in this browser.");
});
$("loadBtn").addEventListener("click",async()=>{
  const saved=localStorage.getItem("skyrimDragonbornSave");
  if(!saved){toast("No saved saga found in this browser.");return}
  try{
    pyodide.globals.set("saved_json",saved);
    game=pyodide.runPython("game.Game(__import__('json').loads(saved_json))");
    const data=fromPython(game.result());
    $("setup").classList.add("hidden");$("game").classList.remove("hidden");
    $("storyLog").innerHTML="";appendLines(["Your saved adventure resumes..."]);
    render(data,false);toast("Saved adventure loaded.");
  }catch(e){toast("That save could not be loaded.");console.error(e)}
});
boot();
