import QtQuick
import QtQuick.Layouts
import "../components"

// Methods: load FIREFLY + palmTRACER output folders, then score vs the GT.
Rectangle {
    id: root
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    readonly property var gt: Verify.gtSummary
    readonly property var ms: Verify.methodsSummary
    property bool commonRefit: false

    function _card(parentItem, info, title, subtitle, icon, onLoad) {}

    color: pal.BG

    ColumnLayout {
        width: Math.min(1040, parent.width - sc.sp10 * 2)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        spacing: sc.sp6

        Alert {
            Layout.fillWidth: true
            visible: !(root.gt.loaded === true)
            severity: "warn"
            text: "Load or simulate a ground truth first (Ground Truth tab)."
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: sc.sp6

            // FIREFLY card
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 188
                ColumnLayout {
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2; spacing: sc.sp4
                    RowLayout { spacing: sc.sp3
                        Icon { name: "zap"; size: 18; color: pal.ACC }
                        Text { text: "FIREFLY"; color: pal.TXT; font.pixelSize: sc.textLg; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Badge { visible: root.ms.FIREFLY.loaded === true; text: "loaded"; tone: pal.SUCCESS; dot: true }
                    }
                    Button { text: "Load output folder…"; icon: "folder-open"; variant: "secondary"
                             onClicked: Verify.chooseFireflyFolder() }
                    RowLayout { spacing: sc.sp8; visible: root.ms.FIREFLY.loaded === true
                        MetricStat { label: "Tracks"; value: (root.ms.FIREFLY.n_tracks || 0) + "" }
                        MetricStat { label: "Localisations"; value: (root.ms.FIREFLY.n_locs || 0) + "" }
                        MetricStat { label: "Reported D"; value: root.ms.FIREFLY.has_D ? "yes" : "no"
                                     tone: root.ms.FIREFLY.has_D ? pal.SUCCESS : pal.TXT_MUTED }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // palmTRACER card
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 188
                ColumnLayout {
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2; spacing: sc.sp4
                    RowLayout { spacing: sc.sp3
                        Icon { name: "scan-search"; size: 18; color: "#f6a623" }
                        Text { text: "palmTRACER"; color: pal.TXT; font.pixelSize: sc.textLg; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Badge { visible: root.ms.palmTRACER.loaded === true; text: "loaded"; tone: pal.SUCCESS; dot: true }
                    }
                    Button { text: "Load output folder…"; icon: "folder-open"; variant: "secondary"
                             onClicked: Verify.choosePalmtracerFolder() }
                    RowLayout { spacing: sc.sp8; visible: root.ms.palmTRACER.loaded === true
                        MetricStat { label: "Tracks"; value: (root.ms.palmTRACER.n_tracks || 0) + "" }
                        MetricStat { label: "Localisations"; value: (root.ms.palmTRACER.n_locs || 0) + "" }
                        MetricStat { label: "Reported D"; value: root.ms.palmTRACER.has_D ? "yes" : "no"
                                     tone: root.ms.palmTRACER.has_D ? pal.SUCCESS : pal.TXT_MUTED }
                    }
                    Text { visible: root.ms.palmTRACER.loaded === true && !root.ms.palmTRACER.has_D
                           text: "No native D — enable common re-fit for a D comparison."
                           color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                    Item { Layout.fillHeight: true }
                }
            }
        }

        // score row
        Card {
            Layout.fillWidth: true
            implicitHeight: scoreRow.implicitHeight + sc.sp8
            RowLayout {
                id: scoreRow
                x: sc.sp6; y: sc.sp4; width: parent.width - sc.sp6 * 2; spacing: sc.sp4
                RowLayout { spacing: sc.sp3
                    Switch { checked: root.commonRefit; onToggled: (c) => root.commonRefit = c }
                    Text { text: "Common re-fit (recompute D for both tools with one fitter)"
                           color: pal.TXT; font.pixelSize: sc.textSm }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Score vs ground truth"; icon: "git-compare"; variant: "primary"; spin: Verify.busy
                    enabled: root.gt.loaded === true &&
                             (root.ms.FIREFLY.loaded === true || root.ms.palmTRACER.loaded === true)
                    onClicked: { Verify.score(root.commonRefit); App.setTab(2); }
                }
            }
        }
    }
}
