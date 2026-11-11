import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';

const workspaceDir = 'C:/Users/Administrator/water-tank-study';
const skill = 'C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const runtime = 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime';
const build = path.join(workspaceDir,'tmp/next-submissions');
const output = path.join(workspaceDir,'next-submissions/Design_Presentation_2026-11-17');
const {finalizePresentation} = await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);

const slides = JSON.parse(await fs.readFile(path.join(workspaceDir,'next-submissions/Authoring/design_slides.json'),'utf8'));

const p = Presentation.create({slideSize:{width:1280,height:720}});
function text(slide,name,value,x,y,w,h,size=30,bold=false,color='#111111') {
 const shape=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=value;
 shape.text.style={fontFamily:'Arial',fontSize:size,bold,color};
 shape.text.insets=0;
 return shape;
}
await fs.mkdir(path.join(build,'design-order-previews'),{recursive:true});
await fs.mkdir(output,{recursive:true});
for (const [i,data] of slides.entries()) {
 const s=p.slides.add(); s.background.fill='#FFFFFF';
 if (data.cover) {
  text(s,'title',data.title,80,120,1120,170,58,true);
  data.lines.forEach((line,j)=>text(s,`cover-${j}`,line,84,360+j*48,1000,42,28,false));
 } else {
  text(s,'title',data.title,80,62,1120,80,44,true);
  const start=data.code ? 240:210;
  if(data.code) text(s,'command-format',data.code,84,160,1100,46,31,true,'#284B63');
  data.lines.forEach((line,j)=>text(s,`point-${j}`,line,84,start+j*88,1100,74,30,false));
 }
 text(s,'page',String(i+1),1165,664,40,25,17,false,'#555555');
 s.speakerNotes.text=data.notes;
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(build,'design-order-previews',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(build,'design-order-candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(output,'Design_Presentation_Finley_Burns_Final.pptx');
const result=await finalizePresentation({
 workspaceDir,candidatePath:candidate,finalPath,
 pythonExecutable:path.join(runtime,'dependencies/python/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'design-order-validation.json')
});
await fs.writeFile(path.join(output,'Speaking_Notes.txt'),slides.map((s,i)=>`SLIDE ${i+1} - ${s.title.replaceAll('\n',' ')}\n\n${s.notes}\n`).join('\n'));
await fs.writeFile(path.join(workspaceDir,'next-submissions/Authoring/design_slides.json'),JSON.stringify(slides,null,2)+'\n');
console.log(JSON.stringify({finalPath,result},null,2));
