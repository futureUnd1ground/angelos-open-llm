import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class BridgeTests(unittest.TestCase):
 def test_agent_state_and_process_transport(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def write(name,text):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   write('Bridge.qml',(ROOT/'Bridge.qml').read_text().replace('id: root','id: root\n    property alias testWorker: worker',1).replace('property Process worker: Process {','property Process worker: Process {\n        id: worker'))
   write('Backends.js',(ROOT/'Backends.js').read_text());write('qmldir','singleton Bridge 1.0 Bridge.qml\n')
   write('imports/qs/services/qmldir','module qs.services\n')
   write('imports/Quickshell/Io/qmldir','module Quickshell.Io\nProcess 1.0 Process.qml\nSplitParser 1.0 SplitParser.qml\nStdioCollector 1.0 StdioCollector.qml\n')
   write('imports/Quickshell/Io/Process.qml','import QtQuick\nItem { property var command: []; property bool running: false; property bool stdinEnabled: true; property QtObject stdout; property QtObject stderr; property string written: ""; function write(text) { written+=text } signal started; signal exited(int code,int exitStatus) }')
   write('imports/Quickshell/Io/SplitParser.qml','import QtQuick\nQtObject { signal read(string data) }')
   write('imports/Quickshell/Io/StdioCollector.qml','import QtQuick\nQtObject { property string text: "" }')
   write('tst_bridge.qml','''import QtQuick
import QtTest
import "."
TestCase {
 name: "OpenLlmBridge"
 property var prefs: ({model:"qwen3:4b"})
 function init() {
   Bridge.testWorker.running=false; Bridge.stopping=false; Bridge.pending=[]; Bridge.messages=[]; Bridge.helperMood=""; Bridge.helperTurn=false; Bridge.transcript="";
   prefs={model:"qwen3:4b"}; Bridge.plugin={dir:"/plugin",url:path=>"file:///plugin/"+path,get:(k,d)=>prefs[k]===undefined?d:prefs[k],set:(k,v)=>{prefs[k]=v}};
   Bridge.revision++;
 }
 SignalSpy { id: reply; target: Bridge; signalName: "helperAnswered" }
 function finish() { Bridge.testWorker.running=false; Bridge.testWorker.exited(0,0) }
 function test_transport_and_confirmation() {
   Bridge.ask("Сделай темно"); verify(Bridge.busy);
   compare(Bridge.testWorker.command,["python3","/plugin/scripts/backend.py"]);
   const req=JSON.parse(Bridge.payload); compare(req.config.model,"qwen3:4b"); compare(req.messages[0].content,"Сделай темно");
   Bridge.testWorker.started(); verify(!Bridge.testWorker.stdinEnabled); compare(JSON.parse(Bridge.testWorker.written).op,"chat");
   const call={id:"c",function:{name:"set_theme",arguments:'{"mode":"dark"}'}};
   Bridge.event({type:"state",messages:req.messages.concat([{role:"assistant",tool_calls:[call]}]),pending:[call],rounds:1}); finish();
   compare(Bridge.pending.length,1); Bridge.backend("lmstudio"); compare(Bridge.get("backend","ollama"),"ollama");
   Bridge.resolve(false); compare(JSON.parse(Bridge.payload).approved,false); compare(JSON.parse(Bridge.payload).config.url,"http://127.0.0.1:11434");
   Bridge.event({type:"checkpoint",messages:req.messages}); compare(Bridge.pending.length,0);
   Bridge.event({type:"error",message:"Connection lost"}); finish(); compare(Bridge.status,"Connection lost"); compare(Bridge.messages,req.messages);
 }
 function test_helper_reply_waits_for_confirmation() {
   reply.clear(); verify(Bridge.askFromHelper("dark")); verify(Bridge.helperTurn); compare(Bridge.helperMood,"thinking");
   Bridge.event({type:"assistant",text:"Planning"});
   Bridge.event({type:"state",messages:Bridge.messages,pending:[{id:"x"}],rounds:1}); compare(reply.count,0);
   Bridge.event({type:"state",messages:Bridge.messages,pending:[],rounds:0}); compare(reply.count,1); verify(!Bridge.helperTurn); compare(Bridge.helperMood,"happy");
   finish(); Bridge.ask("settings prompt"); Bridge.event({type:"assistant",text:"Other"});
   Bridge.event({type:"state",messages:Bridge.messages,pending:[],rounds:0}); compare(reply.count,1); finish();
 }
 function test_model_change_progress_and_cancel() {
   Bridge.backend("lmstudio"); compare(Bridge.config.url,"http://127.0.0.1:1234/v1"); compare(Bridge.config.model,"");
   Bridge.set("model","local"); Bridge.run("pull",{model:"local"}); Bridge.event({type:"progress",message:"Downloading",completed:2,total:4}); compare(Bridge.status,"Downloading · 50%");
   Bridge.cancel(); verify(Bridge.busy); Bridge.event({type:"runtime",message:"late"}); verify(Bridge.status.indexOf("Отменено")===0);
   Bridge.testWorker.exited(15,0); verify(!Bridge.busy); verify(Bridge.testWorker.stdinEnabled);
 }
}''')
   result=subprocess.run(['/usr/lib/qt6/bin/qmltestrunner','-input',tmp,'-import',str(root/'imports')],capture_output=True,text=True,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'},timeout=30)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
