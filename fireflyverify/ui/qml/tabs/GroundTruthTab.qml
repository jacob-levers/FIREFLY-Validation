import QtQuick

Rectangle {
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    color: pal.BG
    Column {
        anchors.centerIn: parent
        spacing: sc.sp4
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Ground Truth"; color: pal.TXT
               font.pixelSize: sc.textXl; font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Import a ground-truth file (CSV / ISBI-2012 XML) or simulate a known-truth dataset."
               color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
    }
}
