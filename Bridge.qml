pragma Singleton
import QtQuick
import Quickshell.Io
import "Backends.js" as Backends

QtObject {
    id: root
    property var plugin: null
    readonly property string helperTitle: "Open LLM"
    readonly property string helperUrl: plugin ? plugin.url("Helper.qml") : ""
    property bool helperTurn: false
    property string helperAnswerText: ""
    signal helperAnswered(string answer)
    property int revision: 0
    property var modelNames: []
    property var messages: []
    property var pending: []
    property int rounds: 0
    property var turnConfig: ({})
    property var beforeMessages: []
    property string transcript: ""
    property string status: "Готов"
    property bool hasKey: false
    property bool failed: false
    property bool cancelled: false
    property bool stopping: false
    property string payload: ""
    property string operation: ""
    readonly property bool busy: worker.running || stopping
    readonly property var config: {
        revision
        const backend = get("backend", "ollama")
        const preset = Backends.preset(backend)
        const mode = get("mode", "confirm")
        return {url:get("url", preset.url), protocol:preset.protocol, model:get("model", ""),
                toolsEnabled:mode !== "chat", autoActions:mode === "auto", maxSteps:Number(get("maxSteps", 8))}
    }
    function get(key, fallback) { return plugin ? plugin.get(key, fallback) : fallback }
    function set(key, value) {
        if (!plugin || busy || pending.length) return
        plugin.set(key, value)
        revision++
    }
    function backend(value) {
        if (busy || pending.length) return
        set("backend",value); set("url",Backends.preset(value).url); set("model","")
        modelNames=[]; hasKey=false; clear()
    }
    function clear() {
        if (busy || pending.length) return
        messages=[]; transcript=""; rounds=0; helperTurn=false; helperAnswerText=""
    }
    function run(op, extra) {
        if (!plugin || busy) return
        operation=op; cancelled=false; failed=false; status="Работаю…"
        payload=JSON.stringify(Object.assign({op:op, config:config},extra || {}))
        worker.command=["python3",plugin.dir+"/scripts/backend.py"]
        worker.running=true
    }
    function askFromHelper(prompt) { return ask(prompt,true) }
    function ask(prompt, fromHelper) {
        prompt=String(prompt).trim()
        if (!prompt || busy || pending.length) return false
        if (!config.model) { status="Сначала выбери или скачай модель."; return false }
        if (messages.length>120) { status="Очисти длинную историю, чтобы начать новый чат."; return false }
        helperTurn=fromHelper === true; helperAnswerText=""
        beforeMessages=messages.slice()
        messages=messages.concat([{role:"user",content:prompt}])
        transcript+="\nТы: "+prompt+"\n"
        turnConfig=Object.assign({},config)
        run("chat",{config:turnConfig,messages:messages,rounds:0})
        return true
    }
    function resolve(approved) {
        if (busy || !pending.length) return
        beforeMessages=messages.slice()
        run("resolve",{config:turnConfig,messages:messages,pending:pending,rounds:rounds,approved:approved})
    }
    function cancel() {
        if (!busy) return
        helperTurn=false; cancelled=true; stopping=true; worker.running=false
        if (operation === "chat" || operation === "resolve") messages=beforeMessages.slice()
        status="Отменено. Уже выполненные действия остаются в силе."
    }
    function event(event) {
        if (cancelled) return
        if (event.type === "checkpoint") {
            messages=event.messages; beforeMessages=event.messages.slice(); pending=[]
        } else if (event.type === "assistant") {
            transcript+="\nМодель: "+event.text+"\n"
            if (helperTurn) helperAnswerText+=(helperAnswerText ? "\n\n" : "")+event.text
        }
        else if (event.type === "tool") transcript+="\nИнструмент "+event.name+": "+JSON.stringify(event.result)+"\n"
        else if (event.type === "state") {
            messages=event.messages; pending=event.pending; rounds=event.rounds
            status=pending.length ? "Подтверди изменения ниже" : "Готов"
            if (helperTurn && !pending.length) {
                helperTurn=false
                helperAnswered(helperAnswerText || "Модель завершила ответ без текста. Результаты инструментов — в чате.")
            }
        } else if (event.type === "error") {
            failed=true; status=event.message
            if (helperTurn && !pending.length) { helperTurn=false; helperAnswered(event.message) }
        } else if (event.type === "models") {
            modelNames=event.models; hasKey=event.hasKey; status="Моделей: "+modelNames.length
        } else if (event.type === "credentials") {
            hasKey=event.hasKey; status=hasKey ? "API-ключ сохранён для этого адреса" : "API-ключ удалён"
        } else if (event.type === "progress") {
            status=event.message+(event.total>0 ? " · "+Math.floor(100*event.completed/event.total)+"%" : "")
        } else if (event.message) status=event.message
    }
    property Process worker: Process {
        stdinEnabled: true
        onStarted: { write(root.payload); stdinEnabled=false; root.payload="" }
        stdout: SplitParser {
            onRead: data => {
                try { root.event(JSON.parse(data)) }
                catch (e) { root.status="Неверный ответ помощника: "+String(e) }
            }
        }
        stderr: StdioCollector { id: errors }
        onExited: (code, exitStatus) => {
            stdinEnabled=true; root.stopping=false
            if (!root.cancelled && code !== 0 && !root.failed) root.status=errors.text.trim() || "Процесс завершился с ошибкой"
        }
    }
}
