import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC
import "../components"

// Results: detection / tracking / diffusion scorecards (FIREFLY vs palmTRACER),
// each value rated (Excellent/Good/Fair/Poor) + explained, plus a comparison figure.
Rectangle {
    id: root
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    readonly property var cards: Verify.scorecards
    property string figKind: "summary"
    property bool showGuide: false

    // metric definitions: key, label, direction (up=higher better, down=lower
    // better, none=neutral count), and a plain-English explanation.
    readonly property var detMetrics: [
        { k: "f1", l: "F1", dir: "up", d: "Harmonic mean of precision and recall for per-frame spot detection. 1.0 = every true spot found, no false ones." },
        { k: "jaccard", l: "Jaccard", dir: "up", d: "Detection overlap, TP / (TP + FP + FN) per frame. 1.0 = perfect detection." },
        { k: "precision", l: "Precision", dir: "up", d: "Fraction of detected spots that are real (1 − false-positive rate)." },
        { k: "recall", l: "Recall", dir: "up", d: "Fraction of true spots that were detected (1 − miss rate)." },
        { k: "rmse_nm", l: "Loc RMSE (nm)", dir: "down", d: "Average position error of matched spots, in nm. Lower is better; the CRLB line on the figure is the theoretical best for this brightness." },
        { k: "n_matched", l: "Matched spots", dir: "none", d: "How many detections were paired to ground-truth spots." }]
    readonly property var trkMetrics: [
        { k: "alpha", l: "α (sensitivity)", dir: "up", d: "ISBI track sensitivity — how much of the true trajectories were recovered. 1.0 = every GT track point correctly followed." },
        { k: "beta", l: "β (w/ spurious)", dir: "up", d: "Like α, but penalised for spurious (false) tracks. β ≤ α; the gap is the false-track burden." },
        { k: "jsc", l: "JSC (points)", dir: "up", d: "Point-level track Jaccard: matched track points / (matched + missed + spurious)." },
        { k: "jsc_theta", l: "JSCθ (tracks)", dir: "up", d: "Track-level Jaccard: fraction of whole trajectories correctly matched to a GT track." },
        { k: "track_rmse_nm", l: "Track RMSE (nm)", dir: "down", d: "Position error along matched tracks, in nm. Lower is better." },
        { k: "n_tracks", l: "Est. tracks", dir: "none", d: "Number of trajectories the tool produced (compare to the GT track count)." }]

    readonly property var figCaptions: ({
        "summary": "Headline panels: detection F1/Jaccard, tracking α/β/JSC, localisation RMSE vs the CRLB floor (dashed), and the detection precision–recall point. Bars closer to 1 are better; RMSE bars near the dashed line are better.",
        "d_dist": "Histogram of each tool's recovered diffusion coefficient D. Dashed green lines mark the ground-truth D per population (simulated ground truth only).",
        "confusion": "Motion-class confusion matrix — rows are the true class, columns are the tool's predicted class. A perfect classifier is purely diagonal.",
        "overlay": "Ground-truth trajectories (grey) vs the tool's tracks: matched tracks in the tool colour, spurious (false) tracks in red."
    })

    function fmt(v, key) {
        if (v === null || v === undefined) return "—"
        if (key === "n_tracks" || key === "n_matched") return Math.round(v) + ""
        if (key.indexOf("rmse") >= 0) return v.toFixed(0)
        return v.toFixed(3)
    }
    function dirOf(key) {
        var all = detMetrics.concat(trkMetrics)
        for (var i = 0; i < all.length; i++) if (all[i].k === key) return all[i].dir
        return "up"
    }
    function rateColor(key, v) {
        if (v === null || v === undefined) return pal.TXT_MUTED
        var dir = dirOf(key)
        if (dir === "none") return pal.TXT
        if (dir === "down") {
            if (v <= 15) return pal.SUCCESS
            if (v <= 30) return pal.ACC
            if (v <= 60) return pal.WARN
            return pal.DANGER
        }
        if (v >= 0.90) return pal.SUCCESS
        if (v >= 0.75) return pal.ACC
        if (v >= 0.50) return pal.WARN
        return pal.DANGER
    }
    function rateWord(key, v) {
        if (v === null || v === undefined || dirOf(key) === "none") return ""
        var c = "" + rateColor(key, v)
        return c === "" + pal.SUCCESS ? "Excellent" : c === "" + pal.ACC ? "Good"
             : c === "" + pal.WARN ? "Fair" : "Poor"
    }
    function goodHint(dir) {
        return dir === "down" ? "lower is better (≤30 nm good, ≤15 excellent)"
             : dir === "none" ? "a count — compare the two tools"
             : "0–1, higher is better (≥0.75 good, ≥0.90 excellent)"
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

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Metric"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs
                               font.weight: Font.DemiBold; Layout.preferredWidth: 210 }
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
                            // metric name — hover it for the explanation
                            Text {
                                Layout.preferredWidth: 210
                                text: drow.modelData.l; font.pixelSize: sc.textSm
                                color: lblHovD.hovered ? pal.ACC : pal.TXT
                                HoverHandler { id: lblHovD; cursorShape: Qt.PointingHandCursor }
                                QQC.ToolTip.visible: lblHovD.hovered; QQC.ToolTip.delay: 200
                                QQC.ToolTip.text: drow.modelData.d + "  (" + root.goodHint(drow.modelData.dir) + ")"
                            }
                            // one rated value per tool
                            Repeater { model: root.cards
                                delegate: Item {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: vtd.implicitHeight
                                    Text { id: vtd; anchors.right: parent.right
                                           text: root.fmt(modelData[drow.modelData.k], drow.modelData.k)
                                           color: root.rateColor(drow.modelData.k, modelData[drow.modelData.k])
                                           font.pixelSize: sc.textSm }
                                    HoverHandler { id: vhd }
                                    QQC.ToolTip.delay: 250
                                    QQC.ToolTip.visible: vhd.hovered && QQC.ToolTip.text !== ""
                                    QQC.ToolTip.text: {
                                        var w = root.rateWord(drow.modelData.k, modelData[drow.modelData.k])
                                        return w === "" ? "" : w + " — " + drow.modelData.d
                                    }
                                }
                            }
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
                            Text {
                                Layout.preferredWidth: 210
                                text: trow.modelData.l; font.pixelSize: sc.textSm
                                color: lblHovT.hovered ? pal.ACC : pal.TXT
                                HoverHandler { id: lblHovT; cursorShape: Qt.PointingHandCursor }
                                QQC.ToolTip.visible: lblHovT.hovered; QQC.ToolTip.delay: 200
                                QQC.ToolTip.text: trow.modelData.d + "  (" + root.goodHint(trow.modelData.dir) + ")"
                            }
                            Repeater { model: root.cards
                                delegate: Item {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: vtt.implicitHeight
                                    Text { id: vtt; anchors.right: parent.right
                                           text: root.fmt(modelData[trow.modelData.k], trow.modelData.k)
                                           color: root.rateColor(trow.modelData.k, modelData[trow.modelData.k])
                                           font.pixelSize: sc.textSm }
                                    HoverHandler { id: vht }
                                    QQC.ToolTip.delay: 250
                                    QQC.ToolTip.visible: vht.hovered && QQC.ToolTip.text !== ""
                                    QQC.ToolTip.text: {
                                        var w = root.rateWord(trow.modelData.k, modelData[trow.modelData.k])
                                        return w === "" ? "" : w + " — " + trow.modelData.d
                                    }
                                }
                            }
                        }
                    }

                    // colour legend
                    Rectangle { Layout.fillWidth: true; height: 1; color: pal.BORDER; Layout.topMargin: sc.sp2 }
                    RowLayout {
                        Layout.fillWidth: true; spacing: sc.sp4
                        Text { text: "Score:"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                        Repeater {
                            model: [{ t: "Excellent", c: pal.SUCCESS }, { t: "Good", c: pal.ACC },
                                    { t: "Fair", c: pal.WARN }, { t: "Poor", c: pal.DANGER }]
                            delegate: RowLayout { required property var modelData; spacing: sc.sp2
                                Rectangle { width: 8; height: 8; radius: 4; color: modelData.c
                                            Layout.alignment: Qt.AlignVCenter }
                                Text { text: modelData.t; color: pal.TXT_MUTED; font.pixelSize: sc.textXs } }
                        }
                        Item { Layout.fillWidth: true }
                        Text { text: "hover a metric name or value for details"
                               color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
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
                    Text { text: "DIFFUSION RECOVERY (D µm²/s)"
                           color: dhh.hovered ? pal.TXT : pal.TXT_MUTED
                           font.pixelSize: sc.textXs; font.weight: Font.Bold; font.letterSpacing: 1.5
                           HoverHandler { id: dhh; cursorShape: Qt.PointingHandCursor }
                           QQC.ToolTip.visible: dhh.hovered; QQC.ToolTip.delay: 200
                           QQC.ToolTip.text: "Recovered diffusion coefficient D vs the known truth, per motion class. "
                                           + "bias% = (recovered − true) / true; closer to 0 is better (green < 15%)." }
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
                                           color: modelData.bias_pct === null ? pal.TXT_MUTED
                                                : Math.abs(modelData.bias_pct) < 15 ? pal.SUCCESS
                                                : Math.abs(modelData.bias_pct) < 30 ? pal.WARN : pal.DANGER
                                           font.pixelSize: sc.textSm; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }
            }

            // ── "how to read these metrics" (collapsible) ─────────────────
            Card {
                Layout.fillWidth: true
                implicitHeight: gCol.implicitHeight + sc.sp8
                ColumnLayout {
                    id: gCol
                    x: sc.sp6; y: sc.sp4; width: parent.width - sc.sp6 * 2; spacing: sc.sp4
                    RowLayout {
                        Layout.fillWidth: true
                        Icon { name: "info"; size: 15; color: pal.ACC }
                        Text { text: "How to read these metrics"; color: pal.TXT
                               font.pixelSize: sc.textMd; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Icon { name: root.showGuide ? "chevron-down" : "chevron-right"
                               size: 16; color: pal.TXT_MUTED }
                        TapHandler { onTapped: root.showGuide = !root.showGuide }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                    Repeater {
                        model: root.showGuide ? root.detMetrics.concat(root.trkMetrics) : []
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true; spacing: 1
                            Text { text: modelData.l; color: pal.ACC; font.pixelSize: sc.textSm
                                   font.weight: Font.DemiBold }
                            Text { text: modelData.d + "  ·  " + root.goodHint(modelData.dir)
                                   color: pal.TXT_MUTED; font.pixelSize: sc.textXs
                                   Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        }
                    }
                }
            }

            // ── figure ────────────────────────────────────────────────────
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 520
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: sc.sp5; spacing: sc.sp3
                    RowLayout { spacing: sc.sp3
                        Text { text: "Figure"; color: pal.TXT; font.pixelSize: sc.textMd; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Select { model: ["summary", "d_dist", "confusion", "overlay"]
                                 onPicked: (t) => root.figKind = t }
                    }
                    Text { text: root.figCaptions[root.figKind] || ""
                           color: pal.TXT_MUTED; font.pixelSize: sc.textXs
                           Layout.fillWidth: true; wrapMode: Text.WordWrap }
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
