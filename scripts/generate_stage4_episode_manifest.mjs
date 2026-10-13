// Auto-generated repository source from tested in-process manifest core.
// Run: node scripts/generate_stage4_episode_manifest.mjs
// No third-party npm packages. Original sealed prereg never modified.
import fs from 'node:fs'; import path from 'node:path'; import {fileURLToPath} from 'node:url';
function SHA256(str){
const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
const H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
const b=[];let z=encodeURIComponent(str);for(let i=0;i<z.length;i++){if(z[i]==="%"){b.push(parseInt(z.slice(i+1,i+3),16));i+=2;}else b.push(z.charCodeAt(i));}
let n=b.length;b.push(128);while(b.length%64!==56)b.push(0);let bits=BigInt(n)*8n;for(let i=7;i>=0;i--)b.push(Number((bits>>BigInt(8*i))&255n));
let rr=(x,n)=>(x>>>n)|(x<<(32-n));
for(let off=0;off<b.length;off+=64){const w=new Array(64);for(let i=0;i<16;i++){let j=off+i*4;w[i]=((b[j]<<24)|(b[j+1]<<16)|(b[j+2]<<8)|b[j+3])>>>0;}for(let i=16;i<64;i++){let s0=rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>>3),s1=rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>>10);w[i]=(w[i-16]+s0+w[i-7]+s1)>>>0;}let [A,B,C,D,E,F,G,Q]=H;for(let i=0;i<64;i++){let S1=rr(E,6)^rr(E,11)^rr(E,25),ch=(E&F)^(~E&G),t1=(Q+S1+ch+K[i]+w[i])>>>0,S0=rr(A,2)^rr(A,13)^rr(A,22),maj=(A&B)^(A&C)^(B&C),t2=(S0+maj)>>>0;Q=G;G=F;F=E;E=(D+t1)>>>0;D=C;C=B;B=A;A=(t1+t2)>>>0;}let v=[A,B,C,D,E,F,G,Q];for(let i=0;i<8;i++)H[i]=(H[i]+v[i])>>>0;}
return H.map(x=>x.toString(16).padStart(8,"0")).join("");
}
function generateManifest(a,p){
const h=a.manifest.hypotheses, splits=["train","validation","test"];
const modes=p.split_policy.structural_nuisance_design;
const combos=[];for(const ac of modes.acquisition_mode)for(const co of modes.counter_source_primary)for(const d of modes.diff_motor_t_mapping)combos.push([ac,co,d]);
combos.sort((x,y)=>x.join("|").localeCompare(y.join("|"),"en"));
if(combos.length!==8)throw Error("structural combos != 8");
const fields=a.manifest.required_manifest_columns;
const seedSet=new Set(),idSet=new Set(),rows=[],count={train:0,validation:0,test:0};
const modeProfile=new Map(),splitSeeds={train:new Set(),validation:new Set(),test:new Set()};
let minPhi=Infinity,maxPhi=-Infinity;
const first8=t=>parseInt(SHA256(t).slice(0,8),16)>>>0;
const rotate=(h,s,q)=>parseInt(SHA256(`TAYCAN4R|struct|${h}|${s}|${q}`).slice(0,2),16)%8;
const phiOff=(h,s)=>parseInt(SHA256(`TAYCAN4R|phi|${h}|${s}`).slice(0,2),16)%7;
const ranges=p.split_policy.parameters_assumed;
const drawSpec=[
["rpm_white_sigma",ranges.rpm_white_sigma_range_rpm],
["rpm_bias_halfwidth",ranges.rpm_bias_halfwidth_range_rpm],
["torque_white_sigma",ranges.torque_white_sigma_range_Nm],
["torque_bias_halfwidth",ranges.torque_bias_halfwidth_range_Nm],
["soc_group_bias_sd",ranges.soc_group_bias_sd_range_pp],
["soc_innovation",ranges.soc_innovation_range_pp_sqrt_s],
["aux_phi",ranges.aux_phi_range_per_second],
["aux_white_sigma",ranges.aux_white_range_W_sqrt_s],
["aux_cap",ranges.aux_cap_range_W]
];
for(const hypo of h)for(const split of splits){
 const countN=a.manifest.n_per_stratum[split];
 const quotas=(hypo==="H00"?a.manifest.H00_quota:a.manifest.severity_tokens);
 for(let qix=0;qix<3;qix++){
 const quota=quotas[qix];const rot=rotate(hypo,split,quota);
 for(let r=0;r<countN;r++){
 const idx=qix*countN+r;
 const block=split==="test"?Math.floor(r/16):Math.floor(r/8);
 const within=split==="test"?r%16:r%8;
 const profile=split==="test"&&within>=8?"SHIFT_REGEN_COLD_6H":"NOMINAL_6H";
 const combo=combos[((split==="test"?within%8:r%8)+rot)%8];
 const phi=p.split_policy.parameters_assumed.soc_phi_grid_per_second[(idx+phiOff(hypo,split))%7];
 const eid=`S4R_${hypo}_${split}_${quota.replaceAll(".","p")}_${String(r).padStart(2,"0")}`;
 if(idSet.has(eid))throw Error("DUPLICATE_ID "+eid);idSet.add(eid);
 const seeds={};for(const stream of ["physics","observer","aux","nuisance"]){
  const str=`TAYCAN4R|${hypo}|${split}|${quota}|${r}|${stream}`;
  const s=first8(str);
  if(seedSet.has(s))throw Error("SEED_COLLISION_"+s+"_"+str);
  seedSet.add(s);splitSeeds[split].add(s);
  seeds["seed_"+stream]=s;
 }
 let state=seeds.seed_nuisance||0x6d2b79f5;
 const rand=()=>{state^=(state<<13);state^=(state>>>17);state^=(state<<5);return (state>>>0)/4294967296;};
 const nuisance={};for(const [name,ran] of drawSpec)nuisance[name]=(ran[0]+(ran[1]-ran[0])*rand()).toFixed(8);
 const entry={episode_id:eid,hypothesis:hypo,split,severity:hypo==="H00"?"0":quota,severity_quota:quota,replicate:r,block,profile,duration_s:a.manifest.episode_duration_s,dt_s:a.manifest.step_seconds_assumed,acquisition_mode:combo[0],counter_source:combo[1],diff_motor_t_mapping:combo[2],soc_phi_per_s:phi.toFixed(7),...nuisance,...seeds};
 if(fields.some(f=>entry[f]===undefined))throw Error("missing column "+eid);
 rows.push(fields.map(f=>String(entry[f])).join(","));
 count[split]++;
 const mkey=[hypo,quota,block,profile,combo.join("|")].join("|");
 if(split==="test"){
  if(modeProfile.has(mkey))throw Error("duplicate structural test block: "+mkey);
  modeProfile.set(mkey,1);
 }
 minPhi=Math.min(minPhi,phi);maxPhi=Math.max(maxPhi,phi);
 }
 }
}
if(rows.length!==2232||count.train!==720||count.validation!==360||count.test!==1152||idSet.size!==2232||seedSet.size!==8928||modeProfile.size!==12*3*2*2*8)throw Error("MANIFEST_COUNTS_OR_STRATA_FAILED "+JSON.stringify({rows:rows.length,count,ids:idSet.size,seeds:seedSet.size,strata:modeProfile.size}));
for(const x of splits)for(const y of splits)if(x!==y)for(const s of splitSeeds[x])if(splitSeeds[y].has(s))throw Error("CROSS_SPLIT_SEED "+s);
const csv=fields.join(",")+"\n"+rows.join("\n")+"\n";
return {csv,summary:{data_rows:rows.length,line_count:rows.length+1,counts:count,unique_episode_ids:idSet.size,unique_seeds:seedSet.size,unique_test_block_mode_combinations:modeProfile.size,test_profile_counts:{nominal:576,shifted:576},phi_range:[minPhi,maxPhi],csv_columns:fields.length,distinct_split_seed_overlap:0}};
}
const HERE = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(HERE,"..");
const sealPath = path.join(root,"experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json");
const amendPath = path.join(root,"experiments/stage_04_data_validation/STAGE4_APPEND_ONLY_AMENDMENT.json");
const outPath = path.join(root,"experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv");
const sealed = fs.readFileSync(sealPath,"utf8"), amend = fs.readFileSync(amendPath,"utf8");
if(SHA256(sealed)!=="1c3c50149e50bceb3f14b8a334b248c225cdc8478128cf88952051ea0bce1b21")throw Error("FAIL: original sealed prereg SHA256 mismatch");
if(SHA256(amend)!=="18c5c8f104f2909a1f23a594eafd8e26a77a1ea4f80e285e0e1396b5a1da29ba")throw Error("FAIL: append-only amendment SHA256 mismatch");
const output=generateManifest(JSON.parse(amend),JSON.parse(sealed));
const csvHash=SHA256(output.csv);
if(fs.existsSync(outPath)){ if(fs.readFileSync(outPath,"utf8")!==output.csv)throw Error("FAIL: manifest exists but differs (no overwrites permitted)"); } else { if(process.argv.includes("--verify"))throw Error("FAIL: expected manifest missing"); fs.writeFileSync(outPath,output.csv,"utf8"); }
console.log(JSON.stringify({...output.summary,manifest_sha256:csvHash,manifest_file:outPath},null,2));
