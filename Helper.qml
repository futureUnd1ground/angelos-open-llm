import QtQuick
import qs.config
import qs.services
import qs.widgets
import "."

Column {
    width: parent ? parent.width : Theme.u*142
    spacing: Theme.u*3
    PxText {
        width: parent.width; wrapMode: Text.Wrap; textFormat: Text.PlainText
        text: Bridge.status
        color: Angel.demon ? Theme.hellText : Theme.text
    }
    PxField {
        id: input
        width: parent.width; keepFocus: true; icon: "chat"
        enabled: !Bridge.busy && !Bridge.pending.length
        placeholder: I18n.t("Напиши запрос модели…", "Ask the model…")
        function send() { if (Bridge.askFromHelper(text)) text="" }
        onAccepted: send()
        onKeyPressed: event => {
            if (event.key === Qt.Key_Escape) { Angel.hush(); event.accepted=true }
        }
        Component.onCompleted: focusLater.start()
        Timer { id: focusLater; interval: 60; onTriggered: if (input.enabled) input.focusField() }
    }
    PxTextArea {
        width: parent.width; implicitHeight: Theme.u*50; readOnly: true
        visible: Bridge.pending.length>0
        text: Bridge.pending.map(call => call.function.name+" "+call.function.arguments).join("\n")
    }
    Flow {
        width: parent.width; spacing: Theme.u*2
        PxButton { hell: Angel.demon; compact: true; text: I18n.t("Отправить", "Send"); accent: true; visible: !Bridge.pending.length; enabled: !Bridge.busy && input.text.trim().length>0; onClicked: input.send() }
        PxButton { hell: Angel.demon; compact: true; text: I18n.t("Применить", "Apply"); accent: true; visible: Bridge.pending.length>0; enabled: !Bridge.busy; onClicked: Bridge.resolve(true) }
        PxButton { hell: Angel.demon; compact: true; text: I18n.t("Отклонить", "Reject"); visible: Bridge.pending.length>0; enabled: !Bridge.busy; onClicked: Bridge.resolve(false) }
        PxButton { hell: Angel.demon; compact: true; text: I18n.t("Остановить", "Stop"); visible: Bridge.busy; onClicked: Bridge.cancel() }
        PxButton { hell: Angel.demon; compact: true; text: I18n.t("Чат и модели", "Chat and models"); onClicked: { Angel.hush(); Shell.openSettings("plugin:open-llm") } }
    }
    PxText {
        width: parent.width; wrapMode: Text.Wrap; dim: true
        text: Bridge.config.model ? Bridge.config.model : I18n.t("Сначала выбери или скачай модель в настройках Open LLM.", "Choose or download a model in Open LLM settings first.")
    }
}
