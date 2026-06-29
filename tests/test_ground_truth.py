"""Ground-truth importer: ISBI-2012 XML and plain CSV yield the same tracks, and
frame-base handling is explicit."""
import numpy as np

from fireflyverify.adapters.ground_truth import load_ground_truth

_XML = """<?xml version="1.0"?>
<root>
  <TrackContestISBI2012 SNR="7" density="low" scenario="vesicle">
    <particle>
      <detection t="0" x="10.0" y="20.0" z="0"/>
      <detection t="1" x="11.0" y="21.0" z="0"/>
      <detection t="2" x="12.0" y="22.0" z="0"/>
    </particle>
    <particle>
      <detection t="0" x="40.0" y="50.0" z="0"/>
      <detection t="1" x="40.5" y="50.5" z="0"/>
    </particle>
  </TrackContestISBI2012>
</root>
"""

_CSV = """track,frame,x,y
0,0,10.0,20.0
0,1,11.0,21.0
0,2,12.0,22.0
1,0,40.0,50.0
1,1,40.5,50.5
"""


def test_xml_and_csv_equivalent(tmp_path):
    xp = tmp_path / "gt.xml"; xp.write_text(_XML)
    cp = tmp_path / "gt.csv"; cp.write_text(_CSV)
    gx = load_ground_truth(str(xp))
    gc = load_ground_truth(str(cp), frame_base="0")
    tx = gx.gt_tracks.sort_values(["particle", "frame"]).reset_index(drop=True)
    tc = gc.gt_tracks.sort_values(["particle", "frame"]).reset_index(drop=True)
    assert tx["particle"].tolist() == tc["particle"].tolist() == [0, 0, 0, 1, 1]
    assert tx["frame"].tolist() == tc["frame"].tolist() == [0, 1, 2, 0, 1]
    assert np.allclose(tx["x"], tc["x"]) and np.allclose(tx["y"], tc["y"])
    # both are 0-based, pixel coordinates, no truth populations
    assert int(tx["frame"].min()) == 0
    assert gx.meta["populations"] == {} and gc.meta["populations"] == {}


def test_frame_base_one_shifts_to_zero(tmp_path):
    csv = "particle,frame,x,y\n5,1,1,1\n5,2,2,2\n5,3,3,3\n"
    p = tmp_path / "one.csv"; p.write_text(csv)
    g = load_ground_truth(str(p), frame_base="1")        # 1-based → subtract 1
    assert g.gt_tracks["frame"].tolist() == [0, 1, 2]


def test_csv_nm_units_converted(tmp_path):
    # x_nm / y_nm columns → divided by pixel size to get pixels
    csv = "track,frame,x_nm,y_nm\n0,0,1060,2120\n0,1,2120,3180\n"
    p = tmp_path / "nm.csv"; p.write_text(csv)
    g = load_ground_truth(str(p), pixel_size_um=0.106, frame_base="0")
    # 1060 nm / 106 nm/px = 10 px
    assert np.allclose(g.gt_tracks["x"].tolist(), [10.0, 20.0])
    assert np.allclose(g.gt_tracks["y"].tolist(), [20.0, 30.0])
