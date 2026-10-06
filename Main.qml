import QtQuick
import qs.services
import "."
Item {
    property var plugin
    onPluginChanged: if (plugin) Bridge.plugin=plugin
    Component.onCompleted: if (plugin) Bridge.plugin=plugin
}
