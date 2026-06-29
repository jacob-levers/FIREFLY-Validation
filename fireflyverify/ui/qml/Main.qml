import QtQuick
import QtQuick.Layouts
import "components"

// FIREFLY-VERIFICATION shell: header wordmark + sliding TabBar + page Loader.
Item {
    id: root
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale

    readonly property var tabUrls: [
        "tabs/GroundTruthTab.qml",
        "tabs/MethodsTab.qml",
        "tabs/ResultsTab.qml",
        "tabs/ReportTab.qml",
    ]

    Rectangle {
        anchors.fill: parent
        color: pal.BG

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ── header ────────────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                color: pal.PANEL

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: sc.sp8
                    anchors.rightMargin: sc.sp8
                    spacing: sc.sp4

                    Text { text: "FIRE"; color: pal.TXT; font.pixelSize: sc.textXl; font.weight: Font.Bold }
                    Text { text: "FLY";  color: pal.ACC; font.pixelSize: sc.textXl; font.weight: Font.Bold
                           Layout.leftMargin: -sc.sp3 }
                    Text { text: "VERIFICATION"; color: pal.TXT_MUTED; font.pixelSize: sc.textSm
                           font.weight: Font.DemiBold; font.letterSpacing: 2
                           Layout.leftMargin: sc.sp3; Layout.alignment: Qt.AlignVCenter }

                    Item { Layout.fillWidth: true }

                    Text { text: "v" + appVersion; color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
                }
                Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                            height: 1; color: pal.BORDER }
            }

            // ── tab bar ───────────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 46
                color: pal.BG
                TabBar {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: sc.sp6
                    model: [
                        { t: "Ground Truth", icon: "database" },
                        { t: "Methods",      icon: "git-compare" },
                        { t: "Results",      icon: "chart-spline" },
                        { t: "Report",       icon: "table" },
                    ]
                    current: App.currentTab
                    onPicked: (i) => App.setTab(i)
                }
                Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                            height: 1; color: pal.BORDER }
            }

            // ── page ──────────────────────────────────────────────────────
            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                source: root.tabUrls[App.currentTab]
            }
        }
    }
}
