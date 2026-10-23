# Owner: export the avatar for CC/iC Blender Tools the same way the official CC/iC Blender
# Pipeline plug-in does (btp/exporter.py): FbxKey + json + current frame pose, textures to folders.
# Run inside CC5 with Script > Load Python.
from RLPy import *

OUT = r"D:\OTOLUME\beyon_cc5\parts\v29_boot\beyon_blender.fbx"

avatar = RScene.GetAvatars()[0]
o1 = (EExportFbxOptions__None | EExportFbxOptions_AutoSkinRigidMesh | EExportFbxOptions_RemoveAllUnused
      | EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory | EExportFbxOptions_FbxKey)
o2 = (EExportFbxOptions2__None | EExportFbxOptions2_ResetBoneScale | EExportFbxOptions2_ResetSelfillumination
      | EExportFbxOptions2_RenameDuplicateMaterialName)
o3 = EExportFbxOptions3__None | EExportFbxOptions3_ExportJson | EExportFbxOptions3_ExportVertexColor
s = RExportFbxSetting()
s.SetOption(o1); s.SetOption2(o2); s.SetOption3(o3)
s.EnableBakeDiffuseSpecularFromShader(False)
s.EnableBakeDiffuseFromSkinColor(False)
s.EnableBasicBindPose(True)
s.SetTextureFormat(EExportTextureFormat_Default)
s.SetTextureSize(EExportTextureSize_Original)
fps = RGlobal.GetFps()
frame = fps.GetFrameIndex(RGlobal.GetTime())
s.EnableExportMotion(True)
s.SetExportMotionFps(fps)
s.SetExportMotionRange(RRangePair(frame, frame))
result = RFileIO.ExportFbxFile(avatar, OUT, s)
with open(OUT[:-4] + "_done.txt", "w") as f:
    f.write("frame %s result %s\n" % (frame, result))
