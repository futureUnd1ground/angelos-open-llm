import QtQuick
import qs.services
import "."
Item {
    id: root
    property var plugin
    property var pages: []
    property int pageIndex: 0
    function register() {
        if (!plugin) return
        Bridge.plugin=plugin
        if (typeof Angel.registerAssistant === "function") Angel.registerAssistant(plugin.id,Bridge)
    }
    onPluginChanged: register()
    Component.onCompleted: register()
    Component.onDestruction: {
        if (typeof Angel.unregisterAssistant === "function" && plugin) Angel.unregisterAssistant(plugin.id,Bridge)
        Bridge.cancel()
    }
    function showAnswer(answer) {
        const chars=Array.from(String(answer))
        pages=[]
        for (let start=0; start<chars.length; start+=360) pages.push(chars.slice(start,start+360).join(""))
        pageIndex=0
        showPage()
    }
    function showPage() {
        if (!Angel.shown || Angel.transition || Novel.wantsClick || Angel.assistant !== Bridge) return
        const acts=[]
        if (pageIndex+1<pages.length) acts.push({label:I18n.t("Дальше", "Next"),icon:"arrow-right",run:()=>{ pageIndex++; showPage() }})
        acts.push({label:I18n.t("Ещё спросить", "Ask again"),icon:"chat",run:()=>Angel.openMenu("assistant")})
        acts.push({label:I18n.t("Весь чат", "Full chat"),icon:"bot",run:()=>Shell.openSettings("plugin:open-llm")})
        Angel.say("Open LLM"+(pages.length>1 ? " · "+(pageIndex+1)+"/"+pages.length : "")+"\n"+pages[pageIndex],acts,45000,true)
    }
    Connections {
        target: Bridge
        function onHelperAnswered(answer) { root.showAnswer(answer) }
    }
}
