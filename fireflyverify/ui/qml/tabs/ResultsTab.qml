import QtQuick

Rectangle {
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    color: pal.BG
    Column {
        anchors.centerIn: parent
        spacing: sc.sp4
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Results"; color: pal.TXT
               font.pixelSize: sc.textXl; font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Detection, tracking and diffusion scorecards — FIREFLY vs palmTRACER, side by side."
               color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
    }
}
