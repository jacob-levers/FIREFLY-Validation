import QtQuick
import QtQuick.Layouts
import "../components"

// Report: export the comparison as CSV or a one-page PDF, with a compact preview.
Rectangle {
    id: root
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    readonly property var cards: Verify.scorecards
    color: pal.BG

    Column {
        anchors.centerIn: parent
        visible: !Verify.hasResults
        spacing: sc.sp4
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Nothing to report yet"
               color: pal.TXT; font.pixelSize: sc.textLg; font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Score the methods first (Methods tab), then export the comparison here."
               color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
    }

    ColumnLayout {
        width: Math.min(1000, parent.width - sc.sp10 * 2)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: sc.sp12
        visible: Verify.hasResults
        spacing: sc.sp6

        Card {
            Layout.fillWidth: true
            implicitHeight: exp.implicitHeight + sc.sp8
            RowLayout {
                id: exp
                x: sc.sp6; y: sc.sp4; width: parent.width - sc.sp6 * 2; spacing: sc.sp4
                ColumnLayout { spacing: 0
                    Text { text: "Export comparison"; color: pal.TXT; font.pixelSize: sc.textMd; font.weight: Font.Bold }
                    Text { text: "ISBI-2012 metrics for FIREFLY vs palmTRACER against the ground truth."
                           color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                }
                Item { Layout.fillWidth: true }
                Button { text: "Export CSV"; icon: "table"; variant: "secondary"
                         onClicked: Verify.chooseReportPath("csv") }
                Button { text: "Export PDF"; icon: "download"; variant: "primary"
                         onClicked: Verify.chooseReportPath("pdf") }
            }
        }

        // compact preview
        Card {
            Layout.fillWidth: true
            implicitHeight: prev.implicitHeight + sc.sp10
            ColumnLayout {
                id: prev
                x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2; spacing: sc.sp3
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Tool"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs; font.weight: Font.DemiBold; Layout.preferredWidth: 160 }
                    Text { text: "F1"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                    Text { text: "Track α"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                    Text { text: "Track JSC"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                    Text { text: "Loc RMSE (nm)"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: pal.BORDER }
                Repeater {
                    model: root.cards
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { text: modelData.tool; color: pal.ACC; font.pixelSize: sc.textSm; font.weight: Font.Bold; Layout.preferredWidth: 160 }
                        Text { text: modelData.f1 !== null ? modelData.f1.toFixed(3) : "—"; color: pal.TXT; font.pixelSize: sc.textSm; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                        Text { text: modelData.alpha !== null ? modelData.alpha.toFixed(3) : "—"; color: pal.TXT; font.pixelSize: sc.textSm; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                        Text { text: modelData.jsc !== null ? modelData.jsc.toFixed(3) : "—"; color: pal.TXT; font.pixelSize: sc.textSm; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                        Text { text: modelData.rmse_nm !== null ? modelData.rmse_nm.toFixed(0) : "—"; color: pal.TXT; font.pixelSize: sc.textSm; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                    }
                }
            }
        }
        Item { Layout.fillHeight: true }
    }
}
