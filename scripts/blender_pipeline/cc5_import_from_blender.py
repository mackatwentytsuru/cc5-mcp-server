# Owner: bring the character back from CC/iC Blender Tools the way the official CC/iC Blender
# Pipeline plug-in does (btp/importer.py): standard human + FbxKey. It replaces the avatar in the
# scene, so save the project first. Run inside CC5 with Script > Load Python.
# The FBX to load is read from cc5_import_from_blender.txt next to this script (one path).
import os
import RLPy

with open(r"D:\OTOLUME\beyon_cc5\scripts\cc5_import_from_blender.txt", encoding="utf-8") as f:
    FBX = f.read().strip()
KEY = FBX[:-4] + ".fbxkey"

args = RLPy.EImportFbxOption__None | RLPy.EImportFbxOption_StandardHumanCharacter
result = RLPy.RFileIO.LoadFbxFile(FBX, args, KEY, "", True) if os.path.exists(KEY) else RLPy.RFileIO.LoadFbxFile(FBX, args)
with open(FBX[:-4] + "_import_done.txt", "w") as f:
    f.write("result %s avatars %s\n" % (result, [a.GetName() for a in RLPy.RScene.GetAvatars()]))
