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

const slides = [
 {
  title:'Secure Embedded\nWater Tank Controller',
  cover:true,
  lines:['Finley Burns','CYCS 3240 Design Presentation','November 17, 2026'],
  notes:'I am building a C controller for one simulated water tank. The main question is whether it can make the right valve decisions while rejecting invalid or unauthorized settings changes. I will explain the design, show what the existing tests establish, and identify the parts I still need to implement. This presentation describes the design as of November 10. It does not claim that the complete tank simulation or authentication is already working.'
 },
 {
  title:'Project scope',
  lines:['One tank, one level sensor, and one inlet valve','C17 on an emulated STM32F4 Cortex-M4','Serial commands for the operating thresholds','Scenario files for repeatable tests'],
  notes:'I kept the scope small so the control behavior and security checks are manageable. The tank is simulated, so I do not need a physical board or plumbing. I originally proposed Rust, but switched to C because the course requires C or C++. Renode still supplies the emulated processor and peripherals. The serial interface is enough for this project, so I am not adding networking or a dashboard. Source: comprehensive design, project scope; https://renode.readthedocs.io/en/latest/introduction/testing.html'
 },
 {
  title:'Valve decisions',
  lines:['Below 30%: open the inlet','Above 70%: close the inlet','At either threshold or between them: keep the previous state','Invalid input: close the inlet and report a fault'],
  notes:'The controller uses hysteresis. Two thresholds give the valve a clear operating range instead of making it switch around one target. The exact endpoints matter: at 30 or 70 percent, the previous state stays in place. The tests check both an initially open and initially closed valve. When valid sensor input returns after a fault, the usual rule resumes. If the reading is between the thresholds, the valve remains closed because the fault closed it. Source: Source/src/controller.c and file-driven control tests.'
 },
 {
  title:'The planned control loop',
  lines:['Sample the level every 100 ms of simulated time','Check the value, validity flag, and sample age','Run the shared control function and update PD12','Then process a limited amount of serial input'],
  notes:'The control step runs before command processing. I plan to treat a sample as stale when it is more than 300 milliseconds old. The current firmware has one fixed reading, so the timer and changing sensor interface are still work to complete. For the first integration I will use a documented record in emulated RAM to inject the level and timestamp. That tests the control loop, but does not establish ADC or electrical behavior. The host tank model will use the measured valve output to calculate the next volume. Sources: comprehensive design; ST RM0090 reference manual.'
 },
 {
  title:'Planned command checks',
  code:'SET,low,high,tag',
  lines:['HMAC-SHA256 checks the command contents','Both thresholds change only after every check passes','Rejected commands leave the existing settings alone','No encryption or replay protection in this scope'],
  notes:'The planned command carries a low threshold, a high threshold, and an authentication tag. I will use an established library such as Mbed TLS and check published HMAC test vectors before using it in the firmware. A valid tag is not enough: reversed thresholds or a value above the allowed range must still be rejected. Both settings are installed together. Authentication is not implemented yet. An earlier valid command can still be replayed because this design has no nonce or counter. Sources: https://github.com/Mbed-TLS/mbedtls and https://www.rfc-editor.org/rfc/rfc4231.html'
 },
 {
  title:'Keeping control running',
  lines:['Bound the receive queue and command length','Limit serial work to 32 bytes and one tag check per cycle','Discard malformed input and expire partial commands','Measure whether heavy input delays the control step'],
  notes:'C requires explicit checks around buffers and conversions. The proposed receive queue holds 256 bytes, and a command line is limited to 128 bytes before its newline. A partial line expires after 500 milliseconds. These limits are intended to keep input work from taking over the control loop. I will test a malformed stream of 1000 bytes per second and inject a sensor fault during that stream. The valve must still close at the next scheduled control step. These timing limits are targets, not measured firmware results. Sources: testing design L01; https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/'
 },
 {
  title:'Tests completed on Windows',
  lines:['69 independent control cases','18 steps that preserve the previous state','23 parser files, including expected failures','3 command-line error checks'],
  notes:'These are results from the native C programs on Windows with MinGW GCC 16.1.0. The 69 cases include the original 15 and 54 added boundary cases. The sequence test checks decisions over time and recovery from faults. The 23 parser files include four accepted inputs, 18 rejected files, and one deliberately wrong expected result. The runner correctly reports that mismatch. I am not combining these different checks into a coverage percentage. They do not test the future authentication or firmware timing. Source: Evidence/Windows_Host/summary.json in the November 12 package.'
 },
 {
  title:'Planned system tests',
  lines:['Normal filling and draining, then changes in demand','Old or invalid sensor readings and recovery','Modified commands, invalid values, and replay behavior','Long runs, slow sampling, and heavy serial input'],
  notes:'The default tank model will hold 100 liters and start at 50 liters, with 2 liters per second entering through an open inlet and 1 liter per second leaving. A normal run will last 600 simulated seconds and repeat three times. I will also test a shortage and a valve forced open. Those cases distinguish an incorrect controller decision from a condition the controller cannot physically correct. These tests are specified in files, but the model and adapter still need implementation. Source: Test_Data/Planned and the November 12 testing design.'
 },
 {
  title:'What comes next',
  lines:['Connect changing sensor input and periodic sampling','Add serial parsing and HMAC verification','Run the tank scenarios and record the real results','Use those results in the December report and presentation'],
  notes:'The host control tests and the fixed-reading firmware give me a starting point. My next step is to verify the sensor and timer path in Renode, then add the command handling and connect the model. I have a common host runner for Windows, macOS, and Linux, but the expanded tests have only run on Windows so far. I will keep unavailable tools and unfinished tests visible in the final report. The goal is a complete, repeatable evaluation, not just a successful boot message. I can take questions about the control rule, test inputs, or security limits.'
 }
];

const p = Presentation.create({slideSize:{width:1280,height:720}});
function text(slide,name,value,x,y,w,h,size=30,bold=false,color='#111111') {
 const shape=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=value;
 shape.text.style={fontFamily:'Arial',fontSize:size,bold,color};
 shape.text.insets=0;
 return shape;
}
await fs.mkdir(path.join(build,'design-previews'),{recursive:true});
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
 await fs.writeFile(path.join(build,'design-previews',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(build,'design-candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(output,'Design_Presentation_Finley_Burns_Reviewed.pptx');
const result=await finalizePresentation({
 workspaceDir,candidatePath:candidate,finalPath,
 pythonExecutable:path.join(runtime,'dependencies/python/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'design-reviewed-validation.json')
});
await fs.writeFile(path.join(output,'Speaking_Notes.txt'),slides.map((s,i)=>`SLIDE ${i+1} - ${s.title.replaceAll('\n',' ')}\n\n${s.notes}\n`).join('\n'));
await fs.writeFile(path.join(workspaceDir,'next-submissions/Authoring/design_slides.json'),JSON.stringify(slides,null,2)+'\n');
console.log(JSON.stringify({finalPath,result},null,2));
