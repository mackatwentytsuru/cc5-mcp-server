# Owner: does the saved custom boot work on another character? Load a template character
# (replaces the avatar in the scene) and put the .ccShoes on it. Script > Load Python.
# Paths come from cc5_try_shoes_on.txt: line 1 character file, line 2 shoes file.
import RLPy

with open(r"D:\OTOLUME\beyon_cc5\scripts\cc5_try_shoes_on.txt", encoding="utf-8") as f:
    CHAR, SHOES = [l.strip() for l in f.read().splitlines()[:2]]
LOG = r"D:\OTOLUME\beyon_cc5\scripts\cc5_try_shoes_on_done.txt"
lines = []
r = RLPy.RFileIO.LoadFile(CHAR)
lines.append("character error=%s avatars=%s" % (r.IsError(), [a.GetName() for a in RLPy.RScene.GetAvatars()]))
avatar = RLPy.RScene.GetAvatars()[0]
RLPy.RScene.ClearSelectObjects()
RLPy.RScene.SelectObject(avatar)
r = RLPy.RFileIO.LoadFile(SHOES)
lines.append("shoes error=%s clothes=%s" % (r.IsError(), [c.GetName() for c in avatar.GetClothes()]))
with open(LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
