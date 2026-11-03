# Owner: put a template motion on the avatar to see it move. Run with Script > Load Python.
# The motion file is read from cc5_load_motion.txt in the work folder (one path).
import os
import RLPy

# Work folder: set CC5_PIPELINE_DIR to choose it (default: ~/cc5_pipeline).
WORK = os.environ.get("CC5_PIPELINE_DIR", os.path.join(os.path.expanduser("~"), "cc5_pipeline"))
with open(os.path.join(WORK, "cc5_load_motion.txt"), encoding="utf-8") as f:
    MOTION = f.read().strip()
avatar = RLPy.RScene.GetAvatars()[0]
RLPy.RScene.ClearSelectObjects()
RLPy.RScene.SelectObject(avatar)
result = RLPy.RFileIO.LoadFile(MOTION)
fps = RLPy.RGlobal.GetFps()
end = fps.GetFrameIndex(RLPy.RGlobal.GetEndTime())
with open(os.path.join(WORK, "cc5_load_motion_done.txt"), "w") as f:
    f.write("result %s end_frame %s\n" % (result, end))
