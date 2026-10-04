// Execute our own dashboard JavaScript with a minimal DOM adapter, not a browser.
// Checks event wiring, computed view content, note isolation and export payloads.
// Does not validate CSS layout or actual browser storage/download behavior.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync(new URL('../output/report.html',import.meta.url),'utf8');
const payload=html.match(/<script id="report-data" type="application\/json">([\s\S]*?)<\/script>/)?.[1];
assert.ok(payload,'Embedded research data missing');
const data=JSON.parse(payload);
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1];
assert.ok(script,'Dashboard script missing');
const elements=new Map(), downloads=[], storage=new Map(), blobs=new Map();
let prints=0;
class Element {
  constructor(id=''){this.id=id;this.handlers={};this.dataset={};this.hidden=false;this.textContent='';this.value='';this.attributes={};this._html='';}
  set innerHTML(value){this._html=value;for(const m of value.matchAll(/\bid="([^"]+)"/g))elements.set(m[1],new Element(m[1]));}
  get innerHTML(){return this._html;}
  addEventListener(name,fn){this.handlers[name]=fn;}
  setAttribute(name,value){this.attributes[name]=value;}
  appendChild(){}
  remove(){}
  click(){if(this.download)downloads.push({name:this.download,blob:blobs.get(this.href)});this.handlers.click?.({target:this});}
  closest(){return null;}
}
for(const m of html.matchAll(/\bid="([^"]+)"/g))elements.set(m[1],new Element(m[1]));
elements.get('report-data').textContent=payload;
const nav=Object.fromEntries(['overview','research','committee','sources'].map(v=>[v,new Element(v)]));
const printNotes=new Element('print-notes');
const doc={
  getElementById:id=>{assert.ok(elements.has(id),'Unexpected DOM id: '+id);return elements.get(id);},
  querySelector:selector=>{if(selector==='.print-notes')return printNotes;const view=selector.match(/data-view="([^"]+)"/)?.[1];assert.ok(nav[view],'Unexpected selector: '+selector);return nav[view];},
  addEventListener(name,fn){this[name]=fn;},
  createElement:()=>new Element(),body:new Element('body')
};
class TestURL extends URL {}
TestURL.createObjectURL=blob=>{const key='blob:test-'+blobs.size;blobs.set(key,blob);return key;};
TestURL.revokeObjectURL=key=>blobs.delete(key);
const context=vm.createContext({document:doc,localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,val)=>storage.set(key,val)},window:{print:()=>prints++},URL:TestURL,Blob,setTimeout:()=>1,clearTimeout:()=>{}});
vm.runInContext(script,context,{timeout:5000});
assert.match(elements.get('pane-overview').innerHTML,/Manager comparison/);
const change=(id,value)=>{const el=elements.get(id);el.value=value;assert.equal(typeof el.handlers.change,'function');el.handlers.change({target:el});};
const view=name=>vm.runInContext(`setView('${name}')`,context);
let comparisons=0;
for(const fund of data.funds){
  change('fund-select',fund.ticker);
  for(const window of ['36','60','120']){
    change('window-select',window);
    for(const benchmark of ['SPY','IWF','IWD','VIG']){
      change('benchmark-select',benchmark);
      const expected=fund.windows[window][benchmark];
      for(const page of ['overview','research','committee','sources']){
        view(page);
        const body=elements.get('pane-'+page).innerHTML;
        assert.ok(body.length>1000);
        assert.doesNotMatch(body,/NaN|undefined|Infinity/);
        assert.equal(elements.get('pane-'+page).hidden,false);
        if(page==='research'){
          assert.ok(body.includes((expected.cagr*100).toFixed(1)+'%'));
          assert.ok(body.includes('Growth of 100 dollars over '+window+' months'));
          assert.ok(body.includes(benchmark+' proxy'));
          assert.ok(body.includes(fund.name.replaceAll('&','&amp;')));
        }
      }
      comparisons++;
    }
  }
}
change('fund-select','FCNTX');change('window-select','36');change('benchmark-select','IWD');view('committee');
let notes=elements.get('analyst-notes');notes.value='Verify capacity <not approved> & team continuity';notes.handlers.input({target:notes});
assert.equal(storage.get('meridian.notes.v1.FCNTX'),notes.value);
elements.get('export-json').click();
const exported=JSON.parse(await downloads.at(-1).blob.text());
assert.equal(exported.scope.fund,'FCNTX');assert.equal(exported.scope.period_months,36);assert.equal(exported.scope.benchmark_proxy,'IWD');
assert.equal(exported.analyst_notes,notes.value);assert.equal(exported.performance.cagr,data.funds[0].windows['36'].IWD.cagr);
elements.get('export-csv').click();
const csv=await downloads.at(-1).blob.text();assert.equal(csv.split('\r\n').length,5);assert.ok(csv.includes('"36","IWD"'));
change('fund-select','DODGX');assert.equal(elements.get('analyst-notes').value,'');
change('fund-select','FCNTX');assert.match(elements.get('pane-committee').innerHTML,/&lt;not approved&gt; &amp; team/);
elements.get('print-brief').click();assert.equal(prints,1);
context.localStorage.setItem=()=>{throw new Error('Storage disabled');};
notes=elements.get('analyst-notes');notes.value='Session-only note';notes.handlers.input({target:notes});
elements.get('export-json').click();assert.equal(JSON.parse(await downloads.at(-1).blob.text()).analyst_notes,'Session-only note');
console.log(`PASS: ${comparisons} comparison states across four views; selector wiring, note isolation/escaping, blocked-storage fallback, CSV/JSON payloads and print wiring. DOM simulation only; visual browser validation not performed.`);
