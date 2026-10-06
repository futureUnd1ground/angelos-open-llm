import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class HelperMainTests(unittest.TestCase):
 def test_registration_pages_and_story_guard(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def write(name,text):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
   write('Main.qml',(ROOT/'Main.qml').read_text())
   write('qmldir','singleton Bridge 1.0 Bridge.qml\n')
   write('Bridge.qml','''pragma Singleton
import QtQuick
QtObject { property var plugin; property string helperUrl: "file:///helper.qml"; property bool cancelled: false; function cancel() { cancelled=true } signal helperAnswered(string answer) }''')
   write('imports/qs/services/qmldir','module qs.services\nsingleton Angel 1.0 Angel.qml\nsingleton Novel 1.0 Novel.qml\nsingleton I18n 1.0 I18n.qml\nsingleton Shell 1.0 Shell.qml\n')
   write('imports/qs/services/Angel.qml','''pragma Singleton
import QtQuick
QtObject {
 property var assistant: null; property string assistantId: ""; property bool shown: true; property string transition: "";
 property string menu: ""; property string spoken: ""; property var actions: [];
 function registerAssistant(id,p) { if (assistant && assistant!==p) return false; assistant=p; assistantId=id; return true }
 function unregisterAssistant(id,p) { if (assistantId===id && assistant===p) { assistant=null; assistantId="" } }
 function openMenu(mode) { menu=mode }
 function say(text,acts,ms,silent) { spoken=text; actions=acts }
}''')
   write('imports/qs/services/Novel.qml','pragma Singleton\nimport QtQuick\nQtObject { property bool wantsClick: false }')
   write('imports/qs/services/I18n.qml','pragma Singleton\nimport QtQuick\nQtObject { function t(ru,en) { return en } }')
   write('imports/qs/services/Shell.qml','pragma Singleton\nimport QtQuick\nQtObject { property string page: ""; function openSettings(value) { page=value } }')
   write('tst_helper.qml','''import QtQuick
import QtTest
import qs.services
import "."
TestCase {
 name:"HelperIntegration"
 Main { id:main; plugin:({id:"open-llm"}) }
 function test_pages_and_registration() {
   compare(Angel.assistant,Bridge); compare(Angel.assistantId,"open-llm");
   Bridge.helperAnswered("x".repeat(800)); compare(main.pages.length,3); verify(Angel.spoken.startsWith("Open LLM · 1/3"));
   Angel.actions[0].run(); verify(Angel.spoken.startsWith("Open LLM · 2/3"));
   Angel.actions[1].run(); compare(Angel.menu,"assistant"); Angel.actions[2].run(); compare(Shell.page,"plugin:open-llm");
   Novel.wantsClick=true; const before=Angel.spoken; Bridge.helperAnswered("new"); compare(Angel.spoken,before); Novel.wantsClick=false;
   Angel.unregisterAssistant("other",Bridge); compare(Angel.assistant,Bridge);
   Angel.unregisterAssistant("open-llm",Bridge); compare(Angel.assistant,null);
   Bridge.helperAnswered("inactive"); compare(Angel.spoken,before);
 }
}''')
   result=subprocess.run(['/usr/lib/qt6/bin/qmltestrunner','-input',tmp,'-import',str(root/'imports')],capture_output=True,text=True,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'},timeout=30)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
