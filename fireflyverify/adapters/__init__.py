"""Adapters — parse exported tracking output files into the scoring schema.

`load_firefly_output`, `load_palmtracer_output`, and `load_ground_truth`
normalise FIREFLY / palmTRACER / ground-truth files to a common
(frame[0-based], x,y[pixels], particle) frame plus calibration metadata.
"""
