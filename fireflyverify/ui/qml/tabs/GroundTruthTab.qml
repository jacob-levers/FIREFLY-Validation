import QtQuick
import QtQuick.Layouts
import "../components"

// Ground Truth: import a GT file (CSV / ISBI XML) or simulate a known-truth set.
Rectangle {
    id: root
    readonly property var pal: Theme.palette
    readonly property var sc: Theme.scale
    readonly property var gt: Verify.gtSummary
    property string mode: "import"        // "import" | "simulate"

    // simulate params (committed from the SpinBoxes below)
    property int   sSeed: 1
    property int   sFrames: 200
    property int   sEmitters: 60
    property real  sD: 0.10
    property real  sPhotons: 800
    property real  sBg: 20
    property real  sKoff: 0.05
    property string sMotion: "Brownian"

    function _populations() {
        if (sMotion === "Confined")
            return [{ name: "confined", fraction: 1.0, D_um2_s: sD, confine_radius_um: 0.15 }]
        if (sMotion === "Directed")
            return [{ name: "directed", fraction: 1.0, D_um2_s: sD, drift_vel_um_s: [0.5, 0.0] }]
        if (sMotion === "Mixed")
            return [{ name: "immobile", fraction: 0.25, D_um2_s: 0.0 },
                    { name: "confined", fraction: 0.25, D_um2_s: 0.05, confine_radius_um: 0.15 },
                    { name: "brownian", fraction: 0.25, D_um2_s: 0.10 },
                    { name: "directed", fraction: 0.25, D_um2_s: 0.05, drift_vel_um_s: [0.5, 0.0] }]
        return [{ name: "brownian", fraction: 1.0, D_um2_s: sD }]
    }

    color: pal.BG

    Flickable {
        anchors.fill: parent
        anchors.margins: sc.sp8
        contentWidth: width
        contentHeight: col.implicitHeight
        clip: true

        ColumnLayout {
            id: col
            width: parent.width
            spacing: sc.sp6

            // mode toggle
            RowLayout {
                spacing: sc.sp3
                Button { text: "Import file"; variant: root.mode === "import" ? "primary" : "secondary"
                         onClicked: root.mode = "import" }
                Button { text: "Simulate"; variant: root.mode === "simulate" ? "primary" : "secondary"
                         onClicked: root.mode = "simulate" }
                Item { Layout.fillWidth: true }
            }

            // ── IMPORT ────────────────────────────────────────────────────
            Card {
                visible: root.mode === "import"
                Layout.fillWidth: true
                implicitHeight: impCol.implicitHeight + sc.sp10
                ColumnLayout {
                    id: impCol
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2
                    spacing: sc.sp4
                    Text { text: "Import ground truth"; color: pal.TXT
                           font.pixelSize: sc.textLg; font.weight: Font.Bold }
                    Text { text: "Plain CSV (track, frame, x, y) or ISBI-2012 XML."
                           color: pal.TXT_MUTED; font.pixelSize: sc.textSm }
                    RowLayout {
                        spacing: sc.sp6
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Pixel size (µm)"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 0; to: 1; decimals: 4; step: 0.001; value: 0.106
                                      special: "auto"
                                      onCommitted: (v) => Verify.setImportPixelSize(v) } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Frame interval (s)"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 0.0001; to: 10; decimals: 4; step: 0.005; value: 0.02
                                      onCommitted: (v) => Verify.setImportFrameInterval(v) } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Frame indexing"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            Select { model: ["auto", "0-based", "1-based"]
                                     onPicked: (t) => Verify.setImportFrameBase(
                                         t === "0-based" ? "0" : t === "1-based" ? "1" : "auto") } }
                        Item { Layout.fillWidth: true }
                    }
                    Button { text: "Choose ground-truth file…"; icon: "folder-open"; variant: "primary"
                             onClicked: Verify.chooseGroundTruth() }
                }
            }

            // ── SIMULATE ──────────────────────────────────────────────────
            Card {
                visible: root.mode === "simulate"
                Layout.fillWidth: true
                implicitHeight: simCol.implicitHeight + sc.sp10
                ColumnLayout {
                    id: simCol
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2
                    spacing: sc.sp4
                    Text { text: "Simulate a known-truth dataset"; color: pal.TXT
                           font.pixelSize: sc.textLg; font.weight: Font.Bold }
                    Text { text: "Generates ground-truth tracks with a known D / motion; export a movie + GT to run FIREFLY / palmTRACER on identical input."
                           color: pal.TXT_MUTED; font.pixelSize: sc.textSm; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    GridLayout {
                        columns: 4; columnSpacing: sc.sp6; rowSpacing: sc.sp4
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Motion"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            Select { model: ["Brownian", "Confined", "Directed", "Mixed"]
                                     onPicked: (t) => root.sMotion = t } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "D (µm²/s)"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 0; to: 5; decimals: 3; step: 0.01; value: root.sD
                                      onCommitted: (v) => root.sD = v } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Frames"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 10; to: 5000; decimals: 0; step: 50; value: root.sFrames
                                      onCommitted: (v) => root.sFrames = v } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Emitters"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 1; to: 2000; decimals: 0; step: 10; value: root.sEmitters
                                      onCommitted: (v) => root.sEmitters = v } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Photons"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 50; to: 10000; decimals: 0; step: 50; value: root.sPhotons
                                      onCommitted: (v) => root.sPhotons = v } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Background"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 0; to: 1000; decimals: 0; step: 5; value: root.sBg
                                      onCommitted: (v) => root.sBg = v } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Blink-off rate"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 0; to: 1; decimals: 3; step: 0.01; value: root.sKoff
                                      onCommitted: (v) => root.sKoff = v } }
                        ColumnLayout { spacing: sc.sp2
                            Text { text: "Seed"; color: pal.TXT_MUTED; font.pixelSize: sc.textXs }
                            SpinBox { from: 0; to: 99999; decimals: 0; step: 1; value: root.sSeed
                                      onCommitted: (v) => root.sSeed = v } }
                    }
                    RowLayout {
                        spacing: sc.sp3
                        Button { text: "Generate"; icon: "sparkles"; variant: "primary"; spin: Verify.busy
                                 onClicked: Verify.simulate({
                                     seed: root.sSeed, n_frames: root.sFrames, height: 128, width: 128,
                                     n_emitters: root.sEmitters, photons_per_emitter: root.sPhotons,
                                     bg_photons: root.sBg, k_off: root.sKoff, bleach_prob: 0.0,
                                     populations: root._populations() }) }
                        Button { text: "Export movie + GT…"; icon: "download"; variant: "secondary"
                                 enabled: root.gt.loaded === true
                                 onClicked: Verify.chooseExportSimDir() }
                    }
                }
            }

            // ── LOADED SUMMARY ────────────────────────────────────────────
            Card {
                visible: root.gt.loaded === true
                Layout.fillWidth: true
                implicitHeight: sumRow.implicitHeight + sc.sp10
                RowLayout {
                    id: sumRow
                    x: sc.sp6; y: sc.sp5; width: parent.width - sc.sp6 * 2
                    spacing: sc.sp10
                    MetricStat { label: "Source"; value: root.gt.source || "—" }
                    MetricStat { label: "Tracks"; value: (root.gt.n_tracks !== undefined ? root.gt.n_tracks : 0) + "" }
                    MetricStat { label: "Localisations"; value: (root.gt.n_locs || 0) + "" }
                    MetricStat { label: "Frames"; value: (root.gt.n_frames || 0) + "" }
                    MetricStat { label: "Pixel size"; value: (root.gt.pixel_size_um || 0).toFixed(3); unit: "µm" }
                    MetricStat { label: "Truth D"; value: root.gt.has_truth_D ? "known" : "—"
                                 tone: root.gt.has_truth_D ? pal.SUCCESS : pal.TXT_MUTED }
                    Item { Layout.fillWidth: true }
                }
            }
        }
    }
}
