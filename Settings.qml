import QtQuick
import qs.config
import qs.services
import qs.widgets
import "."
import "Backends.js" as Backends

Column {
    id: root
    property var plugin
    width: parent ? parent.width : 500
    spacing: Theme.u*4
    onPluginChanged: if (plugin) Bridge.plugin=plugin
    Component.onCompleted: if (plugin) Bridge.plugin=plugin
    readonly property bool locked: Bridge.busy || Bridge.pending.length>0
    PxText {
        width: parent.width; wrapMode: Text.Wrap
        text: "Общайся с моделью и управляй AngelOS одним промптом. Возможности и качество зависят от модели: для действий ей нужна поддержка tools."
    }
    PxText { width: parent.width; wrapMode: Text.Wrap; text: Bridge.status }
    PxGroup {
        width: parent.width; title: "Подключение"; icon: "plug"
        PxCombo {
            width: parent.width; enabled: !root.locked
            model: Backends.presets; currentValue: Bridge.get("backend","ollama")
            onActivated: value => Bridge.backend(value)
        }
        PxField {
            width: parent.width; enabled: !root.locked
            text: Bridge.config.url; placeholder: "Адрес сервера"
            onEdited: { Bridge.set("url",text); Bridge.modelNames=[]; Bridge.hasKey=false; Bridge.clear() }
        }
        Flow {
            width: parent.width; spacing: Theme.u*3
            PxButton { text: "Обновить список моделей"; enabled: !root.locked; onClicked: Bridge.run("models") }
            PxButton { text: "Новый чат"; enabled: !root.locked; onClicked: Bridge.clear() }
        }
        PxCombo {
            width: parent.width; enabled: !root.locked
            model: Bridge.modelNames.map(name => ({label:name,value:name})); currentValue: Bridge.config.model
            onActivated: value => { Bridge.set("model",value); Bridge.clear() }
        }
        PxField {
            width: parent.width; enabled: !root.locked; text: Bridge.config.model; placeholder: "Или введи ID модели вручную"
            onEdited: { Bridge.set("model",text); Bridge.clear() }
        }
        PxField { id: apiKey; width: parent.width; password: true; enabled: !root.locked; placeholder: "API-ключ (для локальной модели обычно не нужен)" }
        Flow {
            width: parent.width; spacing: Theme.u*3
            PxButton { text: "Сохранить ключ"; enabled: !root.locked && apiKey.text.length>0; onClicked: { Bridge.run("credentials",{key:apiKey.text}); apiKey.text="" } }
            PxButton { text: "Удалить ключ"; enabled: !root.locked; onClicked: Bridge.run("credentials",{key:""}) }
        }
        PxText { width: parent.width; wrapMode: Text.Wrap; dim: true; text: "Ключ хранится отдельно, с правами 600 и привязкой к URL. Промпты, результаты инструментов и история отправляются только выбранному серверу. История чата хранится в памяти." }
    }
    PxGroup {
        width: parent.width; title: "Скачать локальную модель"; icon: "download"
        PxText { width: parent.width; wrapMode: Text.Wrap; text: "Ollama запускается на твоём компьютере. Установка runtime занимает около 1,44 ГБ загрузки; нужно 6 ГБ свободного места. Модель скачивается отдельно. Установка не требует sudo." }
        Flow {
            width: parent.width; spacing: Theme.u*3
            PxButton { text: "Установить Ollama"; enabled: !root.locked; onClicked: Bridge.run("install") }
            PxButton { text: "Запустить сервер"; enabled: !root.locked && Bridge.config.protocol === "ollama"; onClicked: Bridge.run("start") }
        }
        PxCombo {
            id: downloadChoice; width: parent.width; enabled: !root.locked
            property string chosen: "qwen3:4b"
            model: [{label:"Qwen3 1.7B · 1,4 ГБ",value:"qwen3:1.7b"},{label:"Qwen3 4B · 2,5 ГБ",value:"qwen3:4b"},{label:"Qwen3 8B · 5,2 ГБ",value:"qwen3:8b"}]
            currentValue: chosen
            onActivated: value => { chosen=value; downloadModel.text=value }
        }
        PxField { id: downloadModel; width: parent.width; enabled: !root.locked; text: "qwen3:4b"; placeholder: "Любой ID модели Ollama" }
        PxButton {
            text: "Скачать и выбрать модель"; enabled: !root.locked && Bridge.config.protocol === "ollama"
            onClicked: { Bridge.set("model",downloadModel.text.trim()); Bridge.clear(); Bridge.run("pull",{model:downloadModel.text.trim()}) }
        }
        PxText { width: parent.width; wrapMode: Text.Wrap; dim: true; text: "Скачивание доступно для локального Ollama. Другие серверы управляют файлами моделей через свои приложения. 4B — компактный стартовый вариант; качество сложных задач зависит от размера модели, её обучения и ресурсов компьютера." }
    }
    PxGroup {
        width: parent.width; title: "Агент"; icon: "bot"
        PxCombo {
            width: parent.width; enabled: !root.locked
            model: [{label:"Только чат",value:"chat"},{label:"Инструменты с подтверждением изменений",value:"confirm"},{label:"Автоматические действия AngelOS",value:"auto"}]
            currentValue: Bridge.get("mode","confirm")
            onActivated: value => Bridge.set("mode",value)
        }
        PxCombo {
            width: parent.width; enabled: !root.locked
            model: [{label:"До 4 шагов",value:4},{label:"До 8 шагов",value:8},{label:"До 16 шагов",value:16},{label:"До 24 шагов",value:24}]
            currentValue: Number(Bridge.get("maxSteps",8))
            onActivated: value => Bridge.set("maxSteps",Number(value))
        }
        PxText { width: parent.width; wrapMode: Text.Wrap; dim: true; text: "Окна, рабочие пространства, настройки, темы, обои из Pictures, музыка и громкость. Автоматический режим разрешает эти действия без отдельного подтверждения. Произвольного выполнения команд и доступа к личным документам нет." }
        PxTextArea { width: parent.width; readOnly: true; text: Bridge.transcript || "Пример: посмотри текущую тему, включи тёмную и проверь результат." }
        PxTextArea { id: prompt; width: parent.width; enabled: !root.locked; placeholder: "Что сделать в AngelOS?" }
        Flow {
            width: parent.width; spacing: Theme.u*3
            PxButton { text: "Отправить"; accent: true; enabled: !root.locked && prompt.text.trim().length>0; onClicked: { Bridge.ask(prompt.text); prompt.text="" } }
            PxButton { text: "Остановить"; enabled: Bridge.busy; onClicked: Bridge.cancel() }
        }
        PxText { width: parent.width; wrapMode: Text.Wrap; text: Bridge.status }
        PxText {
            visible: Bridge.pending.length>0; width: parent.width; wrapMode: Text.Wrap
            text: "Предлагаемые изменения:\n"+Bridge.pending.map(call => call.function.name+" "+call.function.arguments).join("\n")
        }
        Flow {
            visible: Bridge.pending.length>0; width: parent.width; spacing: Theme.u*3
            PxButton { text: "Применить"; accent: true; enabled: !Bridge.busy; onClicked: Bridge.resolve(true) }
            PxButton { text: "Отклонить"; enabled: !Bridge.busy; onClicked: Bridge.resolve(false) }
        }
    }
    PxText {
        width: parent.width; wrapMode: Text.Wrap; dim: true
        text: "В меню «Выполнить…»: llm твой запрос. Для внешнего MCP-клиента: python3 "+(root.plugin ? root.plugin.dir : "…")+"/scripts/mcp.py. По умолчанию MCP даёт только чтение; --allow-actions включает действия."
    }
}
