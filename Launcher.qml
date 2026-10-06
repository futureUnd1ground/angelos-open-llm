import QtQuick
import qs.services
import "."
Item {
    property var plugin
    property string pluginId
    readonly property string prefix: "llm"
    readonly property bool global: false
    signal changed
    function query(text, prefixed) {
        const prompt=String(text || "").trim()
        return [{id:prompt, title:prompt ? "Спросить модель: "+prompt : "Open LLM — чат и модели",
                 subtitle:"Локальные модели · инструменты AngelOS · скачивание",icon:"bot",score:160}]
    }
    function activate(id) {
        if (plugin) Bridge.plugin=plugin
        if (id) Bridge.ask(id)
        Shell.openSettings("plugin:open-llm")
        return false
    }
}
