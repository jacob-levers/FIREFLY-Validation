import QtQuick
import QtQuick.Layouts
import "../components"

// Results: detection / tracking / diffusion scorecards (FIREFLY vs palmTRACER)
// + a comparison figure.
Rectangle {
    id: root
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    readonly property var cards: Verify.scorecards
    property string figKind: "summary"

    readonly property var detMetrics: [
        { k: "f1", l: "F1" }, { k: "jaccard", l: "Jaccard" },
        { k: "precision", l: "Precision" }, { k: "recall", l: "Recall" },
        { k: "rmse_nm", l: "Loc RMSE (nm)" }, { k: "n_matched", l: "Matched spots" }]
    readonly property var trkMetrics: [
        { k: "alpha", l: "α (sensitivity)" }, { k: "beta", l: "β (w/ spurious)" },
        { k: "jsc", l: "JSC (points)" }, { k: "jsc_theta", l: "JSCθ (tracks)" },
        { k: "track_rmse_nm", l: "Track RMSE (nm)" }, { k: "n_tracks", l: "Est. tracks" }]

    function fmt(v, key) {
        if (v === null || v === undefined) return "—"
        if (key === "n_tracks" || key === "n_matched") return Math.round(v) + ""
        if (key.indexOf("rmse") >= 0) return v.toFixed(0)
        return v.toFixed(3)
    }
    function refreshFig() { Verify.renderFigure(figKind, figImg.width, figImg.height) }
    onFigKindChanged: refreshFig()

    color: pal.BG

    // empty state
    Column {
        anchors.centerIn: parent
        visible: !Verify.hasResults
        spacing: sc.sp4
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "No results yet"
               color: pal.TXT; font.pixelSize: sc.textLg; font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: "Load method outputs and press “Score vs ground truth” on the Methods tab."
               color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
    }

    Flickable {
        anchors.fill: parent
        visible: Verify.hasResults
        contentWidth: width
        contentHeight: col.implicitHeight + sc.sp10 * 2
        clip: true

        ColumnLayout {
            id: col
            width: Math.min(1100, parent.width - sc.sp10 * 2)
            anchors.horizontalCenter: parent.horizontalCenter
            y: sc.sp10
            spacing: sc.sp6

            // ── comparison table (Detection + Tracking) ───────────────────
            Card {
                Layout.fillWidth: true
                implicitHeight: tblCol.implicitHeight + sc.sp10
                ColumnLayout {
                    id: tblCol
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2; spacing: sc.sp4

                    // header
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Metric"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs
                               font.weight: Font.DemiBold; Layout.preferredWidth: 200 }
                        Repeater { model: root.cards
                            delegate: Text { required property var modelData
                                             text: modelData.tool; color: pal.ACC
                                             font.pixelSize: sc.textSm; font.weight: Font.Bold
                                             horizontalAlignment: Text.AlignRight
                                             Layout.fillWidth: true } }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: pal.BORDER }

                    Text { text: "DETECTION"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs
                           font.weight: Font.Bold; font.letterSpacing: 1.5; Layout.topMargin: sc.sp2 }
                    Repeater {
                        model: root.detMetrics
                        delegate: RowLayout {
                            id: drow
                            required property var modelData
                            Layout.fillWidth: true
                            Text { text: drow.modelData.l; color: pal.TXT; font.pixelSize: sc.textSm
                                   Layout.preferredWidth: 200 }
                            Repeater { model: root.cards
                                delegate: Text { required property var modelData
                                                 text: root.fmt(modelData[drow.modelData.k], drow.modelData.k)
                                                 color: pal.TXT; font.pixelSize: sc.textSm
                                                 horizontalAlignment: Text.AlignRight; Layout.fillWidth: true } }
                        }
                    }

                    Text { text: "TRACKING (ISBI-2012)"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs
                           font.weight: Font.Bold; font.letterSpacing: 1.5; Layout.topMargin: sc.sp4 }
                    Repeater {
                        model: root.trkMetrics
                        delegate: RowLayout {
                            id: trow
                            required property var modelData
                            Layout.fillWidth: true
                            Text { text: trow.modelData.l; color: pal.TXT; font.pixelSize: sc.textSm
                                   Layout.preferredWidth: 200 }
                            Repeater { model: root.cards
                                delegate: Text { required property var modelData
                                                 text: root.fmt(modelData[trow.modelData.k], trow.modelData.k)
                                                 color: pal.TXT; font.pixelSize: sc.textSm
                                                 horizontalAlignment: Text.AlignRight; Layout.fillWidth: true } }
                        }
                    }
                }
            }

            // ── diffusion recovery ────────────────────────────────────────
            Card {
                Layout.fillWidth: true
                implicitHeight: difCol.implicitHeight + sc.sp10
                ColumnLayout {
                    id: difCol
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2; spacing: sc.sp4
                    Text { text: "DIFFUSION RECOVERY (D µm²/s)"; color: pal.TXT_MUTED
                           font.pixelSize: sc.textXs; font.weight: Font.Bold; font.letterSpacing: 1.5 }
                    Repeater {
                        model: root.cards
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true; spacing: sc.sp2
                            Text { text: modelData.tool; color: pal.ACC; font.pixelSize: sc.textSm
                                   font.weight: Font.Bold }
                            Text { visible: !modelData.diffusion || modelData.diffusion.length === 0
                                   text: "no reported D — enable common re-fit on the Methods tab"
                                   color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            Repeater { model: modelData.diffusion
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Text { text: modelData.pop; color: pal.TXT; font.pixelSize: sc.textSm
                                           Layout.preferredWidth: 140 }
                                    Text { text: "truth " + (modelData.D_true !== null ? modelData.D_true.toFixed(3) : "—")
                                           color: pal.TXT_MUTED; font.pixelSize: sc.textSm; Layout.preferredWidth: 120 }
                                    Text { text: "est " + (modelData.D_est !== null ? modelData.D_est.toFixed(3) : "—")
                                           color: pal.TXT; font.pixelSize: sc.textSm; Layout.preferredWidth: 120 }
                                    Text { text: (modelData.bias_pct !== null ? (modelData.bias_pct >= 0 ? "+" : "") + modelData.bias_pct.toFixed(1) + "% bias" : "")
                                           color: modelData.bias_pct !== null && Math.abs(modelData.bias_pct) < 15 ? pal.SUCCESS : pal.WARN
                                           font.pixelSize: sc.textSm; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }
            }

            // ── figure ────────────────────────────────────────────────────
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 480
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: sc.sp5; spacing: sc.sp3
                    RowLayout { spacing: sc.sp3
                        Text { text: "Figure"; color: pal.TXT; font.pixelSize: sc.textMd; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Select { model: ["summary", "d_dist", "confusion", "overlay"]
                                 onPicked: (t) => root.figKind = t }
                    }
                    Image {
                        id: figImg
                        Layout.fillWidth: true; Layout.fillHeight: true
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        source: "image://figure/" + root.figKind + "/" + Verify.figureToken
                    }
                }
            }
        }
    }
}
