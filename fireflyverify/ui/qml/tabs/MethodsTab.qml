import QtQuick

Rectangle {
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    color: pal.BG
    Column {
        anchors.centerIn: parent
        spacing: sc.sp4
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Methods"; color: pal.TXT
               font.pixelSize: sc.textXl; font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Load FIREFLY and palmTRACER output folders to score against the ground truth."
               color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
    }
}
