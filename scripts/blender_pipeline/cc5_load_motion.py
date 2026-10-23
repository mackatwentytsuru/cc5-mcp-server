# Owner: put a template motion on the avatar to see the boots walk. Run with Script > Load Python.
# The motion file is read from cc5_load_motion.txt next to this script (one path).
import RLPy

with open(r"D:\OTOLUME\beyon_cc5\scripts\cc5_load_motion.txt", encoding="utf-8") as f:
    MOTION = f.read().strip()
avatar = RLPy.RScene.GetAvatars()[0]
RLPy.RScene.ClearSelectObjects()
RLPy.RScene.SelectObject(avatar)
result = RLPy.RFileIO.LoadFile(MOTION)
fps = RLPy.RGlobal.GetFps()
end = fps.GetFrameIndex(RLPy.RGlobal.GetEndTime())
with open(r"D:\OTOLUME\beyon_cc5\scripts\cc5_load_motion_done.txt", "w") as f:
    f.write("result %s end_frame %s\n" % (result, end))
