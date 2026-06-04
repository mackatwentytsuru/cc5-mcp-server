# RLPy API Complete Reference

> Auto-generated from `C:\Program Files\Reallusion\Character Creator 5\Bin64\RLPy.py`

> SWIG-generated Python wrapper | 206 classes | 1188 constants | 287 functions


## Table of Contents

- [Enums](#enums)
  - [EAPILoadMediaAction](#eapiloadmediaaction)
  - [EAlignAxis](#ealignaxis)
  - [EAnimContent](#eanimcontent)
  - [EAttributeFlag](#eattributeflag)
  - [EAttributeType](#eattributetype)
  - [EAvatarGeneration](#eavatargeneration)
  - [EAvatarPartType](#eavatarparttype)
  - [EAvatarType](#eavatartype)
  - [EAxisSetting](#eaxissetting)
  - [EBodyActivePart](#ebodyactivepart)
  - [ECSSType](#ecsstype)
  - [ECameraFitResolution](#ecamerafitresolution)
  - [EChooseBase](#echoosebase)
  - [EClotheType](#eclothetype)
  - [EContentRootFolder](#econtentrootfolder)
  - [EControlType](#econtroltype)
  - [EConvertCharacterLevel](#econvertcharacterlevel)
  - [ECoordinateAxes](#ecoordinateaxes)
  - [ECoordinateAxis](#ecoordinateaxis)
  - [ECoordinateSpace](#ecoordinatespace)
  - [ECoordinateSystem](#ecoordinatesystem)
  - [EDeviceType](#edevicetype)
  - [EDialogType](#edialogtype)
  - [EDockWidgetAreas](#edockwidgetareas)
  - [EDockWidgetFeatures](#edockwidgetfeatures)
  - [EEulerOrder](#eeulerorder)
  - [EExportFbxOptions](#eexportfbxoptions)
  - [EExportGoZPose](#eexportgozpose)
  - [EExportMeshMotionMode](#eexportmeshmotionmode)
  - [EExportTextureFormat](#eexporttextureformat)
  - [EExportTextureSize](#eexporttexturesize)
  - [EFaceHairType](#efacehairtype)
  - [EFacialAnimationMode](#efacialanimationmode)
  - [EFacialProfile](#efacialprofile)
  - [EFloatControlAttribute](#efloatcontrolattribute)
  - [EFloorContactType](#efloorcontacttype)
  - [EHSBodyType](#ehsbodytype)
  - [EHSLevel](#ehslevel)
  - [EHSMode](#ehsmode)
  - [EHairType](#ehairtype)
  - [EHandDataSource](#ehanddatasource)
  - [EHandJoin](#ehandjoin)
  - [EHandJoinType](#ehandjointype)
  - [EHikEffector](#ehikeffector)
  - [EHikEffectorType](#ehikeffectortype)
  - [EImportExpressionPart](#eimportexpressionpart)
  - [EImportFbxOption](#eimportfbxoption)
  - [EIncludeMotionType](#eincludemotiontype)
  - [ELanguage](#elanguage)
  - [ELevelCharacterTemplateType](#elevelcharactertemplatetype)
  - [ELinkObjectAlignType](#elinkobjectaligntype)
  - [ELoadFileOption](#eloadfileoption)
  - [EMDpropCrowdExitType](#emdpropcrowdexittype)
  - [EMaterialTextureChannel](#ematerialtexturechannel)
  - [EMaterialType](#ematerialtype)
  - [EMenu](#emenu)
  - [EMocapState](#emocapstate)
  - [EModeType](#emodetype)
  - [EMotionApplyMode](#emotionapplymode)
  - [EMotionSettingOption](#emotionsettingoption)
  - [EMsgButton](#emsgbutton)
  - [EObjectEventType](#eobjecteventtype)
  - [EObjectModifiedType](#eobjectmodifiedtype)
  - [EObjectType](#eobjecttype)
  - [EPathType](#epathtype)
  - [EPopcornFxSamplerType](#epopcornfxsamplertype)
  - [EPositionUnit](#epositionunit)
  - [EPostEffect](#eposteffect)
  - [EPropertyType](#epropertytype)
  - [EQuaternionOrder](#equaternionorder)
  - [EReduceBonePose](#ereducebonepose)
  - [EReplaceMeshOption](#ereplacemeshoption)
  - [EResolutionType](#eresolutiontype)
  - [ERotationType](#erotationtype)
  - [ERotationUnit](#erotationunit)
  - [ESaveFacialAnimationOption](#esavefacialanimationoption)
  - [ESaveFileType](#esavefiletype)
  - [ESaveMotionClipOption](#esavemotionclipoption)
  - [ESaveMotionPlusOption](#esavemotionplusoption)
  - [ESetCategory](#esetcategory)
  - [ETagType](#etagtype)
  - [ETangentType](#etangenttype)
  - [ETemplateRootFolder](#etemplaterootfolder)
  - [ETimecodeSource](#etimecodesource)
  - [ETransitionType](#etransitiontype)
  - [EUnrealBoneStructure](#eunrealbonestructure)
  - [EVisemeID](#evisemeid)
  - [EWrinkleFacePart](#ewrinklefacepart)
  - [EWrinkleLayerType](#ewrinklelayertype)
  - [EWrinkleTextureChannel](#ewrinkletexturechannel)
- [Constants (Non-Enum)](#constants-non-enum)
- [Classes](#classes)
  - [Vector/Container Types](#vectorcontainer-types)
  - [Core API Classes](#core-api-classes)
    - [FloatPair](#floatpair)
    - [ImportExpressionOptions](#importexpressionoptions)
    - [MaterialSettings](#materialsettings)
    - [PixelStreamCaptureFrame](#pixelstreamcaptureframe)
    - [RApplication](#rapplication)
    - [RAttribute](#rattribute)
    - [RAudio](#raudio)
    - [RAudioRecorder](#raudiorecorder)
    - [RAudioRecorderCallback](#raudiorecordercallback)
    - [RBeginCommandOption](#rbegincommandoption)
    - [RBodySetting](#rbodysetting)
    - [RCallback](#rcallback)
    - [RCameraDofData](#rcameradofdata)
    - [RColor](#rcolor)
    - [RControl](#rcontrol)
    - [RCustomValue](#rcustomvalue)
    - [RCustomValueArray](#rcustomvaluearray)
    - [RCustomValueMap](#rcustomvaluemap)
    - [RDataBlock](#rdatablock)
    - [RDepthParam](#rdepthparam)
    - [RDeviceSetting](#rdevicesetting)
    - [RDialogCallback](#rdialogcallback)
    - [REdgeDetectionCannyParam](#redgedetectioncannyparam)
    - [REventCallback](#reventcallback)
    - [REventHandler](#reventhandler)
    - [RExportAudioParameter](#rexportaudioparameter)
    - [RExportCommonParameter](#rexportcommonparameter)
    - [RExportFbxSetting](#rexportfbxsetting)
    - [RExportGlbSetting](#rexportglbsetting)
    - [RExportGoZMeshOption](#rexportgozmeshoption)
    - [RExportImageParameter](#rexportimageparameter)
    - [RExportImageSequenceParameter](#rexportimagesequenceparameter)
    - [RExportOutputRangeParameter](#rexportoutputrangeparameter)
    - [RExportVideoParameter](#rexportvideoparameter)
    - [RFacialSetting](#rfacialsetting)
    - [RFileIO](#rfileio)
    - [RFlattenWrinkleImageMap](#rflattenwrinkleimagemap)
    - [RFloatControl](#rfloatcontrol)
    - [RFloatKey](#rfloatkey)
    - [RFps](#rfps)
    - [RGlobal](#rglobal)
    - [RHandSetting](#rhandsetting)
    - [RHeadshot](#rheadshot)
    - [RHeadshotOption](#rheadshotoption)
    - [RIAccessory](#riaccessory)
    - [RIAudioObject](#riaudioobject)
    - [RIAvatar](#riavatar)
    - [RIAvatarPart](#riavatarpart)
    - [RIAvatarShapingComponent](#riavatarshapingcomponent)
    - [RIBase](#ribase)
    - [RIBodyDevice](#ribodydevice)
    - [RIBuildingGeneratorObject](#ribuildinggeneratorobject)
    - [RIBuildingObject](#ribuildingobject)
    - [RICamera](#ricamera)
    - [RIClip](#riclip)
    - [RICloth](#ricloth)
    - [RIDeviceBase](#ridevicebase)
    - [RIDialog](#ridialog)
    - [RIDirectionalLight](#ridirectionallight)
    - [RIDockWidget](#ridockwidget)
    - [RIEffector](#rieffector)
    - [RIElementObject](#rielementobject)
    - [RIEventListener](#rieventlistener)
    - [RIFaceComponent](#rifacecomponent)
    - [RIFacialDevice](#rifacialdevice)
    - [RIFacialProfileComponent](#rifacialprofilecomponent)
    - [RIFloorObject](#rifloorobject)
    - [RIHair](#rihair)
    - [RIHandDevice](#rihanddevice)
    - [RIHikEffectorComponent](#rihikeffectorcomponent)
    - [RIImage](#riimage)
    - [RILight](#rilight)
    - [RILightAvatar](#rilightavatar)
    - [RILookAtComponent](#rilookatcomponent)
    - [RIMDProp](#rimdprop)
    - [RIMaterialComponent](#rimaterialcomponent)
    - [RIMesh](#rimesh)
    - [RIMocapManager](#rimocapmanager)
    - [RIMorphComponent](#rimorphcomponent)
    - [RIMotionDirectorManager](#rimotiondirectormanager)
    - [RINode](#rinode)
    - [RINodeTransformPair](#rinodetransformpair)
    - [RINodeTransformPairs](#rinodetransformpairs)
    - [RIObject](#riobject)
    - [RIOmniConnectorManager](#riomniconnectormanager)
    - [RIParticle](#riparticle)
    - [RIPath](#ripath)
    - [RIPhysicsComponent](#riphysicscomponent)
    - [RIPointLight](#ripointlight)
    - [RIPopcornFXObject](#ripopcornfxobject)
    - [RIProp](#riprop)
    - [RIReach](#rireach)
    - [RISaveFileOptionBase](#risavefileoptionbase)
    - [RISkeletonComponent](#riskeletoncomponent)
    - [RISky](#risky)
    - [RISpotLight](#rispotlight)
    - [RIStdMaterial](#ristdmaterial)
    - [RIUnitObject](#riunitobject)
    - [RIVisemeComponent](#rivisemecomponent)
    - [RIVisualSettingComponent](#rivisualsettingcomponent)
    - [RIWallObject](#riwallobject)
    - [RImage](#rimage)
    - [RImportExpressionSetting](#rimportexpressionsetting)
    - [RInsertBoneInfo](#rinsertboneinfo)
    - [RKey](#rkey)
    - [RMath](#rmath)
    - [RMatrix3](#rmatrix3)
    - [RMatrix4](#rmatrix4)
    - [RMessageBoxButton](#rmessageboxbutton)
    - [RMorphSliderSetting](#rmorphslidersetting)
    - [ROpenPoseKeyPointParam](#ropenposekeypointparam)
    - [RPositionSetting](#rpositionsetting)
    - [RPropertyFloatMap](#rpropertyfloatmap)
    - [RPyTimer](#rpytimer)
    - [RPyTimerCallback](#rpytimercallback)
    - [RQuaternion](#rquaternion)
    - [RRangePair](#rrangepair)
    - [RReachKey](#rreachkey)
    - [RRgb](#rrgb)
    - [RRotationSetting](#rrotationsetting)
    - [RSBuildingSettings](#rsbuildingsettings)
    - [RSUsdExportOption](#rsusdexportoption)
    - [RSaveFacialAnimationOption](#rsavefacialanimationoption)
    - [RSaveFileSetting](#rsavefilesetting)
    - [RSaveMotionPlusOption](#rsavemotionplusoption)
    - [RSaveRangePair](#rsaverangepair)
    - [RScene](#rscene)
    - [RStGenPackElementInfo](#rstgenpackelementinfo)
    - [RStGenPackFloorInfo](#rstgenpackfloorinfo)
    - [RStGenPackMaterialInfo](#rstgenpackmaterialinfo)
    - [RStGenPackStyleInfo](#rstgenpackstyleinfo)
    - [RStGenPackWallInfo](#rstgenpackwallinfo)
    - [RStatus](#rstatus)
    - [RTcpCallback](#rtcpcallback)
    - [RTcpClient](#rtcpclient)
    - [RTick](#rtick)
    - [RTime](#rtime)
    - [RTime2IntMap](#rtime2intmap)
    - [RTransform](#rtransform)
    - [RTransformControl](#rtransformcontrol)
    - [RTransformKey](#rtransformkey)
    - [RUdpCallback](#rudpcallback)
    - [RUdpClient](#rudpclient)
    - [RUi](#rui)
    - [RVariant](#rvariant)
    - [RVector2](#rvector2)
    - [RVector3](#rvector3)
    - [RVector4](#rvector4)
    - [RVideo](#rvideo)
    - [RVisemeKey](#rvisemekey)
    - [RVisemeSmoothOption](#rvisemesmoothoption)
    - [RWin32ApiKit](#rwin32apikit)
    - [RWinMessageCallback](#rwinmessagecallback)
    - [RWordData](#rworddata)
    - [SwitchCameraFramePair](#switchcameraframepair)
    - [SwitchCameraFramePairs](#switchcameraframepairs)
    - [WBoneQniqueNameMap](#wboneqniquenamemap)
    - [WStr2FloatMap](#wstr2floatmap)
    - [WStr2Matrix4fMap](#wstr2matrix4fmap)
    - [WStrMap](#wstrmap)
    - [WStrTransformMap](#wstrtransformmap)
    - [WStrTransformVectorMap](#wstrtransformvectormap)
    - [WallPosition](#wallposition)
- [Global Functions](#global-functions)
  - [RApplication](#rapplication)
  - [RAudio](#raudio)
  - [RDataBlock](#rdatablock)
  - [REventHandler](#reventhandler)
  - [RFileIO](#rfileio)
  - [RGlobal](#rglobal)
  - [RHeadshot](#rheadshot)
  - [RIBuildingGeneratorObject](#ribuildinggeneratorobject)
  - [RImage](#rimage)
  - [RMath](#rmath)
  - [RMatrix3](#rmatrix3)
  - [RQuaternion](#rquaternion)
  - [RScene](#rscene)
  - [RStatus](#rstatus)
  - [RTick](#rtick)
  - [RTime](#rtime)
  - [RUi](#rui)
  - [RVideo](#rvideo)
  - [RWin32ApiKit](#rwin32apikit)
  - [Other Functions](#other-functions)

---

## Enums

### EAPILoadMediaAction

- `EAPILoadMediaAction_IMAGELAYER` = `EAPILoadMediaAction_IMAGELAYER`
- `EAPILoadMediaAction_PLANE` = `EAPILoadMediaAction_PLANE`
- `EAPILoadMediaAction_BILLBOARD` = `EAPILoadMediaAction_BILLBOARD`
- `EAPILoadMediaAction_BACKGROUND` = `EAPILoadMediaAction_BACKGROUND`

### EAlignAxis

- `EAlignAxis_INVALID` = `EAlignAxis_INVALID`
- `EAlignAxis_X_AXIS` = `EAlignAxis_X_AXIS`
- `EAlignAxis_Y_AXIS` = `EAlignAxis_Y_AXIS`
- `EAlignAxis_Z_AXIS` = `EAlignAxis_Z_AXIS`
- `EAlignAxis_ROTATE_AXIZ` = `EAlignAxis_ROTATE_AXIZ`

### EAnimContent

- `EAnimContent_Unknown` = `EAnimContent_Unknown`
- `EAnimContent_ObjectTransform` = `EAnimContent_ObjectTransform`
- `EAnimContent_LayerEditor` = `EAnimContent_LayerEditor`
- `EAnimContent_Constraint` = `EAnimContent_Constraint`
- `EAnimContent_Reach` = `EAnimContent_Reach`
- `EAnimContent_All` = `EAnimContent_All`

### EAttributeFlag

- `EAttributeFlag__None` = `EAttributeFlag__None`
- `EAttributeFlag_Keyable` = `EAttributeFlag_Keyable`
- `EAttributeFlag_Storable` = `EAttributeFlag_Storable`
- `EAttributeFlag_Default` = `EAttributeFlag_Default`

### EAttributeType

- `EAttributeType_Group` = `EAttributeType_Group`
- `EAttributeType_Position` = `EAttributeType_Position`
- `EAttributeType_Rotation` = `EAttributeType_Rotation`
- `EAttributeType_Scale` = `EAttributeType_Scale`
- `EAttributeType_Float` = `EAttributeType_Float`
- `EAttributeType_Int` = `EAttributeType_Int`
- `EAttributeType_String` = `EAttributeType_String`
- `EAttributeType_Bool` = `EAttributeType_Bool`
- `EAttributeType_Image` = `EAttributeType_Image`

### EAvatarGeneration

- `EAvatarGeneration__None` = `EAvatarGeneration__None`
- `EAvatarGeneration_CC_G1_Avatar` = `EAvatarGeneration_CC_G1_Avatar`
- `EAvatarGeneration_CC_G3_Avatar` = `EAvatarGeneration_CC_G3_Avatar`
- `EAvatarGeneration_CC_G3_Plus_Avatar` = `EAvatarGeneration_CC_G3_Plus_Avatar`
- `EAvatarGeneration_CC_Game_Base_One` = `EAvatarGeneration_CC_Game_Base_One`
- `EAvatarGeneration_CC_Game_Base_Multi` = `EAvatarGeneration_CC_Game_Base_Multi`
- `EAvatarGeneration_ActorBuild` = `EAvatarGeneration_ActorBuild`
- `EAvatarGeneration_ActorScan` = `EAvatarGeneration_ActorScan`
- `EAvatarGeneration_AccuRig` = `EAvatarGeneration_AccuRig`
- `EAvatarGeneration_CC_Game_Base_Divide` = `EAvatarGeneration_CC_Game_Base_Divide`
- `EAvatarGeneration_CC_LOD` = `EAvatarGeneration_CC_LOD`

### EAvatarPartType

- `EAvatarPartType__None` = `EAvatarPartType__None`
- `EAvatarPartType_Eyes` = `EAvatarPartType_Eyes`
- `EAvatarPartType_Teeth` = `EAvatarPartType_Teeth`
- `EAvatarPartType_Tongue` = `EAvatarPartType_Tongue`
- `EAvatarPartType_Custom` = `EAvatarPartType_Custom`
- `EAvatarPartType_EyeOcclusion` = `EAvatarPartType_EyeOcclusion`
- `EAvatarPartType_TearLine` = `EAvatarPartType_TearLine`
- `EAvatarPartType_Beard` = `EAvatarPartType_Beard`
- `EAvatarPartType_Brow` = `EAvatarPartType_Brow`
- `EAvatarPartType_Eyelash` = `EAvatarPartType_Eyelash`
- `EAvatarPartType_Upper` = `EAvatarPartType_Upper`
- `EAvatarPartType_Lower` = `EAvatarPartType_Lower`
- `EAvatarPartType_Shoes` = `EAvatarPartType_Shoes`
- `EAvatarPartType_Gloves` = `EAvatarPartType_Gloves`
- `EAvatarPartType_Accessory` = `EAvatarPartType_Accessory`

### EAvatarType

- `EAvatarType__None` = `EAvatarType__None`
- `EAvatarType_Standard` = `EAvatarType_Standard`
- `EAvatarType_NonStandard` = `EAvatarType_NonStandard`
- `EAvatarType_NonHuman` = `EAvatarType_NonHuman`
- `EAvatarType_StandardSeries` = `EAvatarType_StandardSeries`
- `EAvatarType_All` = `EAvatarType_All`
- `EAvatarType_AllEditable` = `EAvatarType_AllEditable`
- `EAvatarType_LightAvatarStandard` = `EAvatarType_LightAvatarStandard`
- `EAvatarType_LightAvatarNonStandard` = `EAvatarType_LightAvatarNonStandard`
- `EAvatarType_LightAvatarNonHuman` = `EAvatarType_LightAvatarNonHuman`
- `EAvatarType_LightAvatarStandardSeries` = `EAvatarType_LightAvatarStandardSeries`
- `EAvatarType_AllNonEditable` = `EAvatarType_AllNonEditable`
- `EAvatarType_LightAvatar` = `EAvatarType_LightAvatar`
- `EAvatarType_AllWithLight` = `EAvatarType_AllWithLight`

### EAxisSetting

- `EAxisSetting__None` = `EAxisSetting__None`
- `EAxisSetting_YUp` = `EAxisSetting_YUp`
- `EAxisSetting_ZUp` = `EAxisSetting_ZUp`

### EBodyActivePart

- `EBodyActivePart_Unknown` = `EBodyActivePart_Unknown`
- `EBodyActivePart_Head` = `EBodyActivePart_Head`
- `EBodyActivePart_Body` = `EBodyActivePart_Body`
- `EBodyActivePart_UpperArm_R` = `EBodyActivePart_UpperArm_R`
- `EBodyActivePart_ForeArm_R` = `EBodyActivePart_ForeArm_R`
- `EBodyActivePart_Hand_R` = `EBodyActivePart_Hand_R`
- `EBodyActivePart_Finger_R` = `EBodyActivePart_Finger_R`
- `EBodyActivePart_UpperArm_L` = `EBodyActivePart_UpperArm_L`
- `EBodyActivePart_ForeArm_L` = `EBodyActivePart_ForeArm_L`
- `EBodyActivePart_Hand_L` = `EBodyActivePart_Hand_L`
- `EBodyActivePart_Finger_L` = `EBodyActivePart_Finger_L`
- `EBodyActivePart_UpperLeg_R` = `EBodyActivePart_UpperLeg_R`
- `EBodyActivePart_Leg_R` = `EBodyActivePart_Leg_R`
- `EBodyActivePart_Foot_R` = `EBodyActivePart_Foot_R`
- `EBodyActivePart_UpperLeg_L` = `EBodyActivePart_UpperLeg_L`
- `EBodyActivePart_Leg_L` = `EBodyActivePart_Leg_L`
- `EBodyActivePart_Foot_L` = `EBodyActivePart_Foot_L`
- `EBodyActivePart_FullBody` = `EBodyActivePart_FullBody`
- `EBodyActivePart_UpperBody` = `EBodyActivePart_UpperBody`

### ECSSType

- `ECSSType_Color_0` = `ECSSType_Color_0`
- `ECSSType_Color_1` = `ECSSType_Color_1`

### ECameraFitResolution

- `ECameraFitResolution__None` = `ECameraFitResolution__None`
- `ECameraFitResolution_Horizontal` = `ECameraFitResolution_Horizontal`
- `ECameraFitResolution_Vertical` = `ECameraFitResolution_Vertical`

### EChooseBase

- `EChooseBase_Default` = `EChooseBase_Default`
- `EChooseBase_Current` = `EChooseBase_Current`
- `EChooseBase_File` = `EChooseBase_File`

### EClotheType

- `EClotheType_Unknown` = `EClotheType_Unknown`
- `EClotheType_Upper` = `EClotheType_Upper`
- `EClotheType_Lower` = `EClotheType_Lower`
- `EClotheType_Shoes` = `EClotheType_Shoes`
- `EClotheType_Gloves` = `EClotheType_Gloves`
- `EClotheType_Accessory` = `EClotheType_Accessory`

### EContentRootFolder

- `EContentRootFolder_Project` = `EContentRootFolder_Project`
- `EContentRootFolder_Character` = `EContentRootFolder_Character`
- `EContentRootFolder_AvatarControl` = `EContentRootFolder_AvatarControl`
- `EContentRootFolder_FacialProfile` = `EContentRootFolder_FacialProfile`
- `EContentRootFolder_Teeth` = `EContentRootFolder_Teeth`
- `EContentRootFolder_Eye` = `EContentRootFolder_Eye`
- `EContentRootFolder_Face` = `EContentRootFolder_Face`
- `EContentRootFolder_RLHead` = `EContentRootFolder_RLHead`
- `EContentRootFolder_Oral` = `EContentRootFolder_Oral`
- `EContentRootFolder_Upper` = `EContentRootFolder_Upper`
- `EContentRootFolder_Lower` = `EContentRootFolder_Lower`
- `EContentRootFolder_FullBodyMorphSkin` = `EContentRootFolder_FullBodyMorphSkin`
- `EContentRootFolder_HeadMorphSkin` = `EContentRootFolder_HeadMorphSkin`
- `EContentRootFolder_FullBodyMorph` = `EContentRootFolder_FullBodyMorph`
- `EContentRootFolder_BodyMorph` = `EContentRootFolder_BodyMorph`
- `EContentRootFolder_HeadMorph` = `EContentRootFolder_HeadMorph`
- `EContentRootFolder_AvatarPresetEyelash` = `EContentRootFolder_AvatarPresetEyelash`
- `EContentRootFolder_Nail` = `EContentRootFolder_Nail`
- `EContentRootFolder_MixerPreset_Leg` = `EContentRootFolder_MixerPreset_Leg`
- `EContentRootFolder_MixerPreset_Arm` = `EContentRootFolder_MixerPreset_Arm`
- `EContentRootFolder_MixerPreset_BodyAdjust` = `EContentRootFolder_MixerPreset_BodyAdjust`
- `EContentRootFolder_MixerPreset_HeadAdjust` = `EContentRootFolder_MixerPreset_HeadAdjust`
- `EContentRootFolder_MixerPreset_Chin` = `EContentRootFolder_MixerPreset_Chin`
- `EContentRootFolder_MixerPreset_Brow` = `EContentRootFolder_MixerPreset_Brow`
- `EContentRootFolder_MixerPreset_Ear` = `EContentRootFolder_MixerPreset_Ear`
- `EContentRootFolder_MixerPreset_Mouth` = `EContentRootFolder_MixerPreset_Mouth`
- `EContentRootFolder_MixerPreset_Nose` = `EContentRootFolder_MixerPreset_Nose`
- `EContentRootFolder_MixerPreset_Eye` = `EContentRootFolder_MixerPreset_Eye`
- `EContentRootFolder_MixerPreset_Body` = `EContentRootFolder_MixerPreset_Body`
- `EContentRootFolder_MixerPreset_Head` = `EContentRootFolder_MixerPreset_Head`
- `EContentRootFolder_MixerPreset_FullCharacter` = `EContentRootFolder_MixerPreset_FullCharacter`
- `EContentRootFolder_MixerPreset_Torso` = `EContentRootFolder_MixerPreset_Torso`
- `EContentRootFolder_MixerPresetSet` = `EContentRootFolder_MixerPresetSet`
- `EContentRootFolder_MixerPresetPackage` = `EContentRootFolder_MixerPresetPackage`
- `EContentRootFolder_Overall` = `EContentRootFolder_Overall`
- `EContentRootFolder_Skin_Head` = `EContentRootFolder_Skin_Head`
- `EContentRootFolder_FullSkin` = `EContentRootFolder_FullSkin`
- `EContentRootFolder_SkinBase` = `EContentRootFolder_SkinBase`
- `EContentRootFolder_NormalEffects` = `EContentRootFolder_NormalEffects`
- `EContentRootFolder_SkinDetails` = `EContentRootFolder_SkinDetails`
- `EContentRootFolder_Blemish` = `EContentRootFolder_Blemish`
- `EContentRootFolder_Acquired` = `EContentRootFolder_Acquired`
- `EContentRootFolder_BodyHair` = `EContentRootFolder_BodyHair`
- `EContentRootFolder_Nails` = `EContentRootFolder_Nails`
- `EContentRootFolder_SkinGenTools` = `EContentRootFolder_SkinGenTools`
- `EContentRootFolder_WrinkleMasks` = `EContentRootFolder_WrinkleMasks`
- `EContentRootFolder_FullMakeup` = `EContentRootFolder_FullMakeup`
- `EContentRootFolder_FoundationMakeup` = `EContentRootFolder_FoundationMakeup`
- `EContentRootFolder_EyeMakeup` = `EContentRootFolder_EyeMakeup`
- `EContentRootFolder_MakeupEyelash` = `EContentRootFolder_MakeupEyelash`
- `EContentRootFolder_LipMakeup` = `EContentRootFolder_LipMakeup`
- `EContentRootFolder_Eyebrow` = `EContentRootFolder_Eyebrow`
- `EContentRootFolder_Miscellaneous` = `EContentRootFolder_Miscellaneous`
- `EContentRootFolder_MakeupSkinGenTools` = `EContentRootFolder_MakeupSkinGenTools`
- `EContentRootFolder_Style` = `EContentRootFolder_Style`
- `EContentRootFolder_Group` = `EContentRootFolder_Group`
- `EContentRootFolder_Element` = `EContentRootFolder_Element`
- `EContentRootFolder_Underwear` = `EContentRootFolder_Underwear`
- `EContentRootFolder_Shirts` = `EContentRootFolder_Shirts`
- `EContentRootFolder_Pants` = `EContentRootFolder_Pants`
- `EContentRootFolder_Skirts` = `EContentRootFolder_Skirts`
- `EContentRootFolder_Coats` = `EContentRootFolder_Coats`
- `EContentRootFolder_FullBody` = `EContentRootFolder_FullBody`
- `EContentRootFolder_ClothOthers` = `EContentRootFolder_ClothOthers`
- `EContentRootFolder_Gloves` = `EContentRootFolder_Gloves`
- `EContentRootFolder_Shoes` = `EContentRootFolder_Shoes`
- `EContentRootFolder_Head` = `EContentRootFolder_Head`
- `EContentRootFolder_Torso` = `EContentRootFolder_Torso`
- `EContentRootFolder_Arm` = `EContentRootFolder_Arm`
- `EContentRootFolder_Leg` = `EContentRootFolder_Leg`
- `EContentRootFolder_AccessoryOthers` = `EContentRootFolder_AccessoryOthers`
- `EContentRootFolder_MotionPlus` = `EContentRootFolder_MotionPlus`
- `EContentRootFolder_Motion` = `EContentRootFolder_Motion`
- `EContentRootFolder_Expression` = `EContentRootFolder_Expression`
- `EContentRootFolder_Gesture` = `EContentRootFolder_Gesture`
- `EContentRootFolder_Pose` = `EContentRootFolder_Pose`
- `EContentRootFolder_MotionDirector` = `EContentRootFolder_MotionDirector`
- `EContentRootFolder_Persona` = `EContentRootFolder_Persona`
- `EContentRootFolder_iAnimation` = `EContentRootFolder_iAnimation`
- `EContentRootFolder_LightRoom` = `EContentRootFolder_LightRoom`
- `EContentRootFolder_Atmosphere` = `EContentRootFolder_Atmosphere`
- `EContentRootFolder_Camera` = `EContentRootFolder_Camera`
- `EContentRootFolder_Light` = `EContentRootFolder_Light`
- `EContentRootFolder_PostEffect` = `EContentRootFolder_PostEffect`
- `EContentRootFolder_ImageLayer` = `EContentRootFolder_ImageLayer`
- `EContentRootFolder_Scene3D` = `EContentRootFolder_Scene3D`
- `EContentRootFolder_Material` = `EContentRootFolder_Material`
- `EContentRootFolder_MaterialPlus` = `EContentRootFolder_MaterialPlus`
- `EContentRootFolder_Background2D` = `EContentRootFolder_Background2D`
- `EContentRootFolder_Texture` = `EContentRootFolder_Texture`
- `EContentRootFolder_Diffuse` = `EContentRootFolder_Diffuse`
- `EContentRootFolder_Opacity` = `EContentRootFolder_Opacity`
- `EContentRootFolder_Bump` = `EContentRootFolder_Bump`
- `EContentRootFolder_Glow` = `EContentRootFolder_Glow`
- `EContentRootFolder_Reflection` = `EContentRootFolder_Reflection`
- `EContentRootFolder_Specular` = `EContentRootFolder_Specular`
- `EContentRootFolder_Blend` = `EContentRootFolder_Blend`
- `EContentRootFolder_Displacement` = `EContentRootFolder_Displacement`
- `EContentRootFolder_IBL` = `EContentRootFolder_IBL`
- `EContentRootFolder_WeightMap` = `EContentRootFolder_WeightMap`
- `EContentRootFolder_Metallic` = `EContentRootFolder_Metallic`
- `EContentRootFolder_Roughness` = `EContentRootFolder_Roughness`
- `EContentRootFolder_AO` = `EContentRootFolder_AO`
- `EContentRootFolder_LensFlare` = `EContentRootFolder_LensFlare`
- `EContentRootFolder_IES` = `EContentRootFolder_IES`
- `EContentRootFolder_IMDL` = `EContentRootFolder_IMDL`
- `EContentRootFolder_Tree` = `EContentRootFolder_Tree`
- `EContentRootFolder_Grass` = `EContentRootFolder_Grass`
- `EContentRootFolder_Particle` = `EContentRootFolder_Particle`
- `EContentRootFolder_Terrain` = `EContentRootFolder_Terrain`
- `EContentRootFolder_Water` = `EContentRootFolder_Water`
- `EContentRootFolder_Sky` = `EContentRootFolder_Sky`
- `EContentRootFolder_MotionPath` = `EContentRootFolder_MotionPath`
- `EContentRootFolder_Props` = `EContentRootFolder_Props`
- `EContentRootFolder_Building` = `EContentRootFolder_Building`
- `EContentRootFolder_Sound` = `EContentRootFolder_Sound`
- `EContentRootFolder_Video` = `EContentRootFolder_Video`
- `EContentRootFolder_Digital_Human_Shader_Resource` = `EContentRootFolder_Digital_Human_Shader_Resource`
- `EContentRootFolder_SSS_Shader_Resource` = `EContentRootFolder_SSS_Shader_Resource`
- `EContentRootFolder_Spring` = `EContentRootFolder_Spring`
- `EContentRootFolder_LuaScript` = `EContentRootFolder_LuaScript`
- `EContentRootFolder_Fashion_Gen_Resource` = `EContentRootFolder_Fashion_Gen_Resource`
- `EContentRootFolder_MotionPuppet` = `EContentRootFolder_MotionPuppet`
- `EContentRootFolder_FacePuppet` = `EContentRootFolder_FacePuppet`
- `EContentRootFolder_SubstancePreset` = `EContentRootFolder_SubstancePreset`
- `EContentRootFolder_ContentPatch` = `EContentRootFolder_ContentPatch`
- `EContentRootFolder_SpringProfile` = `EContentRootFolder_SpringProfile`
- `EContentRootFolder_Dictionary` = `EContentRootFolder_Dictionary`
- `EContentRootFolder_Quantity` = `EContentRootFolder_Quantity`
- `EContentRootFolder_Invalid` = `EContentRootFolder_Invalid`

### EControlType

- `EControlType_Float` = `EControlType_Float`
- `EControlType_Transform` = `EControlType_Transform`

### EConvertCharacterLevel

- `EConvertCharacterLevel_ActorBuild` = `EConvertCharacterLevel_ActorBuild`
- `EConvertCharacterLevel_LOD1` = `EConvertCharacterLevel_LOD1`
- `EConvertCharacterLevel_LOD2` = `EConvertCharacterLevel_LOD2`

### ECoordinateAxes

- `ECoordinateAxes_Unknown` = `ECoordinateAxes_Unknown`
- `ECoordinateAxes_X` = `ECoordinateAxes_X`
- `ECoordinateAxes_Y` = `ECoordinateAxes_Y`
- `ECoordinateAxes_Z` = `ECoordinateAxes_Z`
- `ECoordinateAxes_XY` = `ECoordinateAxes_XY`
- `ECoordinateAxes_YZ` = `ECoordinateAxes_YZ`
- `ECoordinateAxes_XZ` = `ECoordinateAxes_XZ`
- `ECoordinateAxes_All` = `ECoordinateAxes_All`

### ECoordinateAxis

- `ECoordinateAxis_X` = `ECoordinateAxis_X`
- `ECoordinateAxis_NegativeX` = `ECoordinateAxis_NegativeX`
- `ECoordinateAxis_Y` = `ECoordinateAxis_Y`
- `ECoordinateAxis_NegativeY` = `ECoordinateAxis_NegativeY`
- `ECoordinateAxis_Z` = `ECoordinateAxis_Z`
- `ECoordinateAxis_NegativeZ` = `ECoordinateAxis_NegativeZ`

### ECoordinateSpace

- `ECoordinateSpace_World` = `ECoordinateSpace_World`
- `ECoordinateSpace_Local` = `ECoordinateSpace_Local`

### ECoordinateSystem

- `ECoordinateSystem_RightHand` = `ECoordinateSystem_RightHand`
- `ECoordinateSystem_LeftHand` = `ECoordinateSystem_LeftHand`

### EDeviceType

- `EDeviceType_Facial` = `EDeviceType_Facial`
- `EDeviceType_Body` = `EDeviceType_Body`
- `EDeviceType_Hand` = `EDeviceType_Hand`
- `EDeviceType_All` = `EDeviceType_All`

### EDialogType

- `EDialogType_Normal` = `EDialogType_Normal`
- `EDialogType_Exclusive` = `EDialogType_Exclusive`

### EDockWidgetAreas

- `EDockWidgetAreas_NoDockwidgetArea` = `EDockWidgetAreas_NoDockwidgetArea`
- `EDockWidgetAreas_LeftDockWidgetArea` = `EDockWidgetAreas_LeftDockWidgetArea`
- `EDockWidgetAreas_RightDockWidgetArea` = `EDockWidgetAreas_RightDockWidgetArea`
- `EDockWidgetAreas_TopDockWidgetArea` = `EDockWidgetAreas_TopDockWidgetArea`
- `EDockWidgetAreas_BottomDockWidgetArea` = `EDockWidgetAreas_BottomDockWidgetArea`
- `EDockWidgetAreas_AllFeatures` = `EDockWidgetAreas_AllFeatures`

### EDockWidgetFeatures

- `EDockWidgetFeatures_NoFeatures` = `EDockWidgetFeatures_NoFeatures`
- `EDockWidgetFeatures_Closable` = `EDockWidgetFeatures_Closable`
- `EDockWidgetFeatures_Movable` = `EDockWidgetFeatures_Movable`
- `EDockWidgetFeatures_Floatable` = `EDockWidgetFeatures_Floatable`
- `EDockWidgetFeatures_VerticalTitleBar` = `EDockWidgetFeatures_VerticalTitleBar`
- `EDockWidgetFeatures_AllFeatures` = `EDockWidgetFeatures_AllFeatures`

### EEulerOrder

- `EEulerOrder_XYZ` = `EEulerOrder_XYZ`
- `EEulerOrder_ZYX` = `EEulerOrder_ZYX`
- `EEulerOrder_XZY` = `EEulerOrder_XZY`
- `EEulerOrder_YZX` = `EEulerOrder_YZX`
- `EEulerOrder_YXZ` = `EEulerOrder_YXZ`
- `EEulerOrder_ZXY` = `EEulerOrder_ZXY`

### EExportFbxOptions

- `EExportFbxOptions__None` = `EExportFbxOptions__None`
- `EExportFbxOptions_FbxKey` = `EExportFbxOptions_FbxKey`
- `EExportFbxOptions_LightWaveYUp` = `EExportFbxOptions_LightWaveYUp`
- `EExportFbxOptions_LightWaveReferenceBone` = `EExportFbxOptions_LightWaveReferenceBone`
- `EExportFbxOptions_AutoSkinRigidMesh` = `EExportFbxOptions_AutoSkinRigidMesh`
- `EExportFbxOptions_AutoSkinRigidMeshWithDifferentBoneName` = `EExportFbxOptions_AutoSkinRigidMeshWithDifferentBoneName`
- `EExportFbxOptions_SaveHideMeshStateInOneSelectionSet` = `EExportFbxOptions_SaveHideMeshStateInOneSelectionSet`
- `EExportFbxOptions_ForceTrangleExport` = `EExportFbxOptions_ForceTrangleExport`
- `EExportFbxOptions_ExportMotion30SecOnly` = `EExportFbxOptions_ExportMotion30SecOnly`
- `EExportFbxOptions_TPoseOnMotionFirstFrame` = `EExportFbxOptions_TPoseOnMotionFirstFrame`
- `EExportFbxOptions_FirstMotionNotOffset` = `EExportFbxOptions_FirstMotionNotOffset`
- `EExportFbxOptions_ExportRootMotion` = `EExportFbxOptions_ExportRootMotion`
- `EExportFbxOptions_ZeroMotionRoot` = `EExportFbxOptions_ZeroMotionRoot`
- `EExportFbxOptions_TPoseForCreateMorphTargetMesh` = `EExportFbxOptions_TPoseForCreateMorphTargetMesh`
- `EExportFbxOptions_RemoveAllUnused` = `EExportFbxOptions_RemoveAllUnused`
- `EExportFbxOptions_RemoveBoneRoot` = `EExportFbxOptions_RemoveBoneRoot`
- `EExportFbxOptions_RemoveHiddenMesh` = `EExportFbxOptions_RemoveHiddenMesh`
- `EExportFbxOptions_RemoveUnusedMorph` = `EExportFbxOptions_RemoveUnusedMorph`
- `EExportFbxOptions_RemoveEyelash` = `EExportFbxOptions_RemoveEyelash`
- `EExportFbxOptions_RemoveTearLineAndOcclusion` = `EExportFbxOptions_RemoveTearLineAndOcclusion`
- `EExportFbxOptions_RemoveAllMesh` = `EExportFbxOptions_RemoveAllMesh`
- `EExportFbxOptions_RemoveAllMeshKeepMorph` = `EExportFbxOptions_RemoveAllMeshKeepMorph`
- `EExportFbxOptions_EmbedTexture` = `EExportFbxOptions_EmbedTexture`
- `EExportFbxOptions_ExportPbrTextureAsImageInDiffuseLayer` = `EExportFbxOptions_ExportPbrTextureAsImageInDiffuseLayer`
- `EExportFbxOptions_ExportPbrTextureAsImageInOneDirectory` = `EExportFbxOptions_ExportPbrTextureAsImageInOneDirectory`
- `EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory` = `EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory`
- `EExportFbxOptions_ExportPbrTextureAsSbsar` = `EExportFbxOptions_ExportPbrTextureAsSbsar`
- `EExportFbxOptions_ExportMetallicAlpha` = `EExportFbxOptions_ExportMetallicAlpha`
- `EExportFbxOptions_InverseNormalY` = `EExportFbxOptions_InverseNormalY`
- `EExportFbxOptions_InverseOpacity` = `EExportFbxOptions_InverseOpacity`
- `EExportFbxOptions_MergeDiffuseOpacityMap` = `EExportFbxOptions_MergeDiffuseOpacityMap`
- `EExportFbxOptions_MayaAdjustMaterial` = `EExportFbxOptions_MayaAdjustMaterial`
- `EExportFbxOptions_ConvertTifToPNG` = `EExportFbxOptions_ConvertTifToPNG`

### EExportGoZPose

- `EExportGoZPose_Current` = `EExportGoZPose_Current`
- `EExportGoZPose_TPose` = `EExportGoZPose_TPose`
- `EExportGoZPose_APose` = `EExportGoZPose_APose`

### EExportMeshMotionMode

- `EExportMeshMotionMode_MeshOnly` = `EExportMeshMotionMode_MeshOnly`
- `EExportMeshMotionMode_MotionOnly` = `EExportMeshMotionMode_MotionOnly`
- `EExportMeshMotionMode_MeshWithMotion` = `EExportMeshMotionMode_MeshWithMotion`

### EExportTextureFormat

- `EExportTextureFormat_Default` = `EExportTextureFormat_Default`
- `EExportTextureFormat_Bmp` = `EExportTextureFormat_Bmp`
- `EExportTextureFormat_Jpeg` = `EExportTextureFormat_Jpeg`
- `EExportTextureFormat_Tga` = `EExportTextureFormat_Tga`
- `EExportTextureFormat_Png` = `EExportTextureFormat_Png`
- `EExportTextureFormat_Tif` = `EExportTextureFormat_Tif`

### EExportTextureSize

- `EExportTextureSize_Original` = `EExportTextureSize_Original`
- `EExportTextureSize_Size_256` = `EExportTextureSize_Size_256`
- `EExportTextureSize_Size_512` = `EExportTextureSize_Size_512`
- `EExportTextureSize_Size_1024` = `EExportTextureSize_Size_1024`
- `EExportTextureSize_Size_2048` = `EExportTextureSize_Size_2048`
- `EExportTextureSize_Size_4096` = `EExportTextureSize_Size_4096`

### EFaceHairType

- `EFaceHairType_NOT_FACEHAIR` = `EFaceHairType_NOT_FACEHAIR`
- `EFaceHairType_Eyebrows` = `EFaceHairType_Eyebrows`
- `EFaceHairType_Beard_Mustache` = `EFaceHairType_Beard_Mustache`
- `EFaceHairType_Beard_Goatee` = `EFaceHairType_Beard_Goatee`
- `EFaceHairType_Beard_Sideburns` = `EFaceHairType_Beard_Sideburns`
- `EFaceHairType_Beard_SoulPatch` = `EFaceHairType_Beard_SoulPatch`
- `EFaceHairType_Beard_FullBeard` = `EFaceHairType_Beard_FullBeard`
- `EFaceHairType_Beard_Accessory` = `EFaceHairType_Beard_Accessory`

### EFacialAnimationMode

- `EFacialAnimationMode_CreateNew` = `EFacialAnimationMode_CreateNew`
- `EFacialAnimationMode_Replace` = `EFacialAnimationMode_Replace`
- `EFacialAnimationMode_Blend` = `EFacialAnimationMode_Blend`

### EFacialProfile

- `EFacialProfile__None` = `EFacialProfile__None`
- `EFacialProfile_CC5MetaHuman` = `EFacialProfile_CC5MetaHuman`
- `EFacialProfile_CC4Extended` = `EFacialProfile_CC4Extended`
- `EFacialProfile_CC4Standard` = `EFacialProfile_CC4Standard`
- `EFacialProfile_Traditional` = `EFacialProfile_Traditional`

### EFloatControlAttribute

- `EFloatControlAttribute__None` = `EFloatControlAttribute__None`
- `EFloatControlAttribute_NonZeroValue` = `EFloatControlAttribute_NonZeroValue`

### EFloorContactType

- `EFloorContactType_HandBottom` = `EFloorContactType_HandBottom`
- `EFloorContactType_HandBack` = `EFloorContactType_HandBack`
- `EFloorContactType_HandMiddle` = `EFloorContactType_HandMiddle`
- `EFloorContactType_HandFront` = `EFloorContactType_HandFront`
- `EFloorContactType_HandIn` = `EFloorContactType_HandIn`
- `EFloorContactType_HandOut` = `EFloorContactType_HandOut`
- `EFloorContactType_FootBottom` = `EFloorContactType_FootBottom`
- `EFloorContactType_FootBack` = `EFloorContactType_FootBack`
- `EFloorContactType_FootMiddle` = `EFloorContactType_FootMiddle`
- `EFloorContactType_FootFront` = `EFloorContactType_FootFront`
- `EFloorContactType_FootIn` = `EFloorContactType_FootIn`
- `EFloorContactType_FootOut` = `EFloorContactType_FootOut`
- `EFloorContactType_All` = `EFloorContactType_All`

### EHSBodyType

- `EHSBodyType_Male` = `EHSBodyType_Male`
- `EHSBodyType_Female` = `EHSBodyType_Female`
- `EHSBodyType_Baby` = `EHSBodyType_Baby`
- `EHSBodyType_Neutral` = `EHSBodyType_Neutral`
- `EHSBodyType_Current` = `EHSBodyType_Current`

### EHSLevel

- `EHSLevel_Zero` = `EHSLevel_Zero`
- `EHSLevel_One` = `EHSLevel_One`
- `EHSLevel_Two` = `EHSLevel_Two`

### EHSMode

- `EHSMode_Pro` = `EHSMode_Pro`
- `EHSMode_Auto` = `EHSMode_Auto`

### EHairType

- `EHairType_UNKNOWN` = `EHairType_UNKNOWN`
- `EHairType_Hair_Top` = `EHairType_Hair_Top`
- `EHairType_Hair_Base` = `EHairType_Hair_Base`
- `EHairType_Hair_Rear` = `EHairType_Hair_Rear`
- `EHairType_Hair_Bangs` = `EHairType_Hair_Bangs`
- `EHairType_Hair_Accessory` = `EHairType_Hair_Accessory`

### EHandDataSource

- `EHandDataSource_RightHand` = `EHandDataSource_RightHand`
- `EHandDataSource_LeftHand` = `EHandDataSource_LeftHand`

### EHandJoin

- `EHandJoin_Shoulder` = `EHandJoin_Shoulder`
- `EHandJoin_Elbow` = `EHandJoin_Elbow`
- `EHandJoin_Wrist` = `EHandJoin_Wrist`
- `EHandJoin_Hand` = `EHandJoin_Hand`
- `EHandJoin_Invalid` = `EHandJoin_Invalid`

### EHandJoinType

- `EHandJoinType_UseParentBone` = `EHandJoinType_UseParentBone`
- `EHandJoinType_UseChildBone` = `EHandJoinType_UseChildBone`

### EHikEffector

- `EHikEffector_Invalid` = `EHikEffector_Invalid`
- `EHikEffector_Hip` = `EHikEffector_Hip`
- `EHikEffector_LeftFoot` = `EHikEffector_LeftFoot`
- `EHikEffector_RightFoot` = `EHikEffector_RightFoot`
- `EHikEffector_LeftHand` = `EHikEffector_LeftHand`
- `EHikEffector_RightHand` = `EHikEffector_RightHand`
- `EHikEffector_LeftKnee` = `EHikEffector_LeftKnee`
- `EHikEffector_RightKnee` = `EHikEffector_RightKnee`
- `EHikEffector_LeftElbow` = `EHikEffector_LeftElbow`
- `EHikEffector_RightElbow` = `EHikEffector_RightElbow`
- `EHikEffector_ChestOrigin` = `EHikEffector_ChestOrigin`
- `EHikEffector_Neck` = `EHikEffector_Neck`
- `EHikEffector_LeftToe` = `EHikEffector_LeftToe`
- `EHikEffector_RightToe` = `EHikEffector_RightToe`
- `EHikEffector_LeftShoulder` = `EHikEffector_LeftShoulder`
- `EHikEffector_RightShoulder` = `EHikEffector_RightShoulder`
- `EHikEffector_Head` = `EHikEffector_Head`
- `EHikEffector_LeftHip` = `EHikEffector_LeftHip`
- `EHikEffector_RightHip` = `EHikEffector_RightHip`
- `EHikEffector_Quantity` = `EHikEffector_Quantity`

### EHikEffectorType

- `EHikEffectorType_Translate` = `EHikEffectorType_Translate`
- `EHikEffectorType_Rotate` = `EHikEffectorType_Rotate`

### EImportExpressionPart

- `EImportExpressionPart_Body` = `EImportExpressionPart_Body`
- `EImportExpressionPart_Eyes` = `EImportExpressionPart_Eyes`
- `EImportExpressionPart_Teeth` = `EImportExpressionPart_Teeth`
- `EImportExpressionPart_Tongue` = `EImportExpressionPart_Tongue`

### EImportFbxOption

- `EImportFbxOption__None` = `EImportFbxOption__None`
- `EImportFbxOption_StandardHumanCharacter` = `EImportFbxOption_StandardHumanCharacter`
- `EImportFbxOption_Humanoid` = `EImportFbxOption_Humanoid`
- `EImportFbxOption_Creature` = `EImportFbxOption_Creature`
- `EImportFbxOption_Prop` = `EImportFbxOption_Prop`

### EIncludeMotionType

- `EIncludeMotionType_Current_Pose` = `EIncludeMotionType_Current_Pose`
- `EIncludeMotionType_Current_Animation` = `EIncludeMotionType_Current_Animation`
- `EIncludeMotionType_Custom` = `EIncludeMotionType_Custom`

### ELanguage

- `ELanguage_TW` = `ELanguage_TW`
- `ELanguage_US` = `ELanguage_US`

### ELevelCharacterTemplateType

- `ELevelCharacterTemplateType_High` = `ELevelCharacterTemplateType_High`
- `ELevelCharacterTemplateType_Middle` = `ELevelCharacterTemplateType_Middle`
- `ELevelCharacterTemplateType_Low` = `ELevelCharacterTemplateType_Low`
- `ELevelCharacterTemplateType_Custom` = `ELevelCharacterTemplateType_Custom`

### ELinkObjectAlignType

- `ELinkObjectAlignType__None` = `ELinkObjectAlignType__None`
- `ELinkObjectAlignType_Position` = `ELinkObjectAlignType_Position`
- `ELinkObjectAlignType_Position_And_Rotation` = `ELinkObjectAlignType_Position_And_Rotation`
- `ELinkObjectAlignType_NO_OFFSET` = `ELinkObjectAlignType_NO_OFFSET`

### ELoadFileOption

- `ELoadFileOption__None` = `ELoadFileOption__None`
- `ELoadFileOption_NoProgress` = `ELoadFileOption_NoProgress`

### EMDpropCrowdExitType

- `EMDpropCrowdExitType_DefaultRate` = `EMDpropCrowdExitType_DefaultRate`
- `EMDpropCrowdExitType_InteractTimes` = `EMDpropCrowdExitType_InteractTimes`
- `EMDpropCrowdExitType_NeverExit` = `EMDpropCrowdExitType_NeverExit`

### EMaterialTextureChannel

- `EMaterialTextureChannel_Metallic` = `EMaterialTextureChannel_Metallic`
- `EMaterialTextureChannel_Diffuse` = `EMaterialTextureChannel_Diffuse`
- `EMaterialTextureChannel_Specular` = `EMaterialTextureChannel_Specular`
- `EMaterialTextureChannel_Shininess` = `EMaterialTextureChannel_Shininess`
- `EMaterialTextureChannel_Glow` = `EMaterialTextureChannel_Glow`
- `EMaterialTextureChannel_Displacement` = `EMaterialTextureChannel_Displacement`
- `EMaterialTextureChannel_Opacity` = `EMaterialTextureChannel_Opacity`
- `EMaterialTextureChannel_DiffuseBlend` = `EMaterialTextureChannel_DiffuseBlend`
- `EMaterialTextureChannel_Bump` = `EMaterialTextureChannel_Bump`
- `EMaterialTextureChannel_Reflection` = `EMaterialTextureChannel_Reflection`
- `EMaterialTextureChannel_Refraction` = `EMaterialTextureChannel_Refraction`
- `EMaterialTextureChannel_Cube` = `EMaterialTextureChannel_Cube`
- `EMaterialTextureChannel_AmbientOcclusion` = `EMaterialTextureChannel_AmbientOcclusion`
- `EMaterialTextureChannel_Normal` = `EMaterialTextureChannel_Normal`
- `EMaterialTextureChannel_VectorDisplacement` = `EMaterialTextureChannel_VectorDisplacement`
- `EMaterialTextureChannel_Quantity` = `EMaterialTextureChannel_Quantity`
- `EMaterialTextureChannel_Roughness` = `EMaterialTextureChannel_Roughness`

### EMaterialType

- `EMaterialType_RTX_Real_Time` = `EMaterialType_RTX_Real_Time`
- `EMaterialType_RTX_Path_Traced` = `EMaterialType_RTX_Path_Traced`

### EMenu

- `EMenu_Plugins` = `EMenu_Plugins`

### EMocapState

- `EMocapState_Unknown` = `EMocapState_Unknown`
- `EMocapState_Preview` = `EMocapState_Preview`
- `EMocapState_Record` = `EMocapState_Record`
- `EMocapState_PreviewWithoutPlay` = `EMocapState_PreviewWithoutPlay`

### EModeType

- `EModeType__None` = `EModeType__None`
- `EModeType_DirectPuppet` = `EModeType_DirectPuppet`
- `EModeType_MotionPuppet` = `EModeType_MotionPuppet`
- `EModeType_PropPuppet` = `EModeType_PropPuppet`
- `EModeType_AvatarProport` = `EModeType_AvatarProport`
- `EModeType_AvatarPoseOffset` = `EModeType_AvatarPoseOffset`
- `EModeType_Duplicate` = `EModeType_Duplicate`
- `EModeType_IkEditing` = `EModeType_IkEditing`
- `EModeType_ReachTarget` = `EModeType_ReachTarget`
- `EModeType_QuickLight` = `EModeType_QuickLight`
- `EModeType_FacePuppet` = `EModeType_FacePuppet`
- `EModeType_FaceKey` = `EModeType_FaceKey`
- `EModeType_VisemeSmooth` = `EModeType_VisemeSmooth`
- `EModeType_EditMeshByFace` = `EModeType_EditMeshByFace`
- `EModeType_EditMeshByVertex` = `EModeType_EditMeshByVertex`
- `EModeType_EditMeshByElement` = `EModeType_EditMeshByElement`
- `EModeType_MorphAnimation` = `EModeType_MorphAnimation`
- `EModeType_AdjustTPose` = `EModeType_AdjustTPose`
- `EModeType_EditNormal` = `EModeType_EditNormal`
- `EModeType_PaintMaskByBrush` = `EModeType_PaintMaskByBrush`
- `EModeType_MotionMatching` = `EModeType_MotionMatching`
- `EModeType_AutoRig` = `EModeType_AutoRig`
- `EModeType_AiPosing` = `EModeType_AiPosing`
- `EModeType_AdjustMixerSliderBoneTranslate` = `EModeType_AdjustMixerSliderBoneTranslate`
- `EModeType_Unknown` = `EModeType_Unknown`

### EMotionApplyMode

- `EMotionApplyMode_ReferenceToAvatar` = `EMotionApplyMode_ReferenceToAvatar`
- `EMotionApplyMode_ReferenceToCoordinate` = `EMotionApplyMode_ReferenceToCoordinate`

### EMotionSettingOption

- `EMotionSettingOption__None` = `EMotionSettingOption__None`
- `EMotionSettingOption_ResetMotionRoot` = `EMotionSettingOption_ResetMotionRoot`
- `EMotionSettingOption_ResetMotionRootRotate` = `EMotionSettingOption_ResetMotionRootRotate`
- `EMotionSettingOption_AlignActorMotion` = `EMotionSettingOption_AlignActorMotion`
- `EMotionSettingOption_AlignToActorOrientation` = `EMotionSettingOption_AlignToActorOrientation`

### EMsgButton

- `EMsgButton_NoButton` = `EMsgButton_NoButton`
- `EMsgButton_Ok` = `EMsgButton_Ok`
- `EMsgButton_Save` = `EMsgButton_Save`
- `EMsgButton_SaveAll` = `EMsgButton_SaveAll`
- `EMsgButton_Open` = `EMsgButton_Open`
- `EMsgButton_Yes` = `EMsgButton_Yes`
- `EMsgButton_YesToAll` = `EMsgButton_YesToAll`
- `EMsgButton_No` = `EMsgButton_No`
- `EMsgButton_NoToAll` = `EMsgButton_NoToAll`
- `EMsgButton_Abort` = `EMsgButton_Abort`
- `EMsgButton_Retry` = `EMsgButton_Retry`
- `EMsgButton_Overlook` = `EMsgButton_Overlook`
- `EMsgButton_Close` = `EMsgButton_Close`
- `EMsgButton_Cancel` = `EMsgButton_Cancel`
- `EMsgButton_Discard` = `EMsgButton_Discard`
- `EMsgButton_Help` = `EMsgButton_Help`
- `EMsgButton_Apply` = `EMsgButton_Apply`
- `EMsgButton_Reset` = `EMsgButton_Reset`
- `EMsgButton_RestoreDefaults` = `EMsgButton_RestoreDefaults`
- `EMsgButton_OkDontAskAgain` = `EMsgButton_OkDontAskAgain`

### EObjectEventType

- `EObjectEventType_VisemeChangeEvent` = `EObjectEventType_VisemeChangeEvent`

### EObjectModifiedType

- `EObjectModifiedType_Transform` = `EObjectModifiedType_Transform`
- `EObjectModifiedType_Attribute` = `EObjectModifiedType_Attribute`
- `EObjectModifiedType_Material` = `EObjectModifiedType_Material`
- `EObjectModifiedType_MorphWeight` = `EObjectModifiedType_MorphWeight`
- `EObjectModifiedType_Motion` = `EObjectModifiedType_Motion`
- `EObjectModifiedType_Texture` = `EObjectModifiedType_Texture`
- `EObjectModifiedType_Wrinkle` = `EObjectModifiedType_Wrinkle`

### EObjectType

- `EObjectType_Object` = `EObjectType_Object`
- `EObjectType_Avatar` = `EObjectType_Avatar`
- `EObjectType_Hair` = `EObjectType_Hair`
- `EObjectType_Cloth` = `EObjectType_Cloth`
- `EObjectType_Accessory` = `EObjectType_Accessory`
- `EObjectType_Prop` = `EObjectType_Prop`
- `EObjectType_Camera` = `EObjectType_Camera`
- `EObjectType_Particle` = `EObjectType_Particle`
- `EObjectType_Light` = `EObjectType_Light`
- `EObjectType_SpotLight` = `EObjectType_SpotLight`
- `EObjectType_PointLight` = `EObjectType_PointLight`
- `EObjectType_DirectionalLight` = `EObjectType_DirectionalLight`
- `EObjectType_PopcornFX` = `EObjectType_PopcornFX`
- `EObjectType_Path` = `EObjectType_Path`
- `EObjectType_Sky` = `EObjectType_Sky`
- `EObjectType_LightAvatar` = `EObjectType_LightAvatar`
- `EObjectType_MDProp` = `EObjectType_MDProp`
- `EObjectType_ImageLayer` = `EObjectType_ImageLayer`

### EPathType

- `EPathType_Temp` = `EPathType_Temp`
- `EPathType_TemplateContent` = `EPathType_TemplateContent`
- `EPathType_CustomContent` = `EPathType_CustomContent`
- `EPathType_ProgramDefault` = `EPathType_ProgramDefault`
- `EPathType_Puppet` = `EPathType_Puppet`
- `EPathType_FacialLayer` = `EPathType_FacialLayer`
- `EPathType_ShareTemplateContent` = `EPathType_ShareTemplateContent`
- `EPathType_Thumb` = `EPathType_Thumb`
- `EPathType_Image` = `EPathType_Image`
- `EPathType_CreatorAssets` = `EPathType_CreatorAssets`
- `EPathType_Resource` = `EPathType_Resource`
- `EPathType_FacialSystem` = `EPathType_FacialSystem`
- `EPathType_CustomWidget` = `EPathType_CustomWidget`
- `EPathType_iCloneAssets` = `EPathType_iCloneAssets`
- `EPathType_CCBaseData` = `EPathType_CCBaseData`

### EPopcornFxSamplerType

- `EPopcornFxSamplerType_MESH` = `EPopcornFxSamplerType_MESH`
- `EPopcornFxSamplerType_IMAGE` = `EPopcornFxSamplerType_IMAGE`
- `EPopcornFxSamplerType_SOUND` = `EPopcornFxSamplerType_SOUND`
- `EPopcornFxSamplerType_TEXT` = `EPopcornFxSamplerType_TEXT`
- `EPopcornFxSamplerType_PATH` = `EPopcornFxSamplerType_PATH`
- `EPopcornFxSamplerType_CURVE` = `EPopcornFxSamplerType_CURVE`

### EPositionUnit

- `EPositionUnit_Centimeters` = `EPositionUnit_Centimeters`
- `EPositionUnit_Meters` = `EPositionUnit_Meters`

### EPostEffect

- `EPostEffect__None` = `EPostEffect__None`
- `EPostEffect_Default` = `EPostEffect_Default`
- `EPostEffect_Faded` = `EPostEffect_Faded`
- `EPostEffect_Cold_Weak` = `EPostEffect_Cold_Weak`
- `EPostEffect_Cold_Strong` = `EPostEffect_Cold_Strong`
- `EPostEffect_Warm_Weak` = `EPostEffect_Warm_Weak`
- `EPostEffect_Warn_Strong` = `EPostEffect_Warn_Strong`
- `EPostEffect_Aged` = `EPostEffect_Aged`
- `EPostEffect_Retro` = `EPostEffect_Retro`
- `EPostEffect_Corrupted_purple` = `EPostEffect_Corrupted_purple`
- `EPostEffect_Black_And_White` = `EPostEffect_Black_And_White`

### EPropertyType

- `EPropertyType_PT_LeftHandThumbSize` = `EPropertyType_PT_LeftHandThumbSize`
- `EPropertyType_PT_LeftHandIndexSize` = `EPropertyType_PT_LeftHandIndexSize`
- `EPropertyType_PT_LeftHandMiddleSize` = `EPropertyType_PT_LeftHandMiddleSize`
- `EPropertyType_PT_LeftHandRingSize` = `EPropertyType_PT_LeftHandRingSize`
- `EPropertyType_PT_LeftHandPinkySize` = `EPropertyType_PT_LeftHandPinkySize`
- `EPropertyType_PT_LeftHandExtraSize` = `EPropertyType_PT_LeftHandExtraSize`
- `EPropertyType_PT_RightHandThumbSize` = `EPropertyType_PT_RightHandThumbSize`
- `EPropertyType_PT_RightHandIndexSize` = `EPropertyType_PT_RightHandIndexSize`
- `EPropertyType_PT_RightHandMiddleSize` = `EPropertyType_PT_RightHandMiddleSize`
- `EPropertyType_PT_RightHandRingSize` = `EPropertyType_PT_RightHandRingSize`
- `EPropertyType_PT_RightHandPinkySize` = `EPropertyType_PT_RightHandPinkySize`
- `EPropertyType_PT_RightHandExtraSize` = `EPropertyType_PT_RightHandExtraSize`
- `EPropertyType_PT_LeftFootThumbSize` = `EPropertyType_PT_LeftFootThumbSize`
- `EPropertyType_PT_LeftFootIndexSize` = `EPropertyType_PT_LeftFootIndexSize`
- `EPropertyType_PT_LeftFootMiddleSize` = `EPropertyType_PT_LeftFootMiddleSize`
- `EPropertyType_PT_LeftFootRingSize` = `EPropertyType_PT_LeftFootRingSize`
- `EPropertyType_PT_LeftFootPinkySize` = `EPropertyType_PT_LeftFootPinkySize`
- `EPropertyType_PT_LeftFootExtraSize` = `EPropertyType_PT_LeftFootExtraSize`
- `EPropertyType_PT_RightFootThumbSize` = `EPropertyType_PT_RightFootThumbSize`
- `EPropertyType_PT_RightFootIndexSize` = `EPropertyType_PT_RightFootIndexSize`
- `EPropertyType_PT_RightFootMiddleSize` = `EPropertyType_PT_RightFootMiddleSize`
- `EPropertyType_PT_RightFootRingSize` = `EPropertyType_PT_RightFootRingSize`
- `EPropertyType_PT_RightFootPinkySize` = `EPropertyType_PT_RightFootPinkySize`
- `EPropertyType_PT_RightFootExtraSize` = `EPropertyType_PT_RightFootExtraSize`
- `EPropertyType_PT_HandBottomToWrist` = `EPropertyType_PT_HandBottomToWrist`
- `EPropertyType_PT_HandMiddleToWrist` = `EPropertyType_PT_HandMiddleToWrist`
- `EPropertyType_PT_HandBackToWrist` = `EPropertyType_PT_HandBackToWrist`
- `EPropertyType_PT_HandFrontToMiddle` = `EPropertyType_PT_HandFrontToMiddle`
- `EPropertyType_PT_HandInToWrist` = `EPropertyType_PT_HandInToWrist`
- `EPropertyType_PT_HandOutToWrist` = `EPropertyType_PT_HandOutToWrist`
- `EPropertyType_PT_FootBottomToAnkle` = `EPropertyType_PT_FootBottomToAnkle`
- `EPropertyType_PT_FootMiddleToAnkle` = `EPropertyType_PT_FootMiddleToAnkle`
- `EPropertyType_PT_FootBackToAnkle` = `EPropertyType_PT_FootBackToAnkle`
- `EPropertyType_PT_FootFrontToMiddle` = `EPropertyType_PT_FootFrontToMiddle`
- `EPropertyType_PT_FootInToAnkle` = `EPropertyType_PT_FootInToAnkle`
- `EPropertyType_PT_FootOutToAnkle` = `EPropertyType_PT_FootOutToAnkle`
- `EPropertyType_PT_RealisticShoulder` = `EPropertyType_PT_RealisticShoulder`
- `EPropertyType_PT_Quantity_Version26` = `EPropertyType_PT_Quantity_Version26`
- `EPropertyType_PT_LeftUpLegRoll` = `EPropertyType_PT_LeftUpLegRoll`
- `EPropertyType_PT_LeftLegRoll` = `EPropertyType_PT_LeftLegRoll`
- `EPropertyType_PT_RightUpLegRoll` = `EPropertyType_PT_RightUpLegRoll`
- `EPropertyType_PT_RightLegRoll` = `EPropertyType_PT_RightLegRoll`
- `EPropertyType_PT_LeftArmRoll` = `EPropertyType_PT_LeftArmRoll`
- `EPropertyType_PT_LeftForeArmRoll` = `EPropertyType_PT_LeftForeArmRoll`
- `EPropertyType_PT_RightArmRoll` = `EPropertyType_PT_RightArmRoll`
- `EPropertyType_PT_RightForeArmRoll` = `EPropertyType_PT_RightForeArmRoll`
- `EPropertyType_PT_Quantity_Version29` = `EPropertyType_PT_Quantity_Version29`
- `EPropertyType_PT_AnkleHeightCompensation` = `EPropertyType_PT_AnkleHeightCompensation`
- `EPropertyType_PT_AnkleProximityCompensation` = `EPropertyType_PT_AnkleProximityCompensation`
- `EPropertyType_PT_HipsHeightCompensation` = `EPropertyType_PT_HipsHeightCompensation`
- `EPropertyType_PT_HipsTOffsetZ` = `EPropertyType_PT_HipsTOffsetZ`
- `EPropertyType_PT_RollExtractionMode` = `EPropertyType_PT_RollExtractionMode`
- `EPropertyType_PT_Quantity_Version210` = `EPropertyType_PT_Quantity_Version210`
- `EPropertyType_PT_SpineStiffness` = `EPropertyType_PT_SpineStiffness`
- `EPropertyType_PT_CtrlNeckStiffness` = `EPropertyType_PT_CtrlNeckStiffness`
- `EPropertyType_PT_FootContactStiffness` = `EPropertyType_PT_FootContactStiffness`
- `EPropertyType_PT_CtrlResistMaximumExtensionLeftKnee` = `EPropertyType_PT_CtrlResistMaximumExtensionLeftKnee`
- `EPropertyType_PT_CtrlResistMaximumExtensionRightKnee` = `EPropertyType_PT_CtrlResistMaximumExtensionRightKnee`
- `EPropertyType_PT_CtrlResistMaximumExtensionLeftElbow` = `EPropertyType_PT_CtrlResistMaximumExtensionLeftElbow`
- `EPropertyType_PT_CtrlResistMaximumExtensionRightElbow` = `EPropertyType_PT_CtrlResistMaximumExtensionRightElbow`
- `EPropertyType_PT_CtrlResistCompressionFactorLeftKnee` = `EPropertyType_PT_CtrlResistCompressionFactorLeftKnee`
- `EPropertyType_PT_CtrlResistCompressionFactorRightKnee` = `EPropertyType_PT_CtrlResistCompressionFactorRightKnee`
- `EPropertyType_PT_CtrlResistCompressionFactorLeftElbow` = `EPropertyType_PT_CtrlResistCompressionFactorLeftElbow`
- `EPropertyType_PT_CtrlResistCompressionFactorRightElbow` = `EPropertyType_PT_CtrlResistCompressionFactorRightElbow`
- `EPropertyType_PT_HandFingerContactRollStiffness` = `EPropertyType_PT_HandFingerContactRollStiffness`
- `EPropertyType_PT_FootFingerContactRollStiffness` = `EPropertyType_PT_FootFingerContactRollStiffness`
- `EPropertyType_PT_HandContactStiffness` = `EPropertyType_PT_HandContactStiffness`
- `EPropertyType_PT_PullIterationCount` = `EPropertyType_PT_PullIterationCount`
- `EPropertyType_PT_LeftLegMaxExtensionAngle` = `EPropertyType_PT_LeftLegMaxExtensionAngle`
- `EPropertyType_PT_RightLegMaxExtensionAngle` = `EPropertyType_PT_RightLegMaxExtensionAngle`
- `EPropertyType_PT_LeftArmMaxExtensionAngle` = `EPropertyType_PT_LeftArmMaxExtensionAngle`
- `EPropertyType_PT_RightArmMaxExtensionAngle` = `EPropertyType_PT_RightArmMaxExtensionAngle`
- `EPropertyType_PT_ExtraCollarRatio` = `EPropertyType_PT_ExtraCollarRatio`
- `EPropertyType_PT_CollarStiffnessX` = `EPropertyType_PT_CollarStiffnessX`
- `EPropertyType_PT_CollarStiffnessY` = `EPropertyType_PT_CollarStiffnessY`
- `EPropertyType_PT_CollarStiffnessZ` = `EPropertyType_PT_CollarStiffnessZ`
- `EPropertyType_PT_ReachActorLeftShoulder` = `EPropertyType_PT_ReachActorLeftShoulder`
- `EPropertyType_PT_ReachActorRightShoulder` = `EPropertyType_PT_ReachActorRightShoulder`
- `EPropertyType_PT_RealisticLeftKneeSolving` = `EPropertyType_PT_RealisticLeftKneeSolving`
- `EPropertyType_PT_RealisticRightKneeSolving` = `EPropertyType_PT_RealisticRightKneeSolving`
- `EPropertyType_PT_StretchStartArmsAndLegs` = `EPropertyType_PT_StretchStartArmsAndLegs`
- `EPropertyType_PT_StretchStopArmsAndLegs` = `EPropertyType_PT_StretchStopArmsAndLegs`
- `EPropertyType_PT_TopSpineCorrection` = `EPropertyType_PT_TopSpineCorrection`
- `EPropertyType_PT_SnSScaleArmsAndLegs` = `EPropertyType_PT_SnSScaleArmsAndLegs`
- `EPropertyType_PT_SnSReachLeftWrist` = `EPropertyType_PT_SnSReachLeftWrist`
- `EPropertyType_PT_SnSReachRightWrist` = `EPropertyType_PT_SnSReachRightWrist`
- `EPropertyType_PT_SnSReachLeftAnkle` = `EPropertyType_PT_SnSReachLeftAnkle`
- `EPropertyType_PT_SnSReachRightAnkle` = `EPropertyType_PT_SnSReachRightAnkle`
- `EPropertyType_PT_SnSScaleSpine` = `EPropertyType_PT_SnSScaleSpine`
- `EPropertyType_PT_SnSScaleSpineChildren` = `EPropertyType_PT_SnSScaleSpineChildren`
- `EPropertyType_PT_SnSSpineFreedom` = `EPropertyType_PT_SnSSpineFreedom`
- `EPropertyType_PT_SnSReachChestEnd` = `EPropertyType_PT_SnSReachChestEnd`
- `EPropertyType_PT_SnSScaleNeck` = `EPropertyType_PT_SnSScaleNeck`
- `EPropertyType_PT_SnSNeckFreedom` = `EPropertyType_PT_SnSNeckFreedom`
- `EPropertyType_PT_SnSReachHead` = `EPropertyType_PT_SnSReachHead`
- `EPropertyType_PT_LeftUpLegRollEx` = `EPropertyType_PT_LeftUpLegRollEx`
- `EPropertyType_PT_LeftLegRollEx` = `EPropertyType_PT_LeftLegRollEx`
- `EPropertyType_PT_RightUpLegRollEx` = `EPropertyType_PT_RightUpLegRollEx`
- `EPropertyType_PT_RightLegRollEx` = `EPropertyType_PT_RightLegRollEx`
- `EPropertyType_PT_LeftArmRollEx` = `EPropertyType_PT_LeftArmRollEx`
- `EPropertyType_PT_LeftForeArmRollEx` = `EPropertyType_PT_LeftForeArmRollEx`
- `EPropertyType_PT_RightArmRollEx` = `EPropertyType_PT_RightArmRollEx`
- `EPropertyType_PT_RightForeArmRollEx` = `EPropertyType_PT_RightForeArmRollEx`
- `EPropertyType_PT_LeftAnkle` = `EPropertyType_PT_LeftAnkle`
- `EPropertyType_PT_RightAnkle` = `EPropertyType_PT_RightAnkle`
- `EPropertyType_PT_Chest` = `EPropertyType_PT_Chest`
- `EPropertyType_PT_LeftWrist` = `EPropertyType_PT_LeftWrist`
- `EPropertyType_PT_RightWrist` = `EPropertyType_PT_RightWrist`
- `EPropertyType_PT_LeftKnee` = `EPropertyType_PT_LeftKnee`
- `EPropertyType_PT_RightKnee` = `EPropertyType_PT_RightKnee`
- `EPropertyType_PT_Head` = `EPropertyType_PT_Head`
- `EPropertyType_PT_LeftElbow` = `EPropertyType_PT_LeftElbow`
- `EPropertyType_PT_RightElbow` = `EPropertyType_PT_RightElbow`
- `EPropertyType_PT_LeftAnkleRotation` = `EPropertyType_PT_LeftAnkleRotation`
- `EPropertyType_PT_RightAnkleRotation` = `EPropertyType_PT_RightAnkleRotation`
- `EPropertyType_PT_HeadRotation` = `EPropertyType_PT_HeadRotation`
- `EPropertyType_PT_LeftWristRotation` = `EPropertyType_PT_LeftWristRotation`
- `EPropertyType_PT_RightWristRotation` = `EPropertyType_PT_RightWristRotation`
- `EPropertyType_PT_LeftFingerBase` = `EPropertyType_PT_LeftFingerBase`
- `EPropertyType_PT_RightFingerBase` = `EPropertyType_PT_RightFingerBase`
- `EPropertyType_PT_LeftToesBase` = `EPropertyType_PT_LeftToesBase`
- `EPropertyType_PT_RightToesBase` = `EPropertyType_PT_RightToesBase`
- `EPropertyType_PT_LeftFingerBaseRotation` = `EPropertyType_PT_LeftFingerBaseRotation`
- `EPropertyType_PT_RightFingerBaseRotation` = `EPropertyType_PT_RightFingerBaseRotation`
- `EPropertyType_PT_LeftToesBaseRotation` = `EPropertyType_PT_LeftToesBaseRotation`
- `EPropertyType_PT_RightToesBaseRotation` = `EPropertyType_PT_RightToesBaseRotation`
- `EPropertyType_PT_ChestRotation` = `EPropertyType_PT_ChestRotation`
- `EPropertyType_PT_LowerChestRotation` = `EPropertyType_PT_LowerChestRotation`
- `EPropertyType_PT_LeftHandThumb` = `EPropertyType_PT_LeftHandThumb`
- `EPropertyType_PT_LeftHandIndex` = `EPropertyType_PT_LeftHandIndex`
- `EPropertyType_PT_LeftHandMiddle` = `EPropertyType_PT_LeftHandMiddle`
- `EPropertyType_PT_LeftHandRing` = `EPropertyType_PT_LeftHandRing`
- `EPropertyType_PT_LeftHandPinky` = `EPropertyType_PT_LeftHandPinky`
- `EPropertyType_PT_LeftHandExtraFinger` = `EPropertyType_PT_LeftHandExtraFinger`
- `EPropertyType_PT_RightHandThumb` = `EPropertyType_PT_RightHandThumb`
- `EPropertyType_PT_RightHandIndex` = `EPropertyType_PT_RightHandIndex`
- `EPropertyType_PT_RightHandMiddle` = `EPropertyType_PT_RightHandMiddle`
- `EPropertyType_PT_RightHandRing` = `EPropertyType_PT_RightHandRing`
- `EPropertyType_PT_RightHandPinky` = `EPropertyType_PT_RightHandPinky`
- `EPropertyType_PT_RightHandExtraFinger` = `EPropertyType_PT_RightHandExtraFinger`
- `EPropertyType_PT_LeftFootThumb` = `EPropertyType_PT_LeftFootThumb`
- `EPropertyType_PT_LeftFootIndex` = `EPropertyType_PT_LeftFootIndex`
- `EPropertyType_PT_LeftFootMiddle` = `EPropertyType_PT_LeftFootMiddle`
- `EPropertyType_PT_LeftFootRing` = `EPropertyType_PT_LeftFootRing`
- `EPropertyType_PT_LeftFootPinky` = `EPropertyType_PT_LeftFootPinky`
- `EPropertyType_PT_LeftFootExtraFinger` = `EPropertyType_PT_LeftFootExtraFinger`
- `EPropertyType_PT_RightFootThumb` = `EPropertyType_PT_RightFootThumb`
- `EPropertyType_PT_RightFootIndex` = `EPropertyType_PT_RightFootIndex`
- `EPropertyType_PT_RightFootMiddle` = `EPropertyType_PT_RightFootMiddle`
- `EPropertyType_PT_RightFootRing` = `EPropertyType_PT_RightFootRing`
- `EPropertyType_PT_RightFootPinky` = `EPropertyType_PT_RightFootPinky`
- `EPropertyType_PT_RightFootExtraFinger` = `EPropertyType_PT_RightFootExtraFinger`
- `EPropertyType_PT_CtrlPullLeftFoot` = `EPropertyType_PT_CtrlPullLeftFoot`
- `EPropertyType_PT_CtrlPullRightFoot` = `EPropertyType_PT_CtrlPullRightFoot`
- `EPropertyType_PT_CtrlPullLeftHand` = `EPropertyType_PT_CtrlPullLeftHand`
- `EPropertyType_PT_CtrlPullRightHand` = `EPropertyType_PT_CtrlPullRightHand`
- `EPropertyType_PT_CtrlPullHead` = `EPropertyType_PT_CtrlPullHead`
- `EPropertyType_PT_CtrlPullLeftToeBase` = `EPropertyType_PT_CtrlPullLeftToeBase`
- `EPropertyType_PT_CtrlPullLeftKnee` = `EPropertyType_PT_CtrlPullLeftKnee`
- `EPropertyType_PT_CtrlPullRightToeBase` = `EPropertyType_PT_CtrlPullRightToeBase`
- `EPropertyType_PT_CtrlPullRightKnee` = `EPropertyType_PT_CtrlPullRightKnee`
- `EPropertyType_PT_CtrlPullLeftFingerBase` = `EPropertyType_PT_CtrlPullLeftFingerBase`
- `EPropertyType_PT_CtrlPullLeftElbow` = `EPropertyType_PT_CtrlPullLeftElbow`
- `EPropertyType_PT_CtrlPullRightFingerBase` = `EPropertyType_PT_CtrlPullRightFingerBase`
- `EPropertyType_PT_CtrlPullRightElbow` = `EPropertyType_PT_CtrlPullRightElbow`
- `EPropertyType_PT_CtrlPullChestPullLeftHand` = `EPropertyType_PT_CtrlPullChestPullLeftHand`
- `EPropertyType_PT_CtrlPullChestPullRightHand` = `EPropertyType_PT_CtrlPullChestPullRightHand`
- `EPropertyType_PT_CtrlPullResistHipsPosition` = `EPropertyType_PT_CtrlPullResistHipsPosition`
- `EPropertyType_PT_CtrlPullEnforceGravity` = `EPropertyType_PT_CtrlPullEnforceGravity`
- `EPropertyType_PT_CtrlResistHipsOrientation` = `EPropertyType_PT_CtrlResistHipsOrientation`
- `EPropertyType_PT_CtrlResistChestPosition` = `EPropertyType_PT_CtrlResistChestPosition`
- `EPropertyType_PT_CtrlResistChestOrientation` = `EPropertyType_PT_CtrlResistChestOrientation`
- `EPropertyType_PT_CtrlResistLeftCollar` = `EPropertyType_PT_CtrlResistLeftCollar`
- `EPropertyType_PT_CtrlResistRightCollar` = `EPropertyType_PT_CtrlResistRightCollar`
- `EPropertyType_PT_CtrlResistLeftKnee` = `EPropertyType_PT_CtrlResistLeftKnee`
- `EPropertyType_PT_CtrlResistRightKnee` = `EPropertyType_PT_CtrlResistRightKnee`
- `EPropertyType_PT_CtrlResistLeftElbow` = `EPropertyType_PT_CtrlResistLeftElbow`
- `EPropertyType_PT_CtrlResistRightElbow` = `EPropertyType_PT_CtrlResistRightElbow`
- `EPropertyType_PT_HipsTOffsetX` = `EPropertyType_PT_HipsTOffsetX`
- `EPropertyType_PT_HipsTOffsetY` = `EPropertyType_PT_HipsTOffsetY`
- `EPropertyType_PT_ChestTOffsetX` = `EPropertyType_PT_ChestTOffsetX`
- `EPropertyType_PT_ChestTOffsetY` = `EPropertyType_PT_ChestTOffsetY`
- `EPropertyType_PT_ChestTOffsetZ` = `EPropertyType_PT_ChestTOffsetZ`
- `EPropertyType_PT_Quantity` = `EPropertyType_PT_Quantity`

### EQuaternionOrder

- `EQuaternionOrder_XYZW` = `EQuaternionOrder_XYZW`
- `EQuaternionOrder_WXYZ` = `EQuaternionOrder_WXYZ`

### EReduceBonePose

- `EReduceBonePose__None` = `EReduceBonePose__None`
- `EReduceBonePose_TPose` = `EReduceBonePose_TPose`
- `EReduceBonePose_Default` = `EReduceBonePose_Default`
- `EReduceBonePose_Current` = `EReduceBonePose_Current`
- `EReduceBonePose_Custom` = `EReduceBonePose_Custom`

### EReplaceMeshOption

- `EReplaceMeshOption_YUp` = `EReplaceMeshOption_YUp`
- `EReplaceMeshOption_ZUp` = `EReplaceMeshOption_ZUp`

### EResolutionType

- `EResolutionType_Large` = `EResolutionType_Large`
- `EResolutionType_Original` = `EResolutionType_Original`
- `EResolutionType_Small` = `EResolutionType_Small`

### ERotationType

- `ERotationType_Euler` = `ERotationType_Euler`
- `ERotationType_Quaternion` = `ERotationType_Quaternion`

### ERotationUnit

- `ERotationUnit_Radians` = `ERotationUnit_Radians`
- `ERotationUnit_Degrees` = `ERotationUnit_Degrees`

### ESaveFacialAnimationOption

- `ESaveFacialAnimationOption__None` = `ESaveFacialAnimationOption__None`
- `ESaveFacialAnimationOption_Expression` = `ESaveFacialAnimationOption_Expression`
- `ESaveFacialAnimationOption_Viseme` = `ESaveFacialAnimationOption_Viseme`
- `ESaveFacialAnimationOption_VisemeRawData` = `ESaveFacialAnimationOption_VisemeRawData`
- `ESaveFacialAnimationOption_All` = `ESaveFacialAnimationOption_All`

### ESaveFileType

- `ESaveFileType_Project` = `ESaveFileType_Project`
- `ESaveFileType_Character` = `ESaveFileType_Character`
- `ESaveFileType_Upper` = `ESaveFileType_Upper`
- `ESaveFileType_Lower` = `ESaveFileType_Lower`
- `ESaveFileType_Gloves` = `ESaveFileType_Gloves`
- `ESaveFileType_Shoes` = `ESaveFileType_Shoes`
- `ESaveFileType_Accessory` = `ESaveFileType_Accessory`
- `ESaveFileType_Motion` = `ESaveFileType_Motion`
- `ESaveFileType_Prop` = `ESaveFileType_Prop`
- `ESaveFileType_Talk` = `ESaveFileType_Talk`
- `ESaveFileType_MotionPlus` = `ESaveFileType_MotionPlus`
- `ESaveFileType_AvatarPart` = `ESaveFileType_AvatarPart`
- `ESaveFileType_AvatarPresetAll` = `ESaveFileType_AvatarPresetAll`
- `ESaveFileType_FaceHairElement` = `ESaveFileType_FaceHairElement`
- `ESaveFileType_AvatarPresetFacialProfile` = `ESaveFileType_AvatarPresetFacialProfile`
- `ESaveFileType_EyelashElement` = `ESaveFileType_EyelashElement`

### ESaveMotionClipOption

- `ESaveMotionClipOption__None` = `ESaveMotionClipOption__None`
- `ESaveMotionClipOption_WithLayerKey` = `ESaveMotionClipOption_WithLayerKey`
- `ESaveMotionClipOption_FkMotionOnly` = `ESaveMotionClipOption_FkMotionOnly`
- `ESaveMotionClipOption_AllBone` = `ESaveMotionClipOption_AllBone`
- `ESaveMotionClipOption_ExcludeTransformData` = `ESaveMotionClipOption_ExcludeTransformData`

### ESaveMotionPlusOption

- `ESaveMotionPlusOption__None` = `ESaveMotionPlusOption__None`
- `ESaveMotionPlusOption_Avatar_Motion` = `ESaveMotionPlusOption_Avatar_Motion`
- `ESaveMotionPlusOption_Avatar_Spring` = `ESaveMotionPlusOption_Avatar_Spring`
- `ESaveMotionPlusOption_Avatar_Visible` = `ESaveMotionPlusOption_Avatar_Visible`
- `ESaveMotionPlusOption_Avatar_Sound` = `ESaveMotionPlusOption_Avatar_Sound`
- `ESaveMotionPlusOption_Avatar_Talk` = `ESaveMotionPlusOption_Avatar_Talk`
- `ESaveMotionPlusOption_Avatar_Morph` = `ESaveMotionPlusOption_Avatar_Morph`
- `ESaveMotionPlusOption_Avatar_Material` = `ESaveMotionPlusOption_Avatar_Material`
- `ESaveMotionPlusOption_AllAvatar` = `ESaveMotionPlusOption_AllAvatar`

### ESetCategory

- `ESetCategory_Body` = `ESetCategory_Body`
- `ESetCategory_Head` = `ESetCategory_Head`
- `ESetCategory_Eyes` = `ESetCategory_Eyes`
- `ESetCategory_Teeth` = `ESetCategory_Teeth`
- `ESetCategory_Eyelash` = `ESetCategory_Eyelash`
- `ESetCategory_UpperEyelash` = `ESetCategory_UpperEyelash`
- `ESetCategory_LowerEyelash` = `ESetCategory_LowerEyelash`
- `ESetCategory_Nail` = `ESetCategory_Nail`

### ETagType

- `ETagType_Developer` = `ETagType_Developer`
- `ETagType_User` = `ETagType_User`

### ETangentType

- `ETangentType_Beizier` = `ETangentType_Beizier`
- `ETangentType_Linear` = `ETangentType_Linear`
- `ETangentType_Step` = `ETangentType_Step`
- `ETangentType_EaseIn` = `ETangentType_EaseIn`
- `ETangentType_EaseOut` = `ETangentType_EaseOut`
- `ETangentType_EaseInOut` = `ETangentType_EaseInOut`
- `ETangentType_EaseOutIn` = `ETangentType_EaseOutIn`
- `ETangentType_Fast` = `ETangentType_Fast`
- `ETangentType_Slow` = `ETangentType_Slow`
- `ETangentType_Auto` = `ETangentType_Auto`
- `ETangentType_Smooth` = `ETangentType_Smooth`

### ETemplateRootFolder

- `ETemplateRootFolder_Project` = `ETemplateRootFolder_Project`
- `ETemplateRootFolder_Character` = `ETemplateRootFolder_Character`
- `ETemplateRootFolder_AvatarControl` = `ETemplateRootFolder_AvatarControl`
- `ETemplateRootFolder_FacialProfile` = `ETemplateRootFolder_FacialProfile`
- `ETemplateRootFolder_Teeth` = `ETemplateRootFolder_Teeth`
- `ETemplateRootFolder_Eye` = `ETemplateRootFolder_Eye`
- `ETemplateRootFolder_Face` = `ETemplateRootFolder_Face`
- `ETemplateRootFolder_RLHead` = `ETemplateRootFolder_RLHead`
- `ETemplateRootFolder_Oral` = `ETemplateRootFolder_Oral`
- `ETemplateRootFolder_Upper` = `ETemplateRootFolder_Upper`
- `ETemplateRootFolder_Lower` = `ETemplateRootFolder_Lower`
- `ETemplateRootFolder_FullBodyMorphSkin` = `ETemplateRootFolder_FullBodyMorphSkin`
- `ETemplateRootFolder_HeadMorphSkin` = `ETemplateRootFolder_HeadMorphSkin`
- `ETemplateRootFolder_FullBodyMorph` = `ETemplateRootFolder_FullBodyMorph`
- `ETemplateRootFolder_BodyMorph` = `ETemplateRootFolder_BodyMorph`
- `ETemplateRootFolder_HeadMorph` = `ETemplateRootFolder_HeadMorph`
- `ETemplateRootFolder_AvatarPresetEyelash` = `ETemplateRootFolder_AvatarPresetEyelash`
- `ETemplateRootFolder_Nail` = `ETemplateRootFolder_Nail`
- `ETemplateRootFolder_MixerPreset_Leg` = `ETemplateRootFolder_MixerPreset_Leg`
- `ETemplateRootFolder_MixerPreset_Arm` = `ETemplateRootFolder_MixerPreset_Arm`
- `ETemplateRootFolder_MixerPreset_BodyAdjust` = `ETemplateRootFolder_MixerPreset_BodyAdjust`
- `ETemplateRootFolder_MixerPreset_HeadAdjust` = `ETemplateRootFolder_MixerPreset_HeadAdjust`
- `ETemplateRootFolder_MixerPreset_Chin` = `ETemplateRootFolder_MixerPreset_Chin`
- `ETemplateRootFolder_MixerPreset_Brow` = `ETemplateRootFolder_MixerPreset_Brow`
- `ETemplateRootFolder_MixerPreset_Ear` = `ETemplateRootFolder_MixerPreset_Ear`
- `ETemplateRootFolder_MixerPreset_Mouth` = `ETemplateRootFolder_MixerPreset_Mouth`
- `ETemplateRootFolder_MixerPreset_Nose` = `ETemplateRootFolder_MixerPreset_Nose`
- `ETemplateRootFolder_MixerPreset_Eye` = `ETemplateRootFolder_MixerPreset_Eye`
- `ETemplateRootFolder_MixerPreset_Body` = `ETemplateRootFolder_MixerPreset_Body`
- `ETemplateRootFolder_MixerPreset_Head` = `ETemplateRootFolder_MixerPreset_Head`
- `ETemplateRootFolder_MixerPreset_FullCharacter` = `ETemplateRootFolder_MixerPreset_FullCharacter`
- `ETemplateRootFolder_MixerPreset_Torso` = `ETemplateRootFolder_MixerPreset_Torso`
- `ETemplateRootFolder_MixerPresetSet` = `ETemplateRootFolder_MixerPresetSet`
- `ETemplateRootFolder_MixerPresetPackage` = `ETemplateRootFolder_MixerPresetPackage`
- `ETemplateRootFolder_Overall` = `ETemplateRootFolder_Overall`
- `ETemplateRootFolder_Skin_Head` = `ETemplateRootFolder_Skin_Head`
- `ETemplateRootFolder_FullSkin` = `ETemplateRootFolder_FullSkin`
- `ETemplateRootFolder_SkinBase` = `ETemplateRootFolder_SkinBase`
- `ETemplateRootFolder_NormalEffects` = `ETemplateRootFolder_NormalEffects`
- `ETemplateRootFolder_SkinDetails` = `ETemplateRootFolder_SkinDetails`
- `ETemplateRootFolder_Blemish` = `ETemplateRootFolder_Blemish`
- `ETemplateRootFolder_Acquired` = `ETemplateRootFolder_Acquired`
- `ETemplateRootFolder_BodyHair` = `ETemplateRootFolder_BodyHair`
- `ETemplateRootFolder_Nails` = `ETemplateRootFolder_Nails`
- `ETemplateRootFolder_SkinGenTools` = `ETemplateRootFolder_SkinGenTools`
- `ETemplateRootFolder_WrinkleMasks` = `ETemplateRootFolder_WrinkleMasks`
- `ETemplateRootFolder_FullMakeup` = `ETemplateRootFolder_FullMakeup`
- `ETemplateRootFolder_FoundationMakeup` = `ETemplateRootFolder_FoundationMakeup`
- `ETemplateRootFolder_EyeMakeup` = `ETemplateRootFolder_EyeMakeup`
- `ETemplateRootFolder_MakeupEyelash` = `ETemplateRootFolder_MakeupEyelash`
- `ETemplateRootFolder_LipMakeup` = `ETemplateRootFolder_LipMakeup`
- `ETemplateRootFolder_Eyebrow` = `ETemplateRootFolder_Eyebrow`
- `ETemplateRootFolder_Miscellaneous` = `ETemplateRootFolder_Miscellaneous`
- `ETemplateRootFolder_MakeupSkinGenTools` = `ETemplateRootFolder_MakeupSkinGenTools`
- `ETemplateRootFolder_Style` = `ETemplateRootFolder_Style`
- `ETemplateRootFolder_Group` = `ETemplateRootFolder_Group`
- `ETemplateRootFolder_Element` = `ETemplateRootFolder_Element`
- `ETemplateRootFolder_Underwear` = `ETemplateRootFolder_Underwear`
- `ETemplateRootFolder_Shirts` = `ETemplateRootFolder_Shirts`
- `ETemplateRootFolder_Pants` = `ETemplateRootFolder_Pants`
- `ETemplateRootFolder_Skirts` = `ETemplateRootFolder_Skirts`
- `ETemplateRootFolder_Coats` = `ETemplateRootFolder_Coats`
- `ETemplateRootFolder_FullBody` = `ETemplateRootFolder_FullBody`
- `ETemplateRootFolder_ClothOthers` = `ETemplateRootFolder_ClothOthers`
- `ETemplateRootFolder_Gloves` = `ETemplateRootFolder_Gloves`
- `ETemplateRootFolder_Shoes` = `ETemplateRootFolder_Shoes`
- `ETemplateRootFolder_Head` = `ETemplateRootFolder_Head`
- `ETemplateRootFolder_Torso` = `ETemplateRootFolder_Torso`
- `ETemplateRootFolder_Arm` = `ETemplateRootFolder_Arm`
- `ETemplateRootFolder_Leg` = `ETemplateRootFolder_Leg`
- `ETemplateRootFolder_AccessoryOthers` = `ETemplateRootFolder_AccessoryOthers`
- `ETemplateRootFolder_MotionPlus` = `ETemplateRootFolder_MotionPlus`
- `ETemplateRootFolder_Motion` = `ETemplateRootFolder_Motion`
- `ETemplateRootFolder_Expression` = `ETemplateRootFolder_Expression`
- `ETemplateRootFolder_Gesture` = `ETemplateRootFolder_Gesture`
- `ETemplateRootFolder_Pose` = `ETemplateRootFolder_Pose`
- `ETemplateRootFolder_MotionDirector` = `ETemplateRootFolder_MotionDirector`
- `ETemplateRootFolder_Persona` = `ETemplateRootFolder_Persona`
- `ETemplateRootFolder_iAnimation` = `ETemplateRootFolder_iAnimation`
- `ETemplateRootFolder_LightRoom` = `ETemplateRootFolder_LightRoom`
- `ETemplateRootFolder_Atmosphere` = `ETemplateRootFolder_Atmosphere`
- `ETemplateRootFolder_Camera` = `ETemplateRootFolder_Camera`
- `ETemplateRootFolder_Light` = `ETemplateRootFolder_Light`
- `ETemplateRootFolder_PostEffect` = `ETemplateRootFolder_PostEffect`
- `ETemplateRootFolder_ImageLayer` = `ETemplateRootFolder_ImageLayer`
- `ETemplateRootFolder_Scene3D` = `ETemplateRootFolder_Scene3D`
- `ETemplateRootFolder_Material` = `ETemplateRootFolder_Material`
- `ETemplateRootFolder_MaterialPlus` = `ETemplateRootFolder_MaterialPlus`
- `ETemplateRootFolder_Background2D` = `ETemplateRootFolder_Background2D`
- `ETemplateRootFolder_Texture` = `ETemplateRootFolder_Texture`
- `ETemplateRootFolder_Diffuse` = `ETemplateRootFolder_Diffuse`
- `ETemplateRootFolder_Opacity` = `ETemplateRootFolder_Opacity`
- `ETemplateRootFolder_Bump` = `ETemplateRootFolder_Bump`
- `ETemplateRootFolder_Glow` = `ETemplateRootFolder_Glow`
- `ETemplateRootFolder_Reflection` = `ETemplateRootFolder_Reflection`
- `ETemplateRootFolder_Specular` = `ETemplateRootFolder_Specular`
- `ETemplateRootFolder_Blend` = `ETemplateRootFolder_Blend`
- `ETemplateRootFolder_Displacement` = `ETemplateRootFolder_Displacement`
- `ETemplateRootFolder_IBL` = `ETemplateRootFolder_IBL`
- `ETemplateRootFolder_WeightMap` = `ETemplateRootFolder_WeightMap`
- `ETemplateRootFolder_Metallic` = `ETemplateRootFolder_Metallic`
- `ETemplateRootFolder_Roughness` = `ETemplateRootFolder_Roughness`
- `ETemplateRootFolder_AO` = `ETemplateRootFolder_AO`
- `ETemplateRootFolder_LensFlare` = `ETemplateRootFolder_LensFlare`
- `ETemplateRootFolder_IES` = `ETemplateRootFolder_IES`
- `ETemplateRootFolder_IMDL` = `ETemplateRootFolder_IMDL`
- `ETemplateRootFolder_Tree` = `ETemplateRootFolder_Tree`
- `ETemplateRootFolder_Grass` = `ETemplateRootFolder_Grass`
- `ETemplateRootFolder_Particle` = `ETemplateRootFolder_Particle`
- `ETemplateRootFolder_Terrain` = `ETemplateRootFolder_Terrain`
- `ETemplateRootFolder_Water` = `ETemplateRootFolder_Water`
- `ETemplateRootFolder_Sky` = `ETemplateRootFolder_Sky`
- `ETemplateRootFolder_MotionPath` = `ETemplateRootFolder_MotionPath`
- `ETemplateRootFolder_Props` = `ETemplateRootFolder_Props`
- `ETemplateRootFolder_Building` = `ETemplateRootFolder_Building`
- `ETemplateRootFolder_Sound` = `ETemplateRootFolder_Sound`
- `ETemplateRootFolder_Video` = `ETemplateRootFolder_Video`
- `ETemplateRootFolder_Digital_Human_Shader_Resource` = `ETemplateRootFolder_Digital_Human_Shader_Resource`
- `ETemplateRootFolder_SSS_Shader_Resource` = `ETemplateRootFolder_SSS_Shader_Resource`
- `ETemplateRootFolder_Spring` = `ETemplateRootFolder_Spring`
- `ETemplateRootFolder_LuaScript` = `ETemplateRootFolder_LuaScript`
- `ETemplateRootFolder_Fashion_Gen_Resource` = `ETemplateRootFolder_Fashion_Gen_Resource`
- `ETemplateRootFolder_MotionPuppet` = `ETemplateRootFolder_MotionPuppet`
- `ETemplateRootFolder_FacePuppet` = `ETemplateRootFolder_FacePuppet`
- `ETemplateRootFolder_SubstancePreset` = `ETemplateRootFolder_SubstancePreset`
- `ETemplateRootFolder_ContentPatch` = `ETemplateRootFolder_ContentPatch`
- `ETemplateRootFolder_SpringProfile` = `ETemplateRootFolder_SpringProfile`
- `ETemplateRootFolder_Dictionary` = `ETemplateRootFolder_Dictionary`
- `ETemplateRootFolder_Quantity` = `ETemplateRootFolder_Quantity`
- `ETemplateRootFolder_Invalid` = `ETemplateRootFolder_Invalid`

### ETimecodeSource

- `ETimecodeSource_AP` = `ETimecodeSource_AP`
- `ETimecodeSource_MotionLive` = `ETimecodeSource_MotionLive`

### ETransitionType

- `ETransitionType_Invalid` = `ETransitionType_Invalid`
- `ETransitionType__None` = `ETransitionType__None`
- `ETransitionType_Linear` = `ETransitionType_Linear`
- `ETransitionType_Step` = `ETransitionType_Step`
- `ETransitionType_Ease_Out` = `ETransitionType_Ease_Out`
- `ETransitionType_Ease_In` = `ETransitionType_Ease_In`
- `ETransitionType_Ease_Out_In` = `ETransitionType_Ease_Out_In`
- `ETransitionType_Ease_In_Out` = `ETransitionType_Ease_In_Out`
- `ETransitionType_Ease_In_Sine` = `ETransitionType_Ease_In_Sine`
- `ETransitionType_Ease_Out_Sine` = `ETransitionType_Ease_Out_Sine`
- `ETransitionType_Ease_In_Out_Sine` = `ETransitionType_Ease_In_Out_Sine`
- `ETransitionType_Ease_In_Quad` = `ETransitionType_Ease_In_Quad`
- `ETransitionType_Ease_Out_Quad` = `ETransitionType_Ease_Out_Quad`
- `ETransitionType_Ease_In_Out_Quad` = `ETransitionType_Ease_In_Out_Quad`
- `ETransitionType_Ease_In_Cubic` = `ETransitionType_Ease_In_Cubic`
- `ETransitionType_Ease_Out_Cubic` = `ETransitionType_Ease_Out_Cubic`
- `ETransitionType_Ease_In_Out_Cubic` = `ETransitionType_Ease_In_Out_Cubic`
- `ETransitionType_Ease_In_Quart` = `ETransitionType_Ease_In_Quart`
- `ETransitionType_Ease_Out_Quart` = `ETransitionType_Ease_Out_Quart`
- `ETransitionType_Ease_In_Out_Quart` = `ETransitionType_Ease_In_Out_Quart`
- `ETransitionType_Ease_In_Quint` = `ETransitionType_Ease_In_Quint`
- `ETransitionType_Ease_Out_Quint` = `ETransitionType_Ease_Out_Quint`
- `ETransitionType_Ease_In_Out_Quint` = `ETransitionType_Ease_In_Out_Quint`
- `ETransitionType_Ease_In_Expo` = `ETransitionType_Ease_In_Expo`
- `ETransitionType_Ease_Out_Expo` = `ETransitionType_Ease_Out_Expo`
- `ETransitionType_Ease_In_Out_Expo` = `ETransitionType_Ease_In_Out_Expo`
- `ETransitionType_Ease_In_Circ` = `ETransitionType_Ease_In_Circ`
- `ETransitionType_Ease_Out_Circ` = `ETransitionType_Ease_Out_Circ`
- `ETransitionType_Ease_In_Out_Circ` = `ETransitionType_Ease_In_Out_Circ`
- `ETransitionType_Ease_In_Back` = `ETransitionType_Ease_In_Back`
- `ETransitionType_Ease_Out_Back` = `ETransitionType_Ease_Out_Back`
- `ETransitionType_Ease_In_Out_Back` = `ETransitionType_Ease_In_Out_Back`
- `ETransitionType_Ease_In_Elastic` = `ETransitionType_Ease_In_Elastic`
- `ETransitionType_Ease_Out_Elastic` = `ETransitionType_Ease_Out_Elastic`
- `ETransitionType_Ease_In_Out_Elastic` = `ETransitionType_Ease_In_Out_Elastic`
- `ETransitionType_Ease_In_Bounce` = `ETransitionType_Ease_In_Bounce`
- `ETransitionType_Ease_Out_Bounce` = `ETransitionType_Ease_Out_Bounce`
- `ETransitionType_Ease_In_Out_Bounce` = `ETransitionType_Ease_In_Out_Bounce`
- `ETransitionType_Last` = `ETransitionType_Last`
- `ETransitionType_Count` = `ETransitionType_Count`

### EUnrealBoneStructure

- `EUnrealBoneStructure__None` = `EUnrealBoneStructure__None`
- `EUnrealBoneStructure_UE4_BoneStructure` = `EUnrealBoneStructure_UE4_BoneStructure`
- `EUnrealBoneStructure_UE5_BoneStructure` = `EUnrealBoneStructure_UE5_BoneStructure`

### EVisemeID

- `EVisemeID_NONE` = `EVisemeID_NONE`
- `EVisemeID_EE` = `EVisemeID_EE`
- `EVisemeID_ER` = `EVisemeID_ER`
- `EVisemeID_IH` = `EVisemeID_IH`
- `EVisemeID_AH` = `EVisemeID_AH`
- `EVisemeID_OH` = `EVisemeID_OH`
- `EVisemeID_W_OO` = `EVisemeID_W_OO`
- `EVisemeID_S_Z` = `EVisemeID_S_Z`
- `EVisemeID_CH_J` = `EVisemeID_CH_J`
- `EVisemeID_F_V` = `EVisemeID_F_V`
- `EVisemeID_TH` = `EVisemeID_TH`
- `EVisemeID_T_L_D_N` = `EVisemeID_T_L_D_N`
- `EVisemeID_B_M_P` = `EVisemeID_B_M_P`
- `EVisemeID_K_G_H_NG` = `EVisemeID_K_G_H_NG`
- `EVisemeID_AE` = `EVisemeID_AE`
- `EVisemeID_R` = `EVisemeID_R`

### EWrinkleFacePart

- `EWrinkleFacePart_Blink` = `EWrinkleFacePart_Blink`
- `EWrinkleFacePart_BrowDrop` = `EWrinkleFacePart_BrowDrop`
- `EWrinkleFacePart_BrowRaise` = `EWrinkleFacePart_BrowRaise`
- `EWrinkleFacePart_Cheek` = `EWrinkleFacePart_Cheek`
- `EWrinkleFacePart_Chin` = `EWrinkleFacePart_Chin`
- `EWrinkleFacePart_Jaw` = `EWrinkleFacePart_Jaw`
- `EWrinkleFacePart_MouthStretch` = `EWrinkleFacePart_MouthStretch`
- `EWrinkleFacePart_Neck` = `EWrinkleFacePart_Neck`
- `EWrinkleFacePart_Nose` = `EWrinkleFacePart_Nose`
- `EWrinkleFacePart_PurseLips` = `EWrinkleFacePart_PurseLips`
- `EWrinkleFacePart_Smile` = `EWrinkleFacePart_Smile`
- `EWrinkleFacePart_Squint` = `EWrinkleFacePart_Squint`
- `EWrinkleFacePart_Sneer` = `EWrinkleFacePart_Sneer`

### EWrinkleLayerType

- `EWrinkleLayerType_AoCrease` = `EWrinkleLayerType_AoCrease`
- `EWrinkleLayerType_Redness` = `EWrinkleLayerType_Redness`
- `EWrinkleLayerType_NormalStrength` = `EWrinkleLayerType_NormalStrength`

### EWrinkleTextureChannel

- `EWrinkleTextureChannel_Diffuse1` = `EWrinkleTextureChannel_Diffuse1`
- `EWrinkleTextureChannel_Diffuse2` = `EWrinkleTextureChannel_Diffuse2`
- `EWrinkleTextureChannel_Diffuse3` = `EWrinkleTextureChannel_Diffuse3`
- `EWrinkleTextureChannel_Normal1` = `EWrinkleTextureChannel_Normal1`
- `EWrinkleTextureChannel_Normal2` = `EWrinkleTextureChannel_Normal2`
- `EWrinkleTextureChannel_Normal3` = `EWrinkleTextureChannel_Normal3`
- `EWrinkleTextureChannel_Roughness1` = `EWrinkleTextureChannel_Roughness1`
- `EWrinkleTextureChannel_Roughness2` = `EWrinkleTextureChannel_Roughness2`
- `EWrinkleTextureChannel_Roughness3` = `EWrinkleTextureChannel_Roughness3`
- `EWrinkleTextureChannel_AoCrease1` = `EWrinkleTextureChannel_AoCrease1`
- `EWrinkleTextureChannel_AoCrease2` = `EWrinkleTextureChannel_AoCrease2`
- `EWrinkleTextureChannel_AoCrease3` = `EWrinkleTextureChannel_AoCrease3`

---

## Constants (Non-Enum)

- `SHARED_PTR_DISOWN` = `SHARED_PTR_DISOWN`
- `InvalidRole` = `InvalidRole`
- `AcceptRole` = `AcceptRole`
- `RejectRole` = `RejectRole`
- `DestructiveRole` = `DestructiveRole`
- `ActionRole` = `ActionRole`
- `HelpRole` = `HelpRole`
- `YesRole` = `YesRole`
- `NoRole` = `NoRole`
- `ResetRole` = `ResetRole`
- `ApplyRole` = `ApplyRole`
- `NRoles` = `NRoles`
- `IMAGE` = `IMAGE`
- `VIDEO` = `VIDEO`
- `IMAGE_SEQUENCE` = `IMAGE_SEQUENCE`
- `AUDIO` = `AUDIO`
- `cvar` = `cvar`
- `Order_XYZ` = `Order_XYZ`
- `Order_ZYX` = `Order_ZYX`
- `Order_XZY` = `Order_XZY`
- `Order_YZX` = `Order_YZX`
- `Order_YXZ` = `Order_YXZ`
- `Order_ZXY` = `Order_ZXY`
- `MATRIX4_T_X` = `MATRIX4_T_X`
- `MATRIX4_T_Y` = `MATRIX4_T_Y`
- `MATRIX4_T_Z` = `MATRIX4_T_Z`
- `CUSTOM_ARRAY_DEFAULT_SIZE` = `CUSTOM_ARRAY_DEFAULT_SIZE`
- `CUSTOM_ARRAY_PATCH_SIZE` = `CUSTOM_ARRAY_PATCH_SIZE`
- `VT_Invalid` = `VT_Invalid`
- `VT_Integer` = `VT_Integer`
- `VT_Float` = `VT_Float`
- `VT_UTF8String` = `VT_UTF8String`
- `VT_Character` = `VT_Character`
- `VT_Boolean` = `VT_Boolean`
- `VT_Handle` = `VT_Handle`
- `VT_Map` = `VT_Map`
- `VT_Double` = `VT_Double`
- `VT_WString` = `VT_WString`
- `VT_Integer64` = `VT_Integer64`
- `RL_MAX_PATH` = `RL_MAX_PATH`
- `CTRLKEY_LAYER` = `CTRLKEY_LAYER`
- `CTRLKEY_TRANSFORM` = `CTRLKEY_TRANSFORM`
- `CTRLKEY_PATHPOSITION` = `CTRLKEY_PATHPOSITION`
- `CTRLKEY_PATHOFFSET` = `CTRLKEY_PATHOFFSET`
- `CTRLKEY_LOOKATWEIGHT_HEAD` = `CTRLKEY_LOOKATWEIGHT_HEAD`
- `CTRLKEY_LOOKATWEIGHT_BODY` = `CTRLKEY_LOOKATWEIGHT_BODY`
- `CTRLKEY_LOOKATOFFSET` = `CTRLKEY_LOOKATOFFSET`
- `GOZ_SPLIT_INI` = `GOZ_SPLIT_INI`
- `EExportFbxOptions2__None` = `EExportFbxOptions2__None`
- `EExportFbxOptions2_XUp` = `EExportFbxOptions2_XUp`
- `EExportFbxOptions2_YUp` = `EExportFbxOptions2_YUp`
- `EExportFbxOptions2_UnrealEngine4BoneAxis` = `EExportFbxOptions2_UnrealEngine4BoneAxis`
- `EExportFbxOptions2_SourceUpAxisSameAsTarget` = `EExportFbxOptions2_SourceUpAxisSameAsTarget`
- `EExportFbxOptions2_RenameDuplicateBoneName` = `EExportFbxOptions2_RenameDuplicateBoneName`
- `EExportFbxOptions2_RenameDuplicateMaterialName` = `EExportFbxOptions2_RenameDuplicateMaterialName`
- `EExportFbxOptions2_RenameDuplicateMorphName` = `EExportFbxOptions2_RenameDuplicateMorphName`
- `EExportFbxOptions2_RenameTransparencyWithPostFix` = `EExportFbxOptions2_RenameTransparencyWithPostFix`
- `EExportFbxOptions2_RenameBoneRootToGameType` = `EExportFbxOptions2_RenameBoneRootToGameType`
- `EExportFbxOptions2_RenameBoneToLowerCase` = `EExportFbxOptions2_RenameBoneToLowerCase`
- `EExportFbxOptions2_RenameBoneOnStd` = `EExportFbxOptions2_RenameBoneOnStd`
- `EExportFbxOptions2_IsNotRenamePivot` = `EExportFbxOptions2_IsNotRenamePivot`
- `EExportFbxOptions2_RenameGameBodyMesh` = `EExportFbxOptions2_RenameGameBodyMesh`
- `EExportFbxOptions2_RenameMorphInvalidCharacter` = `EExportFbxOptions2_RenameMorphInvalidCharacter`
- `EExportFbxOptions2_ResetBoneScale` = `EExportFbxOptions2_ResetBoneScale`
- `EExportFbxOptions2_ResetSkinPose` = `EExportFbxOptions2_ResetSkinPose`
- `EExportFbxOptions2_ResetSelfillumination` = `EExportFbxOptions2_ResetSelfillumination`
- `EExportFbxOptions2_AsciiFormat` = `EExportFbxOptions2_AsciiFormat`
- `EExportFbxOptions2_PrefixAndPostfix` = `EExportFbxOptions2_PrefixAndPostfix`
- `EExportFbxOptions2_IsNotCloneObject` = `EExportFbxOptions2_IsNotCloneObject`
- `EExportFbxOptions2_BoneNubAttribute` = `EExportFbxOptions2_BoneNubAttribute`
- `EExportFbxOptions2_ExtraWordForUnityAndUnreal` = `EExportFbxOptions2_ExtraWordForUnityAndUnreal`
- `EExportFbxOptions2_BakeMouthOpenMotionToMesh` = `EExportFbxOptions2_BakeMouthOpenMotionToMesh`
- `EExportFbxOptions2_AvoidTextureIntoIndexedMode` = `EExportFbxOptions2_AvoidTextureIntoIndexedMode`
- `EExportFbxOptions2_UnrealIkBone` = `EExportFbxOptions2_UnrealIkBone`
- `EExportFbxOptions2_UnityPreset` = `EExportFbxOptions2_UnityPreset`
- `EExportFbxOptions2_UnrealPreset` = `EExportFbxOptions2_UnrealPreset`
- `EExportFbxOptions2_InstaLodPreset` = `EExportFbxOptions2_InstaLodPreset`
- `EExportFbxOptions3__None` = `EExportFbxOptions3__None`
- `EExportFbxOptions3_ExportJson` = `EExportFbxOptions3_ExportJson`
- `EExportFbxOptions3_RestoreStandardSeriesBoneAxis` = `EExportFbxOptions3_RestoreStandardSeriesBoneAxis`
- `EExportFbxOptions3_TraditionalUv` = `EExportFbxOptions3_TraditionalUv`
- `EExportFbxOptions3_ExportVertexColor` = `EExportFbxOptions3_ExportVertexColor`
- `EExport3DFileOption__None` = `EExport3DFileOption__None`
- `EExport3DFileOption_AxisYUp` = `EExport3DFileOption_AxisYUp`
- `EExport3DFileOption_GenerateMeshGroupIni` = `EExport3DFileOption_GenerateMeshGroupIni`
- `EExport3DFileOption_GenerateDrmProtectedFile` = `EExport3DFileOption_GenerateDrmProtectedFile`
- `EExport3DFileOption_BodyPart` = `EExport3DFileOption_BodyPart`
- `EExport3DFileOption_EyePart` = `EExport3DFileOption_EyePart`
- `EExport3DFileOption_TeethPart` = `EExport3DFileOption_TeethPart`
- `EExport3DFileOption_AllClothes` = `EExport3DFileOption_AllClothes`
- `EExport3DFileOption_ResetToBindPose` = `EExport3DFileOption_ResetToBindPose`
- `EExport3DFileOption_ExportMaterial` = `EExport3DFileOption_ExportMaterial`
- `EExport3DFileOption_AbortExportIfMaterialNamesDuplicate` = `EExport3DFileOption_AbortExportIfMaterialNamesDuplicate`
- `EExport3DFileOption_RemoveHiddenMesh` = `EExport3DFileOption_RemoveHiddenMesh`
- `EExport3DFileOption_ExportFacialAnimation` = `EExport3DFileOption_ExportFacialAnimation`
- `EExport3DFileOption_TextureMapsAreShaderGenerated` = `EExport3DFileOption_TextureMapsAreShaderGenerated`
- `EExport3DFileOption_BakeSubdivision` = `EExport3DFileOption_BakeSubdivision`
- `EExport3DFileOption_ExportExtraMaterial` = `EExport3DFileOption_ExportExtraMaterial`
- `EExport3DFileOption_FullBodyPart` = `EExport3DFileOption_FullBodyPart`
- `kPostEffect` = `cvar.kPostEffect`
- `ReachKeyType_Target` = `ReachKeyType_Target`
- `ReachKeyType_Lock` = `ReachKeyType_Lock`
- `ReachKeyType_Release` = `ReachKeyType_Release`
- `REMeshType_Wall` = `REMeshType_Wall`
- `REMeshType_Ground` = `REMeshType_Ground`
- `REMeshType_Pillar` = `REMeshType_Pillar`
- `REShape_Square` = `REShape_Square`
- `REShape_Hypotenuse` = `REShape_Hypotenuse`
- `REAxis_NONE` = `REAxis_NONE`
- `REAxis_X` = `REAxis_X`
- `REAxis_Y` = `REAxis_Y`
- `REAxis_Z` = `REAxis_Z`
- `REAxis_NEGATIVE_X` = `REAxis_NEGATIVE_X`
- `REAxis_NEGATIVE_Y` = `REAxis_NEGATIVE_Y`
- `REAxis_NEGATIVE_Z` = `REAxis_NEGATIVE_Z`
- `REAxis_XY` = `REAxis_XY`
- `REAxis_YZ` = `REAxis_YZ`
- `REAxis_XZ` = `REAxis_XZ`
- `REAxis_XYZ` = `REAxis_XYZ`
- `REAxis_Quantity` = `REAxis_Quantity`
- `REFloorType_FirstFloor` = `REFloorType_FirstFloor`
- `REFloorType_MiddleFloor` = `REFloorType_MiddleFloor`
- `REFloorType_TopFloor` = `REFloorType_TopFloor`
- `REPosition_Up` = `REPosition_Up`
- `REPosition_Left` = `REPosition_Left`
- `REPosition_Down` = `REPosition_Down`
- `REPosition_Right` = `REPosition_Right`
- `REPosition_SlashUp` = `REPosition_SlashUp`
- `REPosition_SlashDown` = `REPosition_SlashDown`
- `REPosition_BackslashUp` = `REPosition_BackslashUp`
- `REPosition_BackslashDown` = `REPosition_BackslashDown`
- `REPosition_TopLeftPillar` = `REPosition_TopLeftPillar`
- `REPosition_TopRightPillar` = `REPosition_TopRightPillar`
- `REPosition_BottomLeftPillar` = `REPosition_BottomLeftPillar`
- `REPosition_BottomRightPillar` = `REPosition_BottomRightPillar`
- `REPosition_Ground` = `REPosition_Ground`
- `REPosition_TopLeftGround` = `REPosition_TopLeftGround`
- `REPosition_TopRightGround` = `REPosition_TopRightGround`
- `REPosition_BottomLeftGround` = `REPosition_BottomLeftGround`
- `REPosition_BottomRightGround` = `REPosition_BottomRightGround`

---

## Classes

### Vector/Container Types

All vector types share identical interfaces (iterator, append, pop, size, etc.).

| Type | Description |
|------|-------------|
| `AccessoryVector` | Inherits from `object` |
| `AvatarPartVector` | Inherits from `object` |
| `AvatarVector` | Inherits from `object` |
| `BaseVector` | Inherits from `object` |
| `BoolVector` | Inherits from `object` |
| `BuildingObjectVector` | Inherits from `object` |
| `CameraVector` | Inherits from `object` |
| `ClothVector` | Inherits from `object` |
| `EMaterialTextureChannelVector` | Inherits from `object` |
| `ElementInfoVector` | Inherits from `object` |
| `ElementObjectVector` | Inherits from `object` |
| `FloatVector` | Inherits from `object` |
| `FloorObjectVector` | Inherits from `object` |
| `HairVector` | Inherits from `object` |
| `Int64Vector` | Inherits from `object` |
| `IntVector` | Inherits from `object` |
| `MDPropVector` | Inherits from `object` |
| `MaterialInfoVector` | Inherits from `object` |
| `Matrix4fVector` | Inherits from `object` |
| `MeshVector` | Inherits from `object` |
| `NodeVector` | Inherits from `object` |
| `ObjectVector` | Inherits from `object` |
| `PropVector` | Inherits from `object` |
| `RAttributePtrVector` | Inherits from `object` |
| `RExportGoZMeshOptionVector` | Inherits from `object` |
| `RHIKEffectorVector` | Inherits from `object` |
| `RInsertBoneInfoVector` | Inherits from `object` |
| `RMessageBoxButtonVector` | Inherits from `object` |
| `RReachKeyVector` | Inherits from `object` |
| `RVisemeKeyVector` | Inherits from `object` |
| `RWordDataVector` | Inherits from `object` |
| `SizetVector` | Inherits from `object` |
| `StdMaterialVector` | Inherits from `object` |
| `TimeVector` | Inherits from `object` |
| `UnitObjectVector` | Inherits from `object` |
| `Vector3fVector` | Inherits from `object` |
| `VectorOfFloatVector` | Inherits from `object` |
| `VectorOfWStringVector` | Inherits from `object` |
| `WStringVector` | Inherits from `object` |
| `WallInfoVector` | Inherits from `object` |
| `WallObjectVector` | Inherits from `object` |

**Common Vector Methods** (shared by all vector types above):

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__getslice__(self, i, j)`
- `__setslice__(self, *args)`
- `__delslice__(self, i, j)`
- `__delitem__(self, *args)`
- `__getitem__(self, *args)`
- `__setitem__(self, *args)`
- `pop(self)`
- `append(self, x)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `pop_back(self)`
- `erase(self, *args)`
- `__init__(self, *args)`
- `push_back(self, x)`
- `front(self)`
- `back(self)`
- `assign(self, n, x)`
- `resize(self, *args)`
- `insert(self, *args)`
- `reserve(self, n)`
- `capacity(self)`

### Core API Classes

#### FloatPair

**Methods:**

- `__init__(self, *args)`
- `__len__(self)`
- `__repr__(self)`
- `__getitem__(self, index)`
- `__setitem__(self, index, val)`

#### ImportExpressionOptions

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__getslice__(self, i, j)`
- `__setslice__(self, *args)`
- `__delslice__(self, i, j)`
- `__delitem__(self, *args)`
- `__getitem__(self, *args)`
- `__setitem__(self, *args)`
- `pop(self)`
- `append(self, x)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `pop_back(self)`
- `erase(self, *args)`
- `__init__(self, *args)`
- `push_back(self, x)`
- `front(self)`
- `back(self)`
- `assign(self, n, x)`
- `resize(self, *args)`
- `insert(self, *args)`
- `reserve(self, n)`
- `capacity(self)`

#### MaterialSettings

**Methods:**

- `__init__(self)`

#### PixelStreamCaptureFrame

**Methods:**

- `__init__(self)`

#### RApplication

**Methods:**

- `GetProductName()`
- `GetProductEdition()`
- `GetProductVersion()`
- `GetProductMajorVersion()`
- `GetProductMinorVersion()`
- `GetApiVersion()`
- `GetApiMajorVersion()`
- `GetApiMinorVersion()`
- `GetProgramPath()`
- `GetDefaultProjectPath()`
- `GetCurrentProjectPath()`
- `GetTemplateDataPath()`
- `GetCustomDataPath()`
- `GetDefaultContentFolder(eFolderType)`
- `GetContentFoldersInFolder(strFolder)`
- `GetContentFilesInFolder(strFolder)`
- `GetCustomContentFolder(eFolderType)`
- `GetContentId(strFilePath)`
- `__init__(self)`

#### RAttribute

**Methods:**

- `__init__(self, *args)`
- `SetName(self, strName)`
- `GetName(self)`
- `SetType(self, eType)`
- `GetType(self)`
- `SetFlag(self, eFlag)`
- `GetFlag(self)`

#### RAudio

**Methods:**

- `CreateAudioObject()`
- `LoadAudioToObject(*args)`
- `__init__(self)`

#### RAudioRecorder

**Methods:**

- `__init__(self)`
- `SetInputDevice(self, strInputAudioDeviceName)`
- `SetTimeLimit(self, nMillisecond)`
- `GetTimeLimit(self)`
- `Start(self)`
- `Stop(self)`
- `GetAudio(self)`
- `GetAvailableDevices(self)`
- `GetInputDevice(self)`
- `RegisterCallback(self, pCallback)`
- `UnregisterCallback(self)`

#### RAudioRecorderCallback

**Methods:**

- `__init__(self)`
- `OnTimeLimitReached(self)`

#### RBeginCommandOption

**Methods:**

- `__init__(self)`

#### RBodySetting

**Methods:**

- `__init__(self, *args)`
- `SetActivePart(self, eActivePart)`
- `GetActivePart(self)`
- `SetMirrorState(self, bIsMirror)`
- `GetMirrorState(self)`
- `SetFixLowerState(self, bIsFixLower)`
- `GetFixLowerState(self)`
- `SetLockFootRotationState(self, bIsLockFootRotation)`
- `GetLockFootRotationState(self)`
- `SetFootBottomToAnkle(self, fFootBottomToAnkle)`
- `GetFootBottomToAnkle(self)`
- `SetMotionApplyMode(self, eMotionApplyMode)`
- `GetMotionApplyMode(self)`
- `SetReferenceAvatar(self, spAvatar)`
- `GetReferenceAvatar(self)`
- `SetHipPositionLockedAxes(self, eAxes)`
- `GetHipPositionLockedAxes(self)`
- `SetCoordinateOffset(self, fRotation, vTranslation)`
- `GetCoordinateOffset(self, fRotation, vTranslation)`
- `SetMotionMatchSource(self, bMatchSource)`
- `GetMotionMatchSource(self)`

#### RCallback

**Methods:**

- `__init__(self)`

#### RCameraDofData

**Methods:**

- `SetEnable(self, bEnable)`
- `GetEnable(self)`
- `SetFocus(self, fFocusData)`
- `GetFocus(self)`
- `SetRange(self, fRangeData)`
- `GetRange(self)`
- `SetNearTransitionRegion(self, fNearTransitionRegion)`
- `GetNearTransitionRegion(self)`
- `SetFarTransitionRegion(self, fFarTransitionRegion)`
- `GetFarTransitionRegion(self)`
- `SetNearBlurScale(self, fNearBlurScale)`
- `GetNearBlurScale(self)`
- `SetFarBlurScale(self, fFarBlurScale)`
- `GetFarBlurScale(self)`
- `SetMinBlendDistance(self, fMinBlendDistance)`
- `GetMinBlendDistance(self)`
- `SetCenterColorWeight(self, fCenterColorWeight)`
- `GetCenterColorWeight(self)`
- `SetEdgeDecayPower(self, fEdgeDecayPower)`
- `GetEdgeDecayPower(self)`
- `__init__(self)`

#### RColor

**Methods:**

- `__init__(self, *args)`
- `R(self, *args)`
- `G(self, *args)`
- `B(self, *args)`
- `A(self, *args)`
- `Red(self)`
- `Green(self)`
- `Blue(self)`
- `Alpha(self)`
- `From(self, r, g, b, a)`
- `FromARGB(self, arg2)`
- `FromCOLORREF(self, arg2)`
- `ToARGB(self)`
- `ToCOLORREF(self)`
- `ToGrayScale(self)`
- `Normalize(self)`
- `Saturate(self)`
- `GammaCorrect(self, fGamma)`
- `ToHSL(self, fHue, fSaturate, fLevel)`
- `FromHSL(self, fHue, fSaturate, fLevel)`
- `AdjustHSBC(self, fHue, fSaturate, fBrightness, fContrast, bInvert)`
- `AdjustRGBA(self, fRed, fGreen, fBlue, fAlpha, bInvert)`
- `__iadd__(self, arg2)`
- `__isub__(self, arg2)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `__pos__(self)`
- `__neg__(self)`
- `__add__(self, arg2)`
- `__sub__(self, arg2)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__eq__(self, arg2)`
- `__ne__(self, arg2)`
- `__lt__(self, arg2)`

#### RControl

**Methods:**

- `__init__(self, *args, **kwargs)`
- `MaxControlTime(self)`
- `HasKeys(self)`
- `GetKeyCount(self)`
- `GetKeyIndex(self, kTick, nIdx)`
- `MoveKey(self, kTick, kOffsetTick)`
- `MoveAllKey(self, kTick)`
- `RemoveKey(self, kTick)`
- `RemoveKeys(self, kStartTime, kEndTime, bExcludeBound)`
- `GetKeyTimeAt(self, uIndex, kTick)`
- `RemoveKeyAt(self, nIndex)`
- `AddKey(self, pKey)`
- `ClearKeys(self)`
- `Clone(self)`
- `LoadDataBlockData(self, rkStream, pkLink, pProgress)`
- `GetDataBlock(self)`
- `GetKeyTransitionType(self, *args)`
- `GetKeyTransitionStrength(self, *args)`
- `SetKeyTransition(self, kTick, eType, fStrength)`

#### RCustomValue

**Methods:**

- `__eq__(self, kValue)`
- `AssignTo(self, kTargetValue)`
- `__init__(self, *args)`
- `SetValue(self, *args)`
- `GetType(self)`
- `GetValue(self, *args)`
- `ToInteger(self)`
- `ToInt64(self)`
- `ToFloat(self)`
- `ToDouble(self)`
- `ToString(self)`
- `ToWString(self)`
- `ToChar(self)`
- `ToBoolean(self)`
- `ToHandle(self)`
- `ToMap(self)`
- `Clear(self)`

#### RCustomValueArray

**Methods:**

- `__init__(self, *args)`
- `AssignTo(self, kTargetArray)`
- `SetCapacity(self, uSize)`
- `Resize(self, uSize)`
- `Add(self, *args)`
- `Clear(self, uCapacity=32)`
- `RemoveAt(self, uIndex)`
- `GetSize(self)`
- `__getitem__(self, *args)`

#### RCustomValueMap

**Methods:**

- `__init__(self, *args)`
- `GetSize(self)`
- `GetKey(self, uIndex)`
- `GetValue(self, uIndex)`

#### RDataBlock

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetControl(self, *args)`
- `Clone(self)`
- `GetData(self, *args)`
- `GetBlockData(self, strName)`
- `SetData(self, *args)`
- `AddAttribute(self, spAttribute)`
- `RemoveAttribute(self, spAttribute)`
- `GetAttributes(self)`
- `LoadFromFile(self, strPath)`
- `SaveToFile(self, strPath)`
- `Create(kAttributes)`

#### RDepthParam

**Methods:**

- `__init__(self)`

#### RDeviceSetting

**Methods:**

- `__init__(self, *args)`
- `SetCoordinateSystem(self, eCoordinateSystem)`
- `GetCoordinateSystem(self)`
- `SetMocapCoordinate(self, eUpAxis, eFrontAxis, eCoordinateSystem)`
- `GetMocapCoordinateUpAxis(self)`
- `GetMocapCoordinateFrontAxis(self)`
- `GetMocapCoordinateSystem(self)`
- `SetCoordinateOffset(self, fRotation, vTranslation)`
- `GetCoordinateOffset(self, fRotation, vTranslation)`
- `GetAxisXYZ(self, eAxis)`
- `GetPositionSetting(self)`
- `GetRotationSetting(self)`
- `SetInitialHipRotation(self, kInitialHipRotation)`
- `GetInitialHipRotation(self)`

#### RDialogCallback

**Inherits from:** `RCallback`

**Methods:**

- `__init__(self)`
- `OnDialogHide(self)`
- `OnDialogShow(self)`
- `OnDialogClose(self)`
- `__disown__(self)`

#### REdgeDetectionCannyParam

**Methods:**

- `__init__(self)`

#### REventCallback

**Inherits from:** `RCallback`

**Methods:**

- `__init__(self)`
- `OnTimerUpdated(self, fTime)`
- `OnSceneUpdated(self, fTime)`
- `OnCurrentTimeChanged(self, fTime)`
- `OnBeforeLoadFile(self, nFileType)`
- `OnBeforeLoadFileWithPath(self, nFileType, strFilePath)`
- `OnFileLoaded(self, nFileType)`
- `OnFileLoadedWithPath(self, nFileType, strFilePath)`
- `OnAfterFileLoaded(self, nFileType)`
- `OnAfterFileLoadedWithPath(self, nFileType, strFilePath)`
- `OnProjectDataChanged(self, nProjectDataType)`
- `OnBeforeSaveFile(self, nFileType, pProjectName)`
- `OnFileSaved(self, nFileType, pProjectName)`
- `OnObjectSelectionChanged(self)`
- `OnObjectDataChanged(self)`
- `OnObjectAdded(self)`
- `OnObjectDeleted(self)`
- `OnDialogModeChanged(self, nDialogMode)`
- `OnUndoRedoDone(self)`
- `OnPlayed(self)`
- `OnStopped(self)`
- `OnObjectDataChangedWithType(self, nObjectChangeDataType)`
- `OnHierarchyChanged(self)`
- `OnAPInitialized(self)`
- `OnSmartGalleryInitialized(self, bSuccess)`
- `OnOmniLiveChanged(self, bOn)`
- `OnImageAsyncLoadStart(self)`
- `OnImageAsyncLoadAllDone(self)`
- `OnCommandReceived(self, strCommand)`
- `OnLuaEvent(self, kParam)`
- `OnQuickMagicWebSocketNotified(self, strMessageData)`
- `OnServiceWebSocketNotified(self, nServiceType, strMessageData)`
- `OnMemberLoginStatusChanged(self, bLogin)`
- `OnRefreshDAPoints(self, nPoints)`
- `OnAPLayoutChanged(self)`
- `OnAPLayoutRestored(self)`
- `__disown__(self)`

#### REventHandler

**Methods:**

- `SetListener(pListener)`
- `RegisterCallback(pCallback)`
- `UnregisterCallback(uId)`
- `UnregisterCallbacks(kIds)`
- `__init__(self)`

#### RExportAudioParameter

**Methods:**

- `__init__(self)`

#### RExportCommonParameter

**Methods:**

- `__init__(self)`

#### RExportFbxSetting

**Methods:**

- `__init__(self)`
- `EnableExportMotion(self, bEnable)`
- `IsExportMotionEnabled(self)`
- `SetExportMotionFps(self, kFps)`
- `GetExportMotionFps(self)`
- `SetExportMotionRange(self, kRange)`
- `GetExportMotionRange(self)`
- `SetOption(self, eOptions)`
- `GetOption(self)`
- `SetOption2(self, eOptions)`
- `GetOption2(self)`
- `SetOption3(self, eOptions)`
- `GetOption3(self)`
- `SetTextureSize(self, eSize)`
- `GetTextureSize(self)`
- `SetTextureFormat(self, eFormat)`
- `GetTextureFormat(self)`
- `SetIncludeMotionPath(self, strPath)`
- `GetIncludeMotionPath(self)`
- `EnableBakeDiffuseSpecularFromShader(self, bEnable)`
- `IsBakeDiffuseSpecularFromShaderEnabled(self)`
- `EnableBakeDiffuseFromSkinColor(self, bEnable)`
- `IsBakeDiffuseFromSkinColorEnabled(self)`
- `EnableBasicBindPose(self, bEnable)`
- `IsBasicBindPoseEnabled(self)`
- `EnableBakeSubdivision(self, bEnable)`
- `IsBakeSubdivisionEnabled(self)`
- `SetEmbedTimecode(self, bEmbed)`
- `IsEmbedTimecode(self)`
- `SetExportLevel(self, nExportLevel)`
- `GetExportLevel(self)`
- `SetUnrealBoneStructure(self, eUnrealBoneStructure)`
- `GetUnrealBoneStructure(self)`

#### RExportGlbSetting

**Inherits from:** `RExportFbxSetting`

**Methods:**

- `__init__(self)`
- `SetMeshMotionMode(self, eMeshMotionMode)`
- `IsMotionOnly(self)`

#### RExportGoZMeshOption

**Methods:**

- `__init__(self)`

#### RExportImageParameter

**Methods:**

- `__init__(self)`

#### RExportImageSequenceParameter

**Methods:**

- `__init__(self)`

#### RExportOutputRangeParameter

**Methods:**

- `__init__(self)`

#### RExportVideoParameter

**Methods:**

- `__init__(self)`

#### RFacialSetting

**Methods:**

- `__init__(self, *args)`
- `SetBlend(self, bBlend)`
- `GetBlend(self)`
- `SetMode(self, eMode)`
- `GetMode(self)`
- `SetReplacePart(self, bHead, bLeftEye, bRightEye, kMorph, kCustom, kBone)`
- `GetReplacePart(self, bHead, bLeftEye, bRightEye, kMorph, kCustom, kBone)`

#### RFileIO

**Methods:**

- `LoadFile(*args)`
- `LoadFbxFile(*args)`
- `LoadClotheFromFbx(pAvatar, strFilePath, kFailedMeshList)`
- `LoadObject(strFilePath, bRecordStep=True)`
- `LoadAlembicFile(spObject, strFilePath, eUpAxis)`
- `ExportFbxFile(*args)`
- `IsCompatibleWithExportOption(spObject, kSetting)`
- `CheckExportFbxHasLicense(spObject)`
- `PreLoadMotion(strFilePath, spObject, kMotionLength)`
- `LoadMotion(strFilePath, kTime, spObject)`
- `SaveThumbnailToFile(strRLFile, strSaveTo)`
- `ExportObjFile(*args)`
- `LoadSubstancePainterTextures(spObject, strFolderPath)`
- `SaveProject(strSavePath)`
- `SaveFile(spObject, kSaveSetting, strSavePath)`
- `ExportGoZFile(kObjects, strFolderPath, kSetting)`
- `ExportMultiPoseGoZFile(kObjects, kFolderPaths, kSettings)`
- `GetTagsFromFileHeader(strFilePath, kTagList, eType)`
- `ExportBvhFile(spObject, strFilePath)`
- `ExportBvhFile2(*args)`
- `ConvertFbxFileToRLMotion(*args)`
- `__init__(self)`

#### RFlattenWrinkleImageMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### RFloatControl

**Inherits from:** `RControl`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetValue(self, kTick, fValue, fDefaultValue=0.0)`
- `SetValue(self, *args)`
- `SetValueAt(self, uIndex, fValue)`
- `OptimizeKeys(self, kBeginTime, kEndTime, kFps, fError=0.5)`
- `ReserveKeyCapacity(self, uSize)`
- `RemoveKeys(self, kTicks)`
- `SyncAdapterToControl(self)`

#### RFloatKey

**Inherits from:** `RKey`

**Methods:**

- `__init__(self, *args)`
- `Clone(self)`
- `SetValue(self, fValue)`
- `GetValue(self)`

#### RFps

**Methods:**

- `__eq__(self, kFps)`
- `__ne__(self, kFps)`
- `__gt__(self, kFps)`
- `__ge__(self, kFps)`
- `__lt__(self, kFps)`
- `__le__(self, kFps)`
- `TickPerFrame(self)`
- `GetFrameIndex(self, kTime)`
- `UpFrameIndex(self, kTime)`
- `RoundFrameIndex(self, kTime)`
- `IndexedFrameTime(self, nFrameIndex)`
- `BaseOneIndexedFrameTime(self, nFrameIndex)`
- `GetFrameTime(self, kTime)`
- `GetNextFrameTime(self, kTime)`
- `GetPreviousFrameTime(self, kTime)`
- `IsSameFrame(self, kTime1, kTime2)`
- `FrameTimeFromSecond(self, fSecond)`
- `SecondFromFrameTime(self, kTime)`
- `EqualFrameTime(self, kA, kB)`
- `LessFrameTime(self, kA, kB)`
- `LessEqualFrameTime(self, kA, kB)`
- `ToTimecodeFormattedString(self, kTime)`
- `FromTimecodeFormattedString(self, strTimecode)`
- `ToInt(self)`
- `ToFloat(self)`
- `ToDouble(self)`
- `ToLong(self)`
- `ToUInt32(self)`
- `ToInt64(self)`
- `__init__(self, tFps)`

#### RGlobal

**Methods:**

- `GetProjectLength()`
- `SetProjectLength(kLength)`
- `GetFps()`
- `GetPath(ePath, strPath)`
- `BeginAction(strAction, bBlockRecordUndo=False)`
- `EndAction()`
- `Undo()`
- `Redo()`
- `Play(kStart, kEnd)`
- `Pause()`
- `Stop()`
- `IsPlaying()`
- `GetTime()`
- `SetTime(kTime, bSendEvent=True)`
- `GetStartTime()`
- `GetEndTime()`
- `SetStartTime(kTime)`
- `SetEndTime(kTime)`
- `GetMocapManager()`
- `TrialVersionRemainingDays(strBinPath, uProductID, strProductFold, strRegRoot)`
- `DoSNVerification(nProductID, strRegistry, strProductName, strSNFailTitle, strSNFailMsg, strSNExceedTitle, strSNExceedMsg)`
- `DoBatchSNVerification(strJson)`
- `DoPluginTrialFollowUp(strProductNamePath, nPID)`
- `IsTrialContentMode()`
- `IsTrialVersion()`
- `RemoveAllAnimations(spObject)`
- `RenderVideo(*args)`
- `RenderAudio(*args)`
- `RenderVideoNormal(*args)`
- `RenderVideoDepth(*args)`
- `RenderVideoCanny(*args)`
- `RenderVideoOpenPoseKeyPoint(*args)`
- `RenderImageSequence(*args)`
- `RenderImageSequenceNormal(*args)`
- `RenderImageSequenceDepth(*args)`
- `RenderImageSequenceCanny(*args)`
- `RenderImageSequenceOpenPoseKeyPoint(*args)`
- `RenderImage(strOutputFileName)`
- `SetRenderExportType(kParams)`
- `GetRenderExportType()`
- `GetRenderExportImageParameter()`
- `GetRenderExportImageSequenceParameter()`
- `GetRenderExportVideoParameter()`
- `SetRenderExportParameter(*args)`
- `GetRenderExportAudioParameter()`
- `GetScreenSize(nWidth, nHeight)`
- `TrialVersionRemainingTimes(strBinPath, uProductID, strProductFold, strRegRoot, uTimeNo)`
- `TrialVersionIncreaseTimes(strBinPath, uProductID, strProductFold, strRegRoot, nCount=1)`
- `ObjectModified(spObject, eType)`
- `ObjectDataChanged2(spObject, eType)`
- `GetPreviewStartTime()`
- `GetPreviewEndTime()`
- `SetPreviewStartTime(kTime)`
- `SetPreviewEndTime(kTime)`
- `SetMotionSettingOptions(eOptions)`
- `GetMotionSettingOptions()`
- `GetVisualSettingComponent()`
- `RenderPreview(*args)`
- `RenderPreviewNormal(*args)`
- `RenderPreviewDepth(*args)`
- `RenderPreviewCanny(*args)`
- `RenderPreviewOpenPoseKeyPoint(*args)`
- `ForceViewportUpdate()`
- `GetMotionDirector()`
- `GetOmniConnectorManager()`
- `GetDialogMode()`
- `SetDialogMode(eMode)`
- `GetSilentMode()`
- `SetSilentMode(bSilent)`
- `SetViewSize(nWidth, nHeight)`
- `GetViewSize(nWidth, nHeight)`
- `EnablePixelStream(bEnable)`
- `CapturePixelStream()`
- `GetDefaultContentFileAbsolutePath(eContent, bCustom)`
- `SetTimecodeSource(eSource)`
- `SetTimecodeSourceData(eSource, strFormattedTime)`
- `GetTimecodeTime()`
- `SetViewportInfoMotionLiveDevice(*args)`
- `CheckTimecodePluginFeatureAllowed()`
- `CheckTimecodePluginTrialValid()`
- `CheckTimecodePluginFullOrTiralInstalled()`
- `IsPhysicsSimulationLoop()`
- `SetPhysicsSimulationLoop(bLoop)`
- `ShowMemberLoginDialog()`
- `AddInfoTips(pObjPtr, strImageSource, strFunctionName, strDescription, strVideoURLLinkcountId, strButtonText, strLearnMoreURL)`
- `SendLogToServer(*args)`
- `__init__(self)`

#### RHandSetting

**Methods:**

- `__init__(self, *args)`
- `Clone(self)`
- `SetActivePart(self, eActivePart)`
- `GetActivePart(self)`
- `SetRightHandJoin(self, eHandJoin)`
- `GetRightHandJoin(self)`
- `SetLeftHandJoin(self, eHandJoin)`
- `GetLeftHandJoin(self)`
- `SetHandJoinType(self, eJoinType)`
- `GetHandJoinType(self)`
- `SetRightHandDataSource(self, eDataSource)`
- `GetRightHandDataSource(self)`
- `SetLeftHandDataSource(self, eDataSource)`
- `GetLeftHandDataSource(self)`

#### RHeadshot

**Methods:**

- `CreateHeadFromPhoto(strPhotoPath, eMode, kOption)`
- `ImportHeadFromObj(*args)`
- `__init__(self)`

#### RHeadshotOption

**Methods:**

- `__init__(self)`

#### RIAccessory

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `TransferSkinWeight(self, strTemplateType)`
- `GetPhysicsComponent(self)`
- `ConvertToHair(self, eHairType)`
- `ConvertToFaceHair(self, eFaceHairType)`
- `GetMaterialComponent(self)`

#### RIAudioObject

**Methods:**

- `__init__(self, *args, **kwargs)`
- `HasData(self)`
- `Save(self, strPath)`
- `Load(self, strPath)`

#### RIAvatar

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetVisible(self, kTime, bVisible)`
- `GetSkeletonComponent(self)`
- `GetVisemeComponent(self)`
- `GetAvatarShapingComponent(self)`
- `GetMorphComponent(self)`
- `GetMaterialComponent(self)`
- `GetPhysicsComponent(self)`
- `GetHikEffectorComponent(self)`
- `GetFaceComponent(self)`
- `GetFacialProfileComponent(self)`
- `GetGeneration(self)`
- `GetAvatarType(self)`
- `GetAccessories(self, bAll=True)`
- `GetClothes(self)`
- `GetHairs(self)`
- `IsVisible(self, kTime)`
- `LoadAccessoryWithTransferSkinWeight(self, kFilePath, kTemplateType)`
- `GetAvatarParts(self, *args)`
- `ConvertTo(self, *args)`
- `GetFloorContactValue(self, eType)`
- `SetFloorContactValue(self, eType, fValue)`
- `AutoAdjustFootHeight(self)`
- `SaveHikProfile(self, strPath)`
- `DoCharacterization(self, strPath, bApplyTpose, bApplyBoneMapping, bSendUpdateEvent)`
- `ReplaceMesh(self, strMeshName, strObjFilePath, bSplitObjects=False, bAutoRig=False)`
- `GetSubdivMeshLevel(self)`
- `GetMaxSubdivMeshLevel(self)`
- `SwitchSubdivMeshLevel(self, nLevel)`
- `GetMorpherConstraintsEnabled(self)`
- `HasMorpherConstraintsSet(self)`
- `UpdateWrinkle(self)`

#### RIAvatarPart

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetAvatarPartType(self)`
- `ConvertToHair(self, eHairType)`
- `ConvertToFaceHair(self, eFaceHairType)`
- `GetFaceHairType(self)`

#### RIAvatarShapingComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `CreateSlider(self, kMorphSliderInputData, strOutputFilePath)`
- `GetShapingMorphIDs(self, strCatergory)`
- `GetShapingMorphDisplayNames(self, strCatergory)`
- `SetShapingMorphDisplayName(self, strId, strName)`
- `GetShapingMorphCatergoryNames(self)`
- `GetShapingMorphMinMax(self, strID)`
- `GetShapingMorphWeight(self, strID)`
- `SetShapingMorphWeight(self, strID, fWeight)`

#### RIBase

**Methods:**

- `__init__(self, *args, **kwargs)`
- `IsValid(self)`

#### RIBodyDevice

**Inherits from:** `RIDeviceBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `Initialize(self, kBoneList)`
- `SetTPoseData(self, *args)`
- `ProcessData(self, nDataIndex, kData, nDeviceTime=-1)`
- `ProcessAllData(self, kDataIndexes, kData, kDeviceTimes)`
- `IsTPoseReady(self, spAvatar)`
- `GetDeviceSetting(self)`
- `SetProcessDataIndex(self, spAvatar, nIndex)`
- `GetProcessDataIndex(self, spAvatar)`
- `SetBodySetting(self, *args)`
- `GetBodySetting(self, spAvatar)`

#### RIBuildingGeneratorObject

**Methods:**

- `GenerateBuilding(kSettings, kInfo)`
- `IsBuildingRoot(spObject)`
- `IsFloor(spObject)`
- `IsUnit(spObject)`
- `IsWall(spObject)`
- `GetBuildingRoot(spObject)`
- `GetFloorByChild(spObject)`
- `GetUnitByChild(spObject)`
- `__init__(self)`

#### RIBuildingObject

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddBlankFloor(self, nNewFloor, nTemplate, nColumn, nRow, fWidth, fLength, strDummyPropFileName)`
- `DeleteFloor(self, spFloorObject)`
- `GetFloors(self, kFloors)`
- `GetFloorNumber(self, spFloor)`
- `DuplicateFloor(self, nNewFloor, spFloor)`
- `UpdateFloorsPosition(self)`
- `MoveFloor(self, spTargetPosition, spFloor, bMoveUpward)`
- `GetAllWalls(self, kWalls)`
- `Optimize(self)`

#### RICamera

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetFocalLength(self, kTime, fFocalLength)`
- `GetFocalLength(self, kTime)`
- `GetFocalLengthKeyCount(self)`
- `RemoveFocalLengthKey(self, kTime)`
- `RemoveFocalLengthKeys(self)`
- `AddDofKey(self, kKey, kDofData)`
- `RemoveDofKey(self, kKey)`
- `RemoveDofKeys(self)`
- `GetDofKeyCount(self)`
- `GetDOFData(self)`
- `GetAngleOfView(self, kTime)`
- `GetAperture(self, fWidth, fHeight)`
- `GetFitRenderRegionType(self)`
- `GetFitFovType(self)`
- `GetNearClippingPlane(self)`
- `SetNearClippingPlane(self, nNearPlane)`
- `GetFarClippingPlane(self)`
- `SetFarClippingPlane(self, nFarPlane)`
- `GetNearClippingPlaneF(self)`
- `SetNearClippingPlaneF(self, fNearPlane)`
- `GetFarClippingPlaneF(self)`
- `SetFarClippingPlaneF(self, fFarPlane)`
- `IsLookAtMode(self, kTime)`

#### RIClip

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetControl(self, strKey, spNode)`
- `GetDataBlock(self, strKey, spBase)`
- `GetEffectorDataBlock(self, strKey, spBase, spDataBlock, spActiveDataBlock)`
- `GetType(self)`
- `GetLength(self)`
- `GetStartOffset(self)`
- `SetLength(self, kLength)`
- `GetLastKeyTime(self)`
- `SceneTimeToClipTime(self, kSceneTick)`
- `ClipTimeToSceneTime(self, kClipTick)`
- `GetClipLength(self)`
- `GetTransitionRange(self)`
- `SetTransitionRange(self, kLength)`
- `GetSpeed(self)`
- `SetSpeed(self, fSpeed)`
- `GetLoopCount(self)`
- `GetTransitionData(self)`
- `SetTransitionData(self, kData)`
- `SetTransitionType(self, bFadeIn, eTransitionType, fTransitionStrength)`
- `GetTransitionType(self, bFadeIn)`
- `GetTransitionStrength(self, bFadeIn)`
- `GetWeightLayerControlName(self)`
- `SetWeightLayerControlName(self, strName)`
- `GetRtsLayerControlName(self)`
- `SetRtsLayerControlName(self, strName)`
- `GetRtsClipControlName(self)`
- `SetRtsClipControlName(self, strName)`
- `AddTimecodeData(self, fFps, fMilliseconds)`

#### RICloth

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `IsClothConformingEnable(self)`
- `SetClothConformingEnable(self, bEnable)`
- `GetClothConformValue(self, strConform)`
- `SetClothConformValue(self, strConform, fValue)`
- `CalculateCollision(self)`
- `TransferSkinWeight(self, strTemplateType)`
- `GetClotheType(self)`
- `SetClotheType(self, eClotheType)`
- `ConvertToAccessory(self, bCurrentShape)`
- `GetMaterialComponent(self)`
- `GetPhysicsComponent(self)`

#### RIDeviceBase

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetDeviceID(self)`
- `GetDeviceType(self)`
- `AddAvatar(self, spAvatar)`
- `AddAvatars(self, kAvatarList)`
- `RemoveAvatar(self, spAvatar)`
- `GetAvatarAt(self, nIndex)`
- `GetAvatarCount(self)`
- `SetEnable(self, spAvatar, bEnable)`
- `IsEnable(self, spAvatar)`

#### RIDialog

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetWindow(self)`
- `GetTitle(self)`
- `GetWindowTitle(self)`
- `SetWindowTitle(self, strTitleName)`
- `SetParent(self, pWidget)`
- `Exec(self)`
- `Show(self)`
- `Hide(self)`
- `Close(self)`
- `IsVisible(self)`
- `SetModal(self, bModal)`
- `IsModal(self)`
- `GetDialogType(self)`
- `RegisterNativeEventCallback(self, pfCallback)`
- `UnregisterNativeEventCallback(self, uId)`
- `UnregisterNativeEventCallbacks(self, kIds)`
- `RegisterEventCallback(self, pfCallback)`
- `UnregisterEventCallback(self, uId)`
- `UnregisterEventCallbacks(self, kIds)`
- `UnregisterAllEventCallbacks(self)`

#### RIDirectionalLight

**Inherits from:** `RILight`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetCastShadow(self, bEnable)`
- `IsCastShadow(self)`
- `SetDarkenShadowStrength(self, kTime, fStrength)`
- `GetDarkenShadowStrength(self)`
- `SetTransmission(self, b)`
- `GetTransmission(self)`

#### RIDockWidget

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetWindow(self)`
- `GetTitle(self)`
- `GetWindowTitle(self)`
- `SetWindowTitle(self, strTitleName)`
- `SetWidget(self, pWidget)`
- `SetParent(self, pWidget)`
- `Show(self)`
- `Hide(self)`
- `Close(self)`
- `IsVisible(self)`
- `SetAllowedAreas(self, eArea)`
- `SetFloating(self, bFloating)`
- `SetFeatures(self, eFeatures)`
- `Features(self)`
- `IsAreaAllowed(self, eArea)`
- `IsFloating(self)`
- `RegisterNativeEventCallback(self, pfCallback)`
- `UnregisterNativeEventCallback(self, uId)`
- `UnregisterNativeEventCallbacks(self, kIds)`
- `RegisterEventCallback(self, pfCallback)`
- `UnregisterEventCallback(self, uId)`
- `UnregisterEventCallbacks(self, kIds)`
- `UnregisterAllEventCallbacks(self)`

#### RIEffector

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetEffector(self)`

#### RIElementObject

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`

#### RIEventListener

**Methods:**

- `__init__(self, *args, **kwargs)`
- `Init(self)`
- `RegisterCallback(self, pCallback)`
- `UnregisterCallback(self, uId)`
- `UnregisterCallbacks(self, kIds)`

#### RIFaceComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddClip(self, kTime, strName, kLength)`
- `GetStrength(self)`
- `GetExpressionNames(self, strType, bMocapOrder=False)`
- `GetExpressionStatuses(self, strType)`
- `GetAutoBlinkNames(self)`
- `GetAutoBlinkName(self)`
- `SetAutoBlinkName(self, strName)`
- `GetClipCount(self)`
- `GetClip(self, uIndex)`
- `GetClipByTime(self, kHitTime)`
- `BreakClip(self, kTime)`
- `DeleteClip(self, spClip)`
- `GetExpressionGroups(self)`
- `GetExpressionWeights(self, *args)`
- `GetExpressionSetUid(self)`
- `BeginKeyEditing(self)`
- `AddExpressionKeys(self, kTime, kExpressions, kStrengths, kInterval)`
- `EndKeyEditing(self)`
- `GetExpressiveness(self, kTime)`
- `AddExpressivenessKey(self, kTime, fWeight)`
- `ImportExpression(self, kSettings)`
- `GetExpressionBoneRotation(self, strBoneName, strExpression)`
- `SetCurrentPoseMode(self)`
- `IsCurrentPoseMode(self)`

#### RIFacialDevice

**Inherits from:** `RIDeviceBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `Initialize(self)`
- `SetFacialSetting(self, *args)`
- `GetFacialSetting(self, spAvatar)`
- `ProcessData(self, *args)`

#### RIFacialProfileComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SaveProfile(self, strPath)`
- `LoadProfile(self, strPath)`
- `ImportMorphs(self, strPath, bReplaceSameSlider, kImportExpressions, strImportCategory)`
- `GetProfileType(self)`
- `GetExpressionCategoryNames(self)`
- `GetExpressionSliderNames(self, strCategoryName)`

#### RIFloorObject

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `BuildFloor(self, *args)`
- `ReBuildFloorWithKeepFacadeSetting(self, *args)`
- `ClearFloor(self)`
- `GetUnits(self)`

#### RIHair

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetPhysicsComponent(self)`
- `ConvertToHair(self, eHairType)`
- `ConvertToFaceHair(self, eFaceHairType)`
- `GetHairType(self)`
- `GetMaterialComponent(self)`

#### RIHandDevice

**Inherits from:** `RIDeviceBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `Initialize(self, kBoneList)`
- `SetTPoseData(self, spAvatar, kData)`
- `ProcessData(self, nDataIndex, kData, nDeviceTime=-1)`
- `IsTPoseReady(self, spAvatar)`
- `GetDeviceSetting(self)`
- `SetProcessDataIndex(self, spAvatar, nIndex)`
- `GetProcessDataIndex(self, spAvatar)`
- `SetHandSetting(self, *args)`
- `GetHandSetting(self, spAvatar)`

#### RIHikEffectorComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetActive(self, eEffector, eType, bActive)`
- `GetActive(self, eEffector, eType)`
- `SetLock(self, eEffector, eType, bLock)`
- `GetLock(self, eEffector, eType)`
- `SetPosition(self, *args)`
- `Solve(self, eEffector, kMatrix)`
- `SetBodyWeight(self, fWeight)`
- `AddReachKey(self, eEffector, kKey)`
- `RemoveReachKey(self, eEffector, kKey)`
- `GetReachKeys(self, eEffector)`
- `GetBone(self, strEffectorText)`
- `SetReachOffsetKey(self, strEffectorText, kTime, mOffset)`

#### RIImage

**Methods:**

- `__init__(self, *args, **kwargs)`
- `LoadFile(self, strPath)`
- `SaveFile(self, strPath)`
- `GetWidth(self)`
- `GetHeight(self)`
- `GetQImage(self)`
- `SetImageData(self, pQImage)`
- `CopyImage(self)`
- `IsSameImage(self, spImage, fTolerance=0.001)`

#### RILight

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetActive(self, kTime, bActive)`
- `GetActive(self)`
- `SetMultiplier(self, kTime, fMultiplier)`
- `GetMultiplier(self)`
- `SetColor(self, kTime, kColor)`
- `GetColor(self)`

#### RILightAvatar

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetGeneration(self)`
- `GetAvatarType(self)`
- `GetSkeletonComponent(self)`
- `GetVisemeComponent(self)`
- `GetMorphComponent(self)`
- `GetFaceComponent(self)`
- `IsVisible(self, kTime)`

#### RILookAtComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddLookAtKey(self, *args)`
- `GetLookAtOffsetDataBlock(self)`
- `GetLookAtWeightDataBlock(self, bIsBody)`

#### RIMDProp

**Inherits from:** `RIProp`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `IsInitialOccupy(self)`
- `IsStartOnEntryDummy(self)`
- `IsActiveCrowdInteraction(self)`
- `IsEnableFollowMode(self)`
- `IsChangedFollowObject(self)`
- `GetCrowdExitType(self)`
- `GetInteractTimes(self)`
- `GetDistance(self)`
- `GetTagRatioMap(self)`
- `GetTagRatio(self, strTagName)`

#### RIMaterialComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddAmbientKey(self, kKey, strMeshName, strMaterialName, kColor)`
- `AddDiffuseKey(self, kKey, strMeshName, strMaterialName, kColor)`
- `AddGlossinessKey(self, kKey, strMeshName, strMaterialName, fWeight)`
- `AddSpecularKey(self, *args)`
- `AddSelfIlluminationKey(self, kKey, strMeshName, strMaterialName, fWeight)`
- `AddOpacityKey(self, kKey, strMeshName, strMaterialName, fWeight)`
- `AddTextureWeightKey(self, kKey, strMeshName, strMaterialName, eChannel, fWeight)`
- `AddUvDataKey(self, kKey, strMeshName, strMaterialName, eChannel, kUvOffset, kUvTile, fUvRotate)`
- `RemoveUvDataKey(self, kKey, strMeshName, strMaterialName, eChannel)`
- `LoadVideoToTexture(self, kKey, strMeshName, strMaterialName, eChannel, strVideoPath)`
- `LoadImageToTexture(self, strMeshName, strMaterialName, eChannel, strImagePath)`
- `AddVideoVolumeKey(self, kKey, strMeshName, strMaterialName, eChannel, fVol, bMute)`
- `GetMaterialNames(self, strMeshName)`
- `GetAmbientColor(self, strMeshName, strMaterialName)`
- `GetDiffuseColor(self, strMeshName, strMaterialName)`
- `GetSpecularColor(self, strMeshName, strMaterialName)`
- `GetGlossinessWeight(self, strMeshName, strMaterialName)`
- `GetSpecularWeight(self, strMeshName, strMaterialName)`
- `GetSelfIlluminationWeight(self, strMeshName, strMaterialName)`
- `GetOpacity(self, strMeshName, strMaterialName)`
- `GetTextureWeights(self, strMeshName, strMaterialName)`
- `GetUvData(self, strMeshName, strMaterialName, eChannel, kUvOffset, kUvTile, fUvRotate)`
- `GetVideoVolume(self, strMeshName, strMaterialName, eChannel)`
- `GetAttributeValue(self, strMeshName, strMaterialName, strAttributeName)`
- `SetAttributeValue(self, strMeshName, strMaterialName, strAttributeName, fValue)`
- `IsTwoSidedMaterial(self, strMeshName, strMaterialName)`
- `SetTwoSidedMaterial(self, strMeshName, strMaterialName, bEnable)`
- `LoadMaterial(self, strMeshName, strMaterialName, strFilePath)`
- `RemoveMaterialTexture(self, strMeshName, strMaterialName, eChannel)`
- `GetShaderNames(self)`
- `GetShader(self, strMeshName, strMaterialName)`
- `SetShader(self, strMeshName, strMaterialName, strShader)`
- `GetShaderParameterNames(self, strMeshName, strMaterialName)`
- `GetShaderParameter(self, strMeshName, strMaterialName, strParameter)`
- `SetShaderParameter(self, strMeshName, strMaterialName, strParameter, kValue)`
- `GetShaderTextureNames(self, strMeshName, strMaterialName)`
- `LoadShaderTexture(self, strMeshName, strMaterialName, strName, strTexturePath)`
- `GetRefraction(self, strMeshName, strMaterialName)`
- `IsRefractionEnable(self, strMeshName, strMaterialName)`
- `SetRefractionEnable(self, strMeshName, strMaterialName, bEnable)`
- `AddRefractionKey(self, kKey, strMeshName, strMaterialName, fWeight)`
- `GetReflection(self, strMeshName, strMaterialName)`
- `IsReflectionEnable(self, strMeshName, strMaterialName)`
- `SetReflectionEnable(self, strMeshName, strMaterialName, bEnable)`
- `AddReflectionKey(self, kKey, strMeshName, strMaterialName, fWeight)`
- `MakeUnique(self, strMeshName, strMaterialName)`
- `SetWrinkleRule(self, strMeshName, strMaterialName, strRelateName, uMaskValueIndex, uMaskTextureIndex, strMaskChannel, fWeight)`
- `SetWrinkleActionToRule(self, strMeshName, strMaterialName, strActionName, strRuleName, strRuleRangeMin, strRuleRangeMax)`
- `SetWrinkleTextureFilePath(self, strMeshName, strMaterialName, strDiffusePath, strNormalPath, strRoughnessPath, uWrinkleImageIndex)`
- `SetWrinkleMaskFilePath(self, strMeshName, strMaterialName, strMaskPath, uMaskIndex)`
- `AddWrinkleWeightKey(self, kKey, strMeshName, strMaterialName, uRuleIndex, nWeight)`
- `SetImageColor(self, strMeshName, strMaterialName, eChannel, fSoftness, kHsbc, kCmy)`
- `GetImageColor(self, strMeshName, strMaterialName, eChannel)`
- `SetMaterialName(self, strMeshName, strOrgMatName, strNewMatName)`
- `MergeMaterialUV(self, *args)`
- `SetWrinkleFlattenTexture(self, eChannel, strImagePath)`
- `SetWrinkleDetailParameters(self, eWrinkleFacePart, eWrinkleLayerType, fStrength)`
- `SetWrinkleDetailStrength(self, eWrinkleFacePart, fStrength)`
- `GetImage(self, strMeshName, strMaterialName, eChannel)`
- `HasImage(self, strMeshName, strMaterialName, eChannel)`
- `SetImage(self, spImage, strMeshName, strMaterialName, eChannel)`
- `SetMaterialSettings(self, kOptions, strMeshName, strMaterialName)`
- `CopyMaterial(self, strSrcMeshName, strSrcMaterialName, strDstMeshName, strDstMaterialName)`
- `GetResourceMapImage(self, strMeshName, strMaterialName, strResourceMapName)`

#### RIMesh

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetName(self)`
- `GetID(self)`
- `GetVerticesCount(self)`
- `GetFacesCount(self)`
- `GetVertex(self, nIndex, bWorld=False)`
- `GetVertices(self, bWorld=False)`
- `GetFace(self, nFaceIdx)`
- `DeleteFaces(self, kFaceIndexs)`
- `ConvertToAccessory(self, bCurrentShape=True)`
- `ReplaceMesh(self, strPath, eOption, bReplaceUv, bSplitObjects=False)`
- `GetStdMaterials(self)`

#### RIMocapManager

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddBodyDevice(self, strDeviceID)`
- `AddHandDevice(self, strDeviceID)`
- `AddFacialDevice(self, strDeviceID)`
- `GetDevice(self, strDeviceID)`
- `IsDeviceExist(self, strDeviceID)`
- `RemoveDevice(self, strDeviceID)`
- `RemoveAllDevices(self)`
- `Start(self, *args)`
- `Stop(self)`
- `IsRunning(self)`
- `MocapState(self)`

#### RIMorphComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddKey(self, strMeshName, strMorphName, kTime, fWeight, bSendEvent, bPauseAP)`
- `RemoveAllKeys(self, strMeshName, strMorphName)`
- `GetWeight(self, strMeshName, strMorphName, kTime, fWeight)`
- `GetMorphNames(self, strMeshName)`

#### RIMotionDirectorManager

**Methods:**

- `__init__(self, *args, **kwargs)`
- `Start(self)`
- `Stop(self)`
- `IsRunning(self)`
- `IsReady(self)`
- `BeginCommand(self, kTime, kObjects, kOption)`
- `EndCommand(self, *args)`
- `EmbedCommand(self, kTime, kAvatars)`
- `RemoveTriggeredByAnimation(self, kTime, kMDProps, kAvatarsToRecord)`

#### RINode

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetName(self)`
- `GetID(self)`
- `GetParent(self)`
- `GetChildren(self, bWithSameCustomID=False)`
- `LocalTransform(self)`
- `BasisTransform(self)`
- `WorldTransform(self)`
- `WorldToLocal(self, kWorldMatrix)`
- `LocalToWorld(self, kLocalMatrix)`
- `SetDataBlock(self, strId, spDataBlock)`
- `GetDataBlock(self, strId)`
- `RemoveDataBlock(self, strId)`
- `Update(self, *args)`

#### RINodeTransformPair

**Methods:**

- `__init__(self, *args)`
- `__len__(self)`
- `__repr__(self)`
- `__getitem__(self, index)`
- `__setitem__(self, index, val)`

#### RINodeTransformPairs

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__getslice__(self, i, j)`
- `__setslice__(self, *args)`
- `__delslice__(self, i, j)`
- `__delitem__(self, *args)`
- `__getitem__(self, *args)`
- `__setitem__(self, *args)`
- `pop(self)`
- `append(self, x)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `pop_back(self)`
- `erase(self, *args)`
- `__init__(self, *args)`
- `push_back(self, x)`
- `front(self)`
- `back(self)`
- `assign(self, n, x)`
- `resize(self, *args)`
- `insert(self, *args)`
- `reserve(self, n)`
- `capacity(self)`

#### RIObject

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetName(self)`
- `GetID(self)`
- `GetControl(self, strKey)`
- `GetType(self)`
- `GetMeshNames(self, bAll=True)`
- `__eq__(self, kRhs)`
- `LocalTransform(self)`
- `WorldTransform(self)`
- `SetParent(self, *args)`
- `LinkTo(self, *args)`
- `UnLink(self, kTime)`
- `GetLinkedObject(self, kTime)`
- `SetName(self, strName)`
- `GetPivot(self, kPosition, kOrientation)`
- `GetBounds(self, kMaxPoint, kCenterPoint, kMinPoint)`
- `Clone(self)`
- `IsSelected(self)`
- `SetDataBlock(self, strId, spDataBlock)`
- `GetDataBlock(self, strId)`
- `RemoveDataBlock(self, strId)`
- `RemoveLinkKey(self, kTime)`
- `ReleasePath(self, kTime)`
- `FollowPath(self, spPath, kAppTime)`
- `AlignTo(self, spTargetObject, eAlignAxis, bAlignToPivot)`
- `IsStatic(self)`
- `SetStatic(self, bStatic)`
- `GetMeshes(self, bAll=True)`
- `DeleteMesh(self, spMesh)`
- `Update(self, *args)`
- `GetParent(self)`
- `GetParentNode(self)`

#### RIOmniConnectorManager

**Methods:**

- `__init__(self, *args, **kwargs)`
- `TurnOnLiveSync(self, kObjects)`
- `TurnOffLiveSync(self)`
- `TransferFile(self, kObjects, kObjectSyncStates)`
- `SetTransferFileMotionSetting(self, kFps, nStartFrame, nEndFrame)`
- `SetTransferFileSetting(self, nMaxImageSize, nTextureFormat, bDeleteHiddenMesh, bSubdivisionMesh, bPathTracedMaterial, bIbl, bSwitchCamera)`
- `SetTransferMotionOnly(self, bMotionOnly)`
- `SetObjectSyncState(self, object, bSyncing)`
- `ObjectSyncStateListChanged(self, kObjects, kSyncStatuses)`
- `SetActiveLiveAdd(self, bSyncing)`
- `SetActive2WaySync(self, bActive)`

#### RIParticle

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetEmit(self, kTime, bOn)`
- `GetEmit(self)`

#### RIPath

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`

#### RIPhysicsComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetSoftPhysicsMeshNameList(self)`
- `GetSoftPhysicsMaterialNameList(self, strMeshName)`
- `IsActivatePhysicsEnable(self)`
- `SetActivatePhysicsEnable(self, bActivate)`
- `IsObjectGravityEnable(self, strMeshName, strMaterialName)`
- `SetObjectGravityEnable(self, strMeshName, strMaterialName, bObjectGravity)`
- `GetSoftPhysXProperty(self, strMeshName, strMaterialName, strPropertyName)`
- `SetSoftPhysXProperty(self, strMeshName, strMaterialName, strPropertyName, fValue)`
- `GetSoftPhysXCollisionValue(self, strMeshName, strMaterialName, strCollisionName)`
- `GetSoftPhysXCollisionEnable(self, strMeshName, strMaterialName, strCollisionName)`
- `SetSoftPhysXCollisionValue(self, strMeshName, strMaterialName, strCollisionName, fValue)`
- `SetSoftPhysXCollisionEnable(self, strMeshName, strMaterialName, strCollisionName, bEnable)`
- `SavePhysicsSoftColthWeightMap(self, strMeshName, strMaterialName, strFilePath)`
- `SetPhysicsSoftColthWeightMap(self, *args)`
- `GetPhysicsSoftColthWeightMap(self, strMeshName, strMaterialName)`

#### RIPointLight

**Inherits from:** `RILight`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetRange(self, kTime, fRange)`
- `GetRange(self)`
- `SetInverseSquare(self, b)`
- `GetInverseSquare(self)`
- `SetTubeShape(self, bTube)`
- `IsTubeShape(self)`
- `SetRectangleShape(self, bRectangle)`
- `IsRectangleShape(self)`
- `SetTubeLength(self, fLength)`
- `GetTubeLength(self)`
- `SetTubeRadius(self, radius)`
- `GetTubeRadius(self)`
- `SetTubeSoftRadius(self, softRadius)`
- `GetTubeSoftRadius(self)`
- `GetRectWidthHeight(self)`
- `SetRectWidthHeight(self, vWidthHeight)`
- `LoadRectTexture(self, strTexturePath)`
- `SaveRectTexture(self, strTexturePath)`
- `ClearRectTexture(self)`
- `LoadIes(self, strIesFilePath)`
- `SaveIes(self, strIesFilePath)`
- `SetCastShadow(self, bEnable)`
- `IsCastShadow(self)`

#### RIPopcornFXObject

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetEmit(self, kTime, bOn)`
- `SetLoop(self, bLoop)`
- `SetLoopInterval(self, fEmissionInterval)`
- `GetEmit(self)`
- `GetLoopInterval(self)`
- `IsLoop(self)`
- `GetEmitKeyCount(self)`
- `RemoveEmitKeys(self)`
- `GetAttributeCount(self)`
- `GetAttributeName(self, nIndex)`
- `GetAttributeValue(self, nIndex)`
- `GetSamplerList(self, eType)`
- `GetMeshSamplerTarget(self, strSamplerName)`
- `SetMeshSamplerTarget(self, strSamplerName, spObject)`
- `ClearMeshSamplerTarget(self, strSamplerName)`
- `AddAttributeKey(self, strName, kTime, kValue)`

#### RIProp

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetVisible(self, kTime, bVisible)`
- `GetSkeletonComponent(self)`
- `GetMorphComponent(self)`
- `GetMaterialComponent(self)`
- `SetPivot(self, kPosition, kOrientation)`
- `SetDummy(self, bIsDummy)`
- `IsDummy(self)`
- `IsVisible(self, kTime)`
- `MakeSubProp(self, bShowProgress=False)`
- `SetLinkOffsetKey(self, spTargetReachNode, spTargetBone, kTime)`
- `ReplaceMesh(self, strMeshName, strObjFilePath)`

#### RIReach

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetEffector(self)`
- `GetReachOffsetControl(self, strKey, nClipIndex=-1)`
- `IsSameReachOffset(self, pTarget, bCompareKeys)`
- `CheckClipModeAndGetFirstClipIndex(self, bClipMode, uFirstClipIndex)`

#### RISaveFileOptionBase

**Methods:**

- `__init__(self)`

#### RISkeletonComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetRootBone(self)`
- `GetClipCount(self)`
- `GetClip(self, uIndex)`
- `GetSkinBones(self)`
- `GetSelectedBones(self)`
- `GetEffector(self, eEffector)`
- `GetReach(self, eEffector)`
- `GetLookAtComponent(self)`
- `ConvertBoneAxisAndParent(self, kAxisMaps, kReParentMaps, kInsertBoneInfo, bIncludeDummyNode=True)`
- `ConvertToOriginalBoneAxis(self, bIncludeDummyNode=True, bIncludeMeshNode=True)`
- `AddClip(self, kTime)`
- `SampleMotionClip(self, spClip, bOptimize=True)`
- `FlattenMotionClip(self, spClip)`
- `BreakClip(self, kTime)`
- `MergeClips(self, spClip1, spClip2)`
- `MirrorClip(self, spClip)`
- `IsBoneAnimated(self, spBone)`
- `GetAllAnimationBone(self)`
- `ConvertToMotionBoneWorldTransforms(self)`
- `ConvertFramesToMotionBoneWorldTransforms(self, _from, to)`
- `BakeFkToIk(self, kTime, bAllClip)`
- `GetClipByTime(self, kHitTime)`
- `GetBoneTPosePosition(self, spBone)`
- `SetBoneTPosePosition(self, spBone, kPos)`
- `DeleteClip(self, spClip)`
- `GetBoneQniqueNames(self)`

#### RISky

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetVisible(self, kTime, bVisible)`
- `GetMaterialComponent(self)`
- `IsVisible(self, kTime)`

#### RISpotLight

**Inherits from:** `RILight`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetSpotLightBeam(self, kTime, fAngle, fFalloff, fAttenuation)`
- `GetSpotLightBeam(self, fAngle, fFalloff, fAttenuation)`
- `SetRange(self, kTime, fRange)`
- `GetRange(self)`
- `SetCastShadow(self, bEnable)`
- `IsCastShadow(self)`
- `SetDarkenShadowStrength(self, kTime, fStrength)`
- `GetDarkenShadowStrength(self)`
- `SetInverseSquare(self, b)`
- `GetInverseSquare(self)`
- `SetTransmission(self, b)`
- `GetTransmission(self)`
- `SetTubeShape(self, bTube)`
- `IsTubeShape(self)`
- `SetRectangleShape(self, bRectangle)`
- `IsRectangleShape(self)`
- `SetTubeLength(self, fLength)`
- `GetTubeLength(self)`
- `SetTubeRadius(self, radius)`
- `GetTubeRadius(self)`
- `SetTubeSoftRadius(self, softRadius)`
- `GetTubeSoftRadius(self)`
- `GetRectWidthHeight(self)`
- `SetRectWidthHeight(self, vWidthHeight)`
- `LoadRectTexture(self, strTexturePath)`
- `SaveRectTexture(self, strTexturePath)`
- `ClearRectTexture(self)`
- `LoadIes(self, strIesFilePath)`
- `SaveIes(self, strIesFilePath)`

#### RIStdMaterial

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetName(self)`
- `GetID(self)`
- `GetImage(self, eChannel)`
- `SetImage(self, strImage, eChannel)`
- `AddAmbientKey(self, kKey, kColor)`
- `AddDiffuseKey(self, kKey, kColor)`
- `GetAmbientColor(self)`
- `GetDiffuseColor(self)`
- `SetUseSRGB(self, eChannel, bSet)`
- `IsUseSRGB(self, eChannel)`

#### RIUnitObject

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `RebuildWall(self, *args)`
- `BuildWall(self, *args)`
- `GetWall(self, ePos)`
- `GetWalls(self)`
- `RemoveWall(self, spWall)`
- `GetActivatedPosition(self)`
- `GetPositionOfWall(self, spWall)`
- `SetWallActive(self, ePos, bActive)`

#### RIVisemeComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `AddVisemeOptionClip(self, kSmoothOption, kStartTick, strClipName)`
- `AddVisemeKey(self, kKey)`
- `AddVisemesClip(self, kTick, strClipName, kClipLength)`
- `ChangeTalkingStyle(self, pClip, strPresetName)`
- `RemoveVisemesClip(self, kTick)`
- `RemoveVisemesKey(self, kKey)`
- `GetVisemeMorphWeights(self)`
- `GetVisemeBones(self)`
- `GetVisemeKeys(self)`
- `GetVisemeKey(self, kTime, kKey)`
- `TextToSpeech(self, *args)`
- `TextToVisemeData(self, strContent, fVolume=100., fPitch=50., fSpeed=50.)`
- `GetStrength(self)`
- `LoadVocal(self, *args)`
- `GetClipCount(self)`
- `GetClip(self, uIndex)`
- `GetClipByTime(self, kHitTime)`
- `GetVisemeNames(self)`
- `GetWords(self, nClipIndex=-1)`
- `AddVisemesClipWithData(self, *args)`

#### RIVisualSettingComponent

**Inherits from:** `RIBase`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `SetIBLEnable(self, bEnable)`
- `IsIBLEnable(self)`
- `LoadIBLImage(self, strFilePath)`
- `IsIBLSyncSkyImage(self)`
- `SetIBLSyncSkyImage(self, bEnable)`
- `IsIBLSyncSkyOrientation(self)`
- `SetIBLSyncSkyOrientation(self, bEnable)`
- `SaveIBLImage(self, strFilePath)`
- `GetAmbientColor(self)`
- `SetAmbientColor(self, kColor)`

#### RIWallObject

**Inherits from:** `RIObject`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `ReplaceMaterial(self, strMaterialFilePath)`
- `BuildArchitectureElement(self, *args)`
- `CopyElementsFromWall(self, spWall)`
- `GetArchitectureElements(self)`

#### RImage

**Methods:**

- `CreateImage()`
- `SetGlobalPtr(pGlobalPtr)`
- `__init__(self)`

#### RImportExpressionSetting

**Methods:**

- `__init__(self)`
- `SetExpressionSource(self, kMeshFilePath)`
- `SetExpressionTarget(self, kMeshFilePath)`
- `SetWrinkleExpressionPart(self, eWrinkleExpression)`
- `GetExpressionSource(self)`
- `GetExpressionTarget(self)`
- `GetWrinkleExpressionPart(self)`

#### RInsertBoneInfo

**Methods:**

- `__init__(self)`
- `SetInfo(self, strParentName, strNewBoneName, strChildName)`
- `GetParentBoneName(self)`
- `GetNewBoneName(self)`
- `GetChildBoneName(self)`
- `__eq__(self, rhs)`

#### RKey

**Methods:**

- `__init__(self, *args)`
- `Clone(self)`
- `SetTime(self, kTick)`
- `GetTime(self)`
- `SetTransitionType(self, eTransitionType)`
- `GetTransitionType(self)`
- `SetTransitionStrength(self, fTransitionStrength)`
- `GetTransitionStrength(self)`

#### RMath

**Methods:**

- `ACos(fValue)`
- `ASin(fValue)`
- `ATan(fValue)`
- `ATan2(fY, fX)`
- `Cos(fValue)`
- `Exp(fValue)`
- `FAbs(fValue)`
- `FMod(fX, fY)`
- `InvSqrt(fValue)`
- `Log(fValue)`
- `Pow(fBase, fExponent)`
- `Sin(fValue)`
- `Sqr(fValue)`
- `Sqrt(fValue)`
- `Tan(fValue)`
- `Sign(fValue)`
- `CopySign(fValue)`
- `UnitRandom(*args)`
- `SymmetricRandom(*args)`
- `IntervalRandom(*args)`
- `FastSin0(fAngle)`
- `FastSin1(fAngle)`
- `FastCos0(fAngle)`
- `FastCos1(fAngle)`
- `FastTan0(fAngle)`
- `FastTan1(fAngle)`
- `FastInvSin(fValue)`
- `FastInvCos(fValue)`
- `FastInvTan0(fValue)`
- `FastInvTan1(fValue)`
- `FastInvSqrt_Walsh(tValue)`
- `FastSqrt_Walsh(tValue)`
- `FastSqrt_LogBase2(tValue)`
- `LogGamma(fX)`
- `Gamma(fX)`
- `IncompleteGamma(fA, fX)`
- `Erf(fX)`
- `Erfc(fX)`
- `ModBessel0(fX)`
- `ModBessel1(fX)`
- `Min(a, b)`
- `Max(a, b)`
- `Abs(a)`
- `Clamp(tMax, tMin, tValue)`
- `AlmostZero(*args)`
- `Equal(*args)`
- `RoundEpsilonZero(tValue)`
- `RoundAlmostZero(tValue)`
- `Round(tValue)`
- `Bezier3(a, b, c, d, t)`
- `__init__(self)`

#### RMatrix3

**Methods:**

- `__init__(self, *args)`
- `MakeIdentity(self)`
- `M(self, *args)`
- `E(self, *args)`
- `GetRow(self, nRow)`
- `GetColumn(self, nCol)`
- `__call__(self, *args)`
- `__eq__(self, mM)`
- `__ne__(self, mM)`
- `__lt__(self, mM)`
- `__gt__(self, mM)`
- `__ge__(self, mM)`
- `__le__(self, mM)`
- `__add__(self, mM)`
- `__sub__(self, mM)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__neg__(self)`
- `__iadd__(self, mM)`
- `__isub__(self, mM)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `Transpose(self)`
- `TransposeTimes(self, mM)`
- `TimesTranspose(self, mM)`
- `Inverse(self)`
- `Adjoint(self)`
- `AdjointTranspose(self)`
- `InverseTranspose(self)`
- `DiagonalElements(self)`
- `Determinant(self)`
- `MaxColumn(self)`
- `MaxRow(self)`
- `OneNorm(self)`
- `InfNorm(self)`
- `FromAxisAngle(self, rkAxis, fAngle)`
- `RotationX(self, fAngle)`
- `RotationY(self, fAngle)`
- `RotationZ(self, fAngle)`
- `AccuScale(self, rkScale)`
- `ToEulerAngle(self, *args)`
- `FromEulerAngle(Oreder, rx, ry, rz)`
- `FromSpereUnitVec(self, rkVec)`
- `IsRightHandCoordinate(self)`

#### RMatrix4

**Methods:**

- `__init__(self, *args)`
- `MakeIdentity(self)`
- `M(self, *args)`
- `E(self, *args)`
- `GetRow(self, nR)`
- `GetColumn(self, nC)`
- `__call__(self, *args)`
- `__eq__(self, mM)`
- `__ne__(self, mM)`
- `__lt__(self, mM)`
- `__gt__(self, mM)`
- `__ge__(self, mM)`
- `__le__(self, mM)`
- `__add__(self, mM)`
- `__sub__(self, mM)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__neg__(self)`
- `__iadd__(self, mM)`
- `__isub__(self, mM)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `Transpose(self)`
- `TransposeTimes(self, mM)`
- `TimesTranspose(self, mM)`
- `Inverse(self)`
- `Adjoint(self)`
- `AdjointTranspose(self)`
- `InverseTranspose(self)`
- `Determinant(self)`
- `MaxColumn(self)`
- `MaxRow(self)`
- `OneNorm(self)`
- `InfNorm(self)`
- `FromRTS(self, kRotate, kTranslate, kScale)`
- `GetSimpleRTS(self, rkRotate, rkTranslate, rkScale)`
- `GetSimpleRotate(self, rkRotate)`
- `SetTranslateZero(self)`
- `RotationX(self, fAngle)`
- `RotationY(self, fAngle)`
- `RotationZ(self, fAngle)`
- `RotateAxisAngle(self, rkAxis, fAngle)`
- `FromEulerAngle(self, Oreder, rx, ry, rz)`
- `SetSR(self, mSR)`
- `SetTranslate(self, vTranslate)`
- `GetSR(self)`
- `GetTranslate(self)`
- `AccuScale(self, rkScale)`
- `AccuRotate(self, rkRotate)`
- `AccuTranslate(self, rkTranslate)`
- `AlmostSame(self, kM, fThreshold)`

#### RMessageBoxButton

**Methods:**

- `__init__(self)`

#### RMorphSliderSetting

**Methods:**

- `__init__(self)`
- `SetMorphName(self, strMorphName)`
- `GetMorphName(self)`
- `SetCategory(self, eSetCategory)`
- `GetCategory(self)`
- `SetSliderPath(self, strSetSliderPath)`
- `GetSliderPath(self)`
- `SetMorphValueRange(self, fMin, fMax)`
- `GetMorphValueRange(self)`
- `SetSourceBaseType(self, eSourceBaseType)`
- `GetSourceBaseType(self)`
- `SetSourceFilePath(self, strSourceMorphPath)`
- `GetSourceFilePath(self)`
- `SetTargetFilePath(self, strTargetMorphPath)`
- `GetTargetFilePath(self)`
- `SetTargetMorphChecksumFilePath(self, strTargetMorphChecksumFilePath)`
- `GetTargetMorphChecksumFilePath(self)`
- `SetAxisSettingForObj(self, eAxisSettingForObj)`
- `GetAxisSettingForObj(self)`
- `SetAdjustBonesToFitMorph(self, bAdjustBonesToFitMorph)`
- `GetAdjustBonesToFitMorph(self)`
- `SetThumbNailFilePath(self, strThumdNailFilePath)`
- `GetThumbNailFilePath(self)`
- `SetAutoApplyToCurrentCharacter(self, bAutoApplyToCurrentCharacter)`
- `GetAutoApplyToCurrentCharacter(self)`

#### ROpenPoseKeyPointParam

**Methods:**

- `__init__(self)`

#### RPositionSetting

**Methods:**

- `__init__(self, *args)`
- `SetCoordinateSpace(self, eCoordinateSpace)`
- `GetCoordinateSpace(self)`
- `SetUnit(self, eUnit)`
- `GetUnit(self)`

#### RPropertyFloatMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### RPyTimer

**Methods:**

- `__init__(self)`
- `Start(self)`
- `Stop(self)`
- `IsRunning(self)`
- `SetSingleShot(self, bSingleShot)`
- `IsSingleShot(self)`
- `SetInterval(self, nMSec)`
- `GetInterval(self)`
- `RegisterPyTimerCallback(self, pCallback)`
- `UnregisterPyTimerCallback(self)`

#### RPyTimerCallback

**Inherits from:** `RCallback`

**Methods:**

- `__init__(self)`
- `Timeout(self)`
- `__disown__(self)`

#### RQuaternion

**Methods:**

- `__init__(self, *args)`
- `__call__(self, *args)`
- `X(self, *args)`
- `Y(self, *args)`
- `Z(self, *args)`
- `W(self, *args)`
- `SetX(self, tX)`
- `SetY(self, tY)`
- `SetZ(self, tZ)`
- `SetW(self, tW)`
- `__eq__(self, qQ)`
- `__ne__(self, qQ)`
- `__lt__(self, qQ)`
- `__le__(self, qQ)`
- `__gt__(self, qQ)`
- `__ge__(self, qQ)`
- `AlmostEqual(self, qQ)`
- `AlmostSame(self, qQ, tThreshold)`
- `__add__(self, qQ)`
- `__sub__(self, qQ)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__neg__(self)`
- `__iadd__(self, qQ)`
- `__isub__(self, qQ)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `FromRotationMatrix(self, rkRot)`
- `ToRotationMatrix(self)`
- `FromAxisAngle(self, rkAxis, fAngle)`
- `FindQuatBetweenHelper(A, B, NormAB)`
- `FindQuatBetweenInternal(An, Bn)`
- `FindQuatBetweenNormals(NormalA, NormalB)`
- `FindQuatBetweenVectors(VectorA, VectorB)`
- `ToAxisAngle(self, rkAxis, rfAngle)`
- `Dot(self, qQ)`
- `Inverse(self)`
- `Normalize(self)`
- `Conjugate(self)`
- `Rotate180(self)`
- `Multiply(self, qQ)`
- `MultiplyAssign(self, qQ)`
- `MultiplyVector(self, vPoint)`

#### RRangePair

**Methods:**

- `__init__(self, *args)`
- `__len__(self)`
- `__repr__(self)`
- `__getitem__(self, index)`
- `__setitem__(self, index, val)`

#### RReachKey

**Methods:**

- `__init__(self, *args)`
- `Clone(self)`
- `SetTime(self, kTime)`
- `GetTime(self)`
- `SetRotationActive(self, bRotateActive)`
- `GetRotationActive(self)`
- `SetForceReach(self, bPull)`
- `GetForceReach(self)`
- `SetTransitionRange(self, kForwardTransitionRange)`
- `GetTransitionRange(self)`
- `SetTargetObject(self, hTargetObject)`
- `GetTargetObject(self)`
- `SetKeyType(self, eKeyType)`
- `GetKeyType(self)`

#### RRgb

**Methods:**

- `__init__(self, *args)`
- `R(self, *args)`
- `G(self, *args)`
- `B(self, *args)`
- `Red(self)`
- `Green(self)`
- `Blue(self)`
- `From(self, r, g, b)`
- `FromXRGB(self, arg2)`
- `FromCOLORREF(self, arg2)`
- `ToXRGB(self)`
- `ToCOLORREF(self)`
- `ToVector3f(self)`
- `Normalize(self)`
- `Saturate(self)`
- `__iadd__(self, arg2)`
- `__isub__(self, arg2)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `__pos__(self)`
- `__neg__(self)`
- `__add__(self, arg2)`
- `__sub__(self, arg2)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__eq__(self, arg2)`
- `__ne__(self, arg2)`
- `__lt__(self, arg2)`

#### RRotationSetting

**Methods:**

- `__init__(self, *args)`
- `SetCoordinateSpace(self, eCoordinateSpace)`
- `GetCoordinateSpace(self)`
- `SetType(self, eType)`
- `GetType(self)`
- `SetUnit(self, eUnit)`
- `GetUnit(self)`
- `SetEulerOrder(self, eOrder)`
- `GetEulerOrder(self)`
- `SetQuaternionOrder(self, eOrder)`
- `GetQuaternionOrder(self)`

#### RSBuildingSettings

**Methods:**

- `__init__(self)`

#### RSUsdExportOption

**Methods:**

- `__init__(self)`

#### RSaveFacialAnimationOption

**Inherits from:** `RISaveFileOptionBase`

**Methods:**

- `SetFlag(self, eFlag)`
- `GetFlag(self)`
- `__init__(self)`

#### RSaveFileSetting

**Methods:**

- `__init__(self)`
- `SetSaveType(self, eType)`
- `GetSaveType(self)`
- `SetSaveRange(self, kStart, kEnd)`
- `SetSaveFileOption(self, pSaveFileOption)`
- `GetSaveRangeStart(self)`
- `GetSaveRangeEnd(self)`
- `GetSaveFileOption(self)`

#### RSaveMotionPlusOption

**Inherits from:** `RISaveFileOptionBase`

**Methods:**

- `SetMotionPlusOption(self, eDataOption)`
- `GetMotionPlusOption(self)`
- `SetMotionClipOption(self, eOption)`
- `GetMotionClipOption(self)`
- `SetSaveTimecode(self, bSaveTimecode)`
- `GetSaveTimecode(self)`
- `SetTimecodeStartTime(self, fTime)`
- `GetTimecodeStartTime(self)`
- `SetTimecodeFps(self, fFps)`
- `GetTimecodeFps(self)`
- `__init__(self)`

#### RSaveRangePair

**Methods:**

- `__init__(self, *args)`
- `__len__(self)`
- `__repr__(self)`
- `__getitem__(self, index)`
- `__setitem__(self, index, val)`

#### RScene

**Methods:**

- `GetSelectedObjects()`
- `GetAvatars(*args)`
- `GetProps()`
- `GetMDProps()`
- `GetBuildings()`
- `GetCameras()`
- `SelectObject(spObject)`
- `SelectObjects(kObjects)`
- `ClearSelectObjects()`
- `RemoveObject(spObject)`
- `FindObject(eType, strName)`
- `FindObjects(*args)`
- `FindChildObjects(spObject, eType, bAllLevel=True)`
- `Show(spObject)`
- `Hide(spObject)`
- `GetCurrentCamera()`
- `SetCurrentCamera(spCamera)`
- `GetSwitchCameraFrameIndexs(kFps)`
- `ClearSwitchCameraKeys()`
- `AddSwitchCameraKey(kSetTime, spCamera)`
- `GetRootNode()`
- `CreateCollection(strNewCollectionName)`
- `DeleteCollection(strCollectionName)`
- `MoveToCollection(*args)`
- `QueryObjectByID(strID)`
- `__init__(self)`

#### RStGenPackElementInfo

**Methods:**

- `__init__(self)`

#### RStGenPackFloorInfo

**Methods:**

- `__init__(self)`

#### RStGenPackMaterialInfo

**Methods:**

- `__init__(self)`

#### RStGenPackStyleInfo

**Methods:**

- `__init__(self)`

#### RStGenPackWallInfo

**Methods:**

- `__init__(self)`

#### RStatus

**Methods:**

- `__init__(self, *args)`
- `__eq__(self, *args)`
- `__ne__(self, *args)`
- `IsError(self)`
- `Clear(self)`
- `GetStatusCode(self)`
- `__nonzero__(self)`

#### RTcpCallback

**Inherits from:** `RCallback`

**Methods:**

- `__init__(self)`
- `OnStatusChanged(self, bIsConnected)`
- `OnDataReceived(self)`
- `OnFailMessageReceived(self, pErrorMsg)`
- `__disown__(self)`

#### RTcpClient

**Methods:**

- `__init__(self)`
- `Connect(self, strIP, uPort)`
- `Disconnect(self)`
- `IsConnected(self)`
- `GetDataSize(self, *args)`
- `GetData(self, pBuffer)`
- `GetDataAt(self, nIndex, pBuffer)`
- `SendData(self, pBuffer, nDataSize)`
- `SetMaximumDataCount(self, nCount)`
- `GetMaximumDataCount(self)`
- `GetDataCount(self)`
- `RegisterCallback(self, pCallback)`
- `UnregisterCallback(self)`

#### RTick

**Methods:**

- `Tps()`
- `Ms()`
- `Hns()`
- `FromSecond(*args)`
- `FromMilliSecond(*args)`
- `FromHns(*args)`
- `ToSecond(*args)`
- `ToMilliSecond(*args)`
- `__init__(self)`

#### RTime

**Methods:**

- `__init__(self)`
- `__eq__(self, kTime)`
- `__ne__(self, kTime)`
- `__gt__(self, kTime)`
- `__lt__(self, kTime)`
- `__ge__(self, kTime)`
- `__le__(self, kTime)`
- `__neg__(self)`
- `__add__(self, kTime)`
- `__sub__(self, kTime)`
- `__mod__(self, kTime)`
- `__isub__(self, kTime)`
- `__iadd__(self, kTime)`
- `ToInt(self)`
- `ToFloat(self)`
- `ToDouble(self)`
- `ToLong(self)`
- `ToUInt32(self)`
- `ToInt64(self)`
- `FromValue(tTick)`
- `__mul__(self, tTimes)`
- `__imul__(self, tTimes)`
- `__truediv__(self, *args)`
- `__itruediv__(self, *args)`

#### RTime2IntMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### RTransform

**Methods:**

- `__init__(self, *args)`
- `D(self, *args)`
- `S(self, *args)`
- `U(self, *args)`
- `R(self, *args)`
- `T(self, *args)`
- `__eq__(self, kRts)`
- `__ne__(self, kRts)`
- `__iadd__(self, kRts)`
- `__add__(self, kRts)`
- `AlmostEqual(self, kRts)`
- `AlmostSame(self, kRts, tThreshold)`
- `Inverse(self)`
- `From(self, mMatrix)`
- `Scale(self)`
- `Rotate(self)`
- `GetSR(self)`
- `Matrix(self)`
- `IsIdentity(self)`

#### RTransformControl

**Inherits from:** `RControl`

**Methods:**

- `__init__(self, *args, **kwargs)`
- `GetValue(self, kTick, kValue)`
- `SetValue(self, kTick, kValue)`
- `SetValueAt(self, uIndex, kValue)`
- `GetTransformKey(self, kTick, pKey)`
- `GetTransformKeyAt(self, uIndex, pKey)`
- `GetRotationOrder(self, eOrder)`
- `UpdateData(self)`

#### RTransformKey

**Inherits from:** `RKey`

**Methods:**

- `__init__(self, *args)`
- `Clone(self)`
- `SetTransform(self, kTransform)`
- `GetTransform(self)`

#### RUdpCallback

**Inherits from:** `RCallback`

**Methods:**

- `__init__(self)`
- `OnStatusChanged(self, bIsConnected)`
- `OnDataReceived(self)`
- `OnFailMessageReceived(self, pErrorMsg)`
- `__disown__(self)`

#### RUdpClient

**Methods:**

- `__init__(self)`
- `Connect(self, strIP, uPort)`
- `Disconnect(self)`
- `IsConnected(self)`
- `GetDataSize(self, *args)`
- `GetData(self, pBuffer)`
- `GetDataAt(self, nIndex, pBuffer)`
- `SendData(self, pBuffer, nDataSize, strIP, uPort)`
- `SetMaximumDataCount(self, nCount)`
- `GetMaximumDataCount(self)`
- `GetDataCount(self)`
- `JoinMulticastGroup(self, strIP)`
- `RegisterCallback(self, pCallback)`
- `UnregisterCallback(self)`

#### RUi

**Methods:**

- `GetMainWindow()`
- `AddMenu(*args)`
- `FindMenu(*args)`
- `RemoveMenu(pMenu)`
- `FindToolBar(strToolBarName)`
- `AddHotKey(strKeySequence)`
- `RemoveHotKey(pAction)`
- `GetResolutionType()`
- `GetCSSType()`
- `ShowMessageBox(*args)`
- `OpenFileDialog(*args)`
- `OpenFilesDialog(*args)`
- `SaveFileDialog(*args)`
- `CreateRDialog(*args)`
- `CreateRDockWidget()`
- `AddContextMenu(spObject, strText)`
- `RemoveContextMenu(spObject, pMenu)`
- `AddContextAction(spObject, strText)`
- `RemoveContextAction(spObject, pAction)`
- `LoadLuaUI(strFilePath)`
- `CallLuaFunction(strFilePath, strFunction, kParam, kReturn)`
- `ShowProgressDialog(bShow, bCancelable=False, bPauseRender=True)`
- `SetProgressStatusString(strStatus)`
- `PushProgress(fProgress)`
- `PopProgress()`
- `IsProgressCancel()`
- `__init__(self)`

#### RVariant

**Methods:**

- `__init__(self, *args)`
- `GetType(self)`
- `ToUInt32(self, pSucess=None)`
- `ToInt32(self, pSucess=None)`
- `ToFloat(self, pSucess=None)`
- `ToString(self, pSuccess=None)`
- `ToBool(self, pSuccess=None)`

#### RVector2

**Methods:**

- `__init__(self, *args)`
- `X(self, *args)`
- `Y(self, *args)`
- `SetX(self, tX)`
- `SetY(self, tY)`
- `__eq__(self, vV)`
- `__ne__(self, vV)`
- `__lt__(self, vV)`
- `__gt__(self, vV)`
- `__ge__(self, vV)`
- `__le__(self, vV)`
- `__add__(self, vV)`
- `__sub__(self, vV)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__neg__(self)`
- `__iadd__(self, vV)`
- `__isub__(self, vV)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `Length(self)`
- `SquaredLength(self)`
- `Dot(self, vV)`
- `Normalize(self)`
- `Inverse(self)`
- `Clear(self)`
- `AddWithWeight(self, vSrc, fWeight)`
- `AlmostZero(self)`
- `__getitem__(self, i)`

#### RVector3

**Methods:**

- `__init__(self, *args)`
- `X(self, *args)`
- `Y(self, *args)`
- `Z(self, *args)`
- `GetPosition(self, *args)`
- `SetXYZ(self, tX, tY, tZ)`
- `XY(self)`
- `SetX(self, tX)`
- `SetY(self, tY)`
- `SetZ(self, tZ)`
- `Clear(self)`
- `AddWithWeight(self, v, fWeight)`
- `__eq__(self, vV)`
- `__ne__(self, vV)`
- `__lt__(self, vV)`
- `__gt__(self, vV)`
- `__ge__(self, vV)`
- `__le__(self, vV)`
- `AlmostEqual(self, vV)`
- `__add__(self, vV)`
- `__sub__(self, vV)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__neg__(self)`
- `__iadd__(self, vV)`
- `__isub__(self, vV)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `Length(self)`
- `SquaredLength(self)`
- `Dot(self, vV)`
- `Normalize(self)`
- `NormalizeConst(self)`
- `Inverse(self)`
- `Distance(self, vV)`
- `SquaredDistance(self, vV)`
- `Cross(self, vV)`
- `Interpolate(self, vRatio, vV)`
- `AlmostZero(self)`
- `AlmostTheSame(self, vV)`
- `AlmostSame(self, vV, fThreshold)`
- `__getitem__(self, i)`

#### RVector4

**Methods:**

- `__init__(self, *args)`
- `X(self, *args)`
- `Y(self, *args)`
- `Z(self, *args)`
- `W(self, *args)`
- `XY(self)`
- `XYZ(self)`
- `SetX(self, tX)`
- `SetY(self, tY)`
- `SetZ(self, tZ)`
- `SetW(self, tW)`
- `__eq__(self, vV)`
- `__ne__(self, vV)`
- `__lt__(self, vV)`
- `__gt__(self, vV)`
- `__ge__(self, vV)`
- `__le__(self, vV)`
- `__add__(self, vV)`
- `__sub__(self, vV)`
- `__mul__(self, *args)`
- `__truediv__(self, *args)`
- `__neg__(self)`
- `__iadd__(self, vV)`
- `__isub__(self, vV)`
- `__imul__(self, *args)`
- `__itruediv__(self, *args)`
- `Length(self)`
- `SquaredLength(self)`
- `Dot(self, vV)`
- `Normalize(self)`
- `Inverse(self)`
- `AlmostZero(self)`
- `__getitem__(self, i)`

#### RVideo

**Methods:**

- `LoadMediaToTarget(strObjName, strFilePath, eAction, fTargetHeight=200.0)`
- `__init__(self)`

#### RVisemeKey

**Inherits from:** `RKey`

**Methods:**

- `__init__(self, *args)`
- `Clone(self)`
- `SetID(self, eID)`
- `GetID(self)`
- `SetWeight(self, fValue)`
- `GetWeight(self)`

#### RVisemeSmoothOption

**Methods:**

- `SetStrengthEnable(self, bJawEnable, bLipsEnable, bTongueEnable)`
- `SetStrengthValue(self, fJaw, fLips, fTongue)`
- `SetSmoothEnable(self, bJawEnable, bLipsEnable, bTongueEnable)`
- `SetSmoothValue(self, fJaw, fLips, fTongue)`
- `GetStrengthEnableSetting(self)`
- `GetSmoothEnableSetting(self)`
- `GetStrengthValueSetting(self)`
- `GetSmoothValueSetting(self)`
- `__init__(self)`

#### RWin32ApiKit

**Methods:**

- `FindWindowByTitleName(strTitleName)`
- `GetForegroundWindow()`
- `GetWindowName(pWnd)`
- `GetWindowThreadProcessId(pWnd)`
- `SendMessageToWindow(pWnd, strMsg)`
- `IsWindowVisible(pWnd)`
- `__init__(self)`

#### RWinMessageCallback

**Inherits from:** `RCallback`

**Methods:**

- `__init__(self)`
- `OnWinMsgReceieved(self, strMsg)`
- `__disown__(self)`

#### RWordData

**Methods:**

- `__init__(self)`

#### SwitchCameraFramePair

**Methods:**

- `__init__(self, *args)`
- `__len__(self)`
- `__repr__(self)`
- `__getitem__(self, index)`
- `__setitem__(self, index, val)`

#### SwitchCameraFramePairs

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__getslice__(self, i, j)`
- `__setslice__(self, *args)`
- `__delslice__(self, i, j)`
- `__delitem__(self, *args)`
- `__getitem__(self, *args)`
- `__setitem__(self, *args)`
- `pop(self)`
- `append(self, x)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `pop_back(self)`
- `erase(self, *args)`
- `__init__(self, *args)`
- `push_back(self, x)`
- `front(self)`
- `back(self)`
- `assign(self, n, x)`
- `resize(self, *args)`
- `insert(self, *args)`
- `reserve(self, n)`
- `capacity(self)`

#### WBoneQniqueNameMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### WStr2FloatMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### WStr2Matrix4fMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### WStrMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### WStrTransformMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### WStrTransformVectorMap

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__iter__(self)`
- `iterkeys(self)`
- `itervalues(self)`
- `iteritems(self)`
- `__getitem__(self, key)`
- `__delitem__(self, key)`
- `has_key(self, key)`
- `keys(self)`
- `values(self)`
- `items(self)`
- `__contains__(self, key)`
- `key_iterator(self)`
- `value_iterator(self)`
- `__setitem__(self, *args)`
- `asdict(self)`
- `__init__(self, *args)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `count(self, x)`
- `erase(self, *args)`
- `find(self, x)`
- `lower_bound(self, x)`
- `upper_bound(self, x)`

#### WallPosition

**Methods:**

- `iterator(self)`
- `__iter__(self)`
- `__nonzero__(self)`
- `__bool__(self)`
- `__len__(self)`
- `__getslice__(self, i, j)`
- `__setslice__(self, *args)`
- `__delslice__(self, i, j)`
- `__delitem__(self, *args)`
- `__getitem__(self, *args)`
- `__setitem__(self, *args)`
- `pop(self)`
- `append(self, x)`
- `empty(self)`
- `size(self)`
- `swap(self, v)`
- `begin(self)`
- `end(self)`
- `rbegin(self)`
- `rend(self)`
- `clear(self)`
- `get_allocator(self)`
- `pop_back(self)`
- `erase(self, *args)`
- `__init__(self, *args)`
- `push_back(self, x)`
- `front(self)`
- `back(self)`
- `assign(self, n, x)`
- `resize(self, *args)`
- `insert(self, *args)`
- `reserve(self, n)`
- `capacity(self)`

---

## Global Functions

### RApplication

- `RApplication_GetProductName()`
- `RApplication_GetProductEdition()`
- `RApplication_GetProductVersion()`
- `RApplication_GetProductMajorVersion()`
- `RApplication_GetProductMinorVersion()`
- `RApplication_GetApiVersion()`
- `RApplication_GetApiMajorVersion()`
- `RApplication_GetApiMinorVersion()`
- `RApplication_GetProgramPath()`
- `RApplication_GetDefaultProjectPath()`
- `RApplication_GetCurrentProjectPath()`
- `RApplication_GetTemplateDataPath()`
- `RApplication_GetCustomDataPath()`
- `RApplication_GetDefaultContentFolder(eFolderType)`
- `RApplication_GetContentFoldersInFolder(strFolder)`
- `RApplication_GetContentFilesInFolder(strFolder)`
- `RApplication_GetCustomContentFolder(eFolderType)`
- `RApplication_GetContentId(strFilePath)`

### RAudio

- `RAudio_CreateAudioObject()`
- `RAudio_LoadAudioToObject(*args)`

### RDataBlock

- `RDataBlock_Create(kAttributes)`

### REventHandler

- `REventHandler_SetListener(pListener)`
- `REventHandler_RegisterCallback(pCallback)`
- `REventHandler_UnregisterCallback(uId)`
- `REventHandler_UnregisterCallbacks(kIds)`

### RFileIO

- `RFileIO_LoadFile(*args)`
- `RFileIO_LoadFbxFile(*args)`
- `RFileIO_LoadClotheFromFbx(pAvatar, strFilePath, kFailedMeshList)`
- `RFileIO_LoadObject(strFilePath, bRecordStep=True)`
- `RFileIO_LoadAlembicFile(spObject, strFilePath, eUpAxis)`
- `RFileIO_ExportFbxFile(*args)`
- `RFileIO_IsCompatibleWithExportOption(spObject, kSetting)`
- `RFileIO_CheckExportFbxHasLicense(spObject)`
- `RFileIO_PreLoadMotion(strFilePath, spObject, kMotionLength)`
- `RFileIO_LoadMotion(strFilePath, kTime, spObject)`
- `RFileIO_SaveThumbnailToFile(strRLFile, strSaveTo)`
- `RFileIO_ExportObjFile(*args)`
- `RFileIO_LoadSubstancePainterTextures(spObject, strFolderPath)`
- `RFileIO_SaveProject(strSavePath)`
- `RFileIO_SaveFile(spObject, kSaveSetting, strSavePath)`
- `RFileIO_ExportGoZFile(kObjects, strFolderPath, kSetting)`
- `RFileIO_ExportMultiPoseGoZFile(kObjects, kFolderPaths, kSettings)`
- `RFileIO_GetTagsFromFileHeader(strFilePath, kTagList, eType)`
- `RFileIO_ExportBvhFile(spObject, strFilePath)`
- `RFileIO_ExportBvhFile2(*args)`
- `RFileIO_ConvertFbxFileToRLMotion(*args)`

### RGlobal

- `RGlobal_GetProjectLength()`
- `RGlobal_SetProjectLength(kLength)`
- `RGlobal_GetFps()`
- `RGlobal_GetPath(ePath, strPath)`
- `RGlobal_BeginAction(strAction, bBlockRecordUndo=False)`
- `RGlobal_EndAction()`
- `RGlobal_Undo()`
- `RGlobal_Redo()`
- `RGlobal_Play(kStart, kEnd)`
- `RGlobal_Pause()`
- `RGlobal_Stop()`
- `RGlobal_IsPlaying()`
- `RGlobal_GetTime()`
- `RGlobal_SetTime(kTime, bSendEvent=True)`
- `RGlobal_GetStartTime()`
- `RGlobal_GetEndTime()`
- `RGlobal_SetStartTime(kTime)`
- `RGlobal_SetEndTime(kTime)`
- `RGlobal_GetMocapManager()`
- `RGlobal_TrialVersionRemainingDays(strBinPath, uProductID, strProductFold, strRegRoot)`
- `RGlobal_DoSNVerification(nProductID, strRegistry, strProductName, strSNFailTitle, strSNFailMsg, strSNExceedTitle, strSNExceedMsg)`
- `RGlobal_DoBatchSNVerification(strJson)`
- `RGlobal_DoPluginTrialFollowUp(strProductNamePath, nPID)`
- `RGlobal_IsTrialContentMode()`
- `RGlobal_IsTrialVersion()`
- `RGlobal_RemoveAllAnimations(spObject)`
- `RGlobal_RenderVideo(*args)`
- `RGlobal_RenderAudio(*args)`
- `RGlobal_RenderVideoNormal(*args)`
- `RGlobal_RenderVideoDepth(*args)`
- `RGlobal_RenderVideoCanny(*args)`
- `RGlobal_RenderVideoOpenPoseKeyPoint(*args)`
- `RGlobal_RenderImageSequence(*args)`
- `RGlobal_RenderImageSequenceNormal(*args)`
- `RGlobal_RenderImageSequenceDepth(*args)`
- `RGlobal_RenderImageSequenceCanny(*args)`
- `RGlobal_RenderImageSequenceOpenPoseKeyPoint(*args)`
- `RGlobal_RenderImage(strOutputFileName)`
- `RGlobal_SetRenderExportType(kParams)`
- `RGlobal_GetRenderExportType()`
- `RGlobal_GetRenderExportImageParameter()`
- `RGlobal_GetRenderExportImageSequenceParameter()`
- `RGlobal_GetRenderExportVideoParameter()`
- `RGlobal_SetRenderExportParameter(*args)`
- `RGlobal_GetRenderExportAudioParameter()`
- `RGlobal_GetScreenSize(nWidth, nHeight)`
- `RGlobal_TrialVersionRemainingTimes(strBinPath, uProductID, strProductFold, strRegRoot, uTimeNo)`
- `RGlobal_TrialVersionIncreaseTimes(strBinPath, uProductID, strProductFold, strRegRoot, nCount=1)`
- `RGlobal_ObjectModified(spObject, eType)`
- `RGlobal_ObjectDataChanged2(spObject, eType)`
- `RGlobal_GetPreviewStartTime()`
- `RGlobal_GetPreviewEndTime()`
- `RGlobal_SetPreviewStartTime(kTime)`
- `RGlobal_SetPreviewEndTime(kTime)`
- `RGlobal_SetMotionSettingOptions(eOptions)`
- `RGlobal_GetMotionSettingOptions()`
- `RGlobal_GetVisualSettingComponent()`
- `RGlobal_RenderPreview(*args)`
- `RGlobal_RenderPreviewNormal(*args)`
- `RGlobal_RenderPreviewDepth(*args)`
- `RGlobal_RenderPreviewCanny(*args)`
- `RGlobal_RenderPreviewOpenPoseKeyPoint(*args)`
- `RGlobal_ForceViewportUpdate()`
- `RGlobal_GetMotionDirector()`
- `RGlobal_GetOmniConnectorManager()`
- `RGlobal_GetDialogMode()`
- `RGlobal_SetDialogMode(eMode)`
- `RGlobal_GetSilentMode()`
- `RGlobal_SetSilentMode(bSilent)`
- `RGlobal_SetViewSize(nWidth, nHeight)`
- `RGlobal_GetViewSize(nWidth, nHeight)`
- `RGlobal_EnablePixelStream(bEnable)`
- `RGlobal_CapturePixelStream()`
- `RGlobal_GetDefaultContentFileAbsolutePath(eContent, bCustom)`
- `RGlobal_SetTimecodeSource(eSource)`
- `RGlobal_SetTimecodeSourceData(eSource, strFormattedTime)`
- `RGlobal_GetTimecodeTime()`
- `RGlobal_SetViewportInfoMotionLiveDevice(*args)`
- `RGlobal_CheckTimecodePluginFeatureAllowed()`
- `RGlobal_CheckTimecodePluginTrialValid()`
- `RGlobal_CheckTimecodePluginFullOrTiralInstalled()`
- `RGlobal_IsPhysicsSimulationLoop()`
- `RGlobal_SetPhysicsSimulationLoop(bLoop)`
- `RGlobal_ShowMemberLoginDialog()`
- `RGlobal_AddInfoTips(pObjPtr, strImageSource, strFunctionName, strDescription, strVideoURLLinkcountId, strButtonText, strLearnMoreURL)`
- `RGlobal_SendLogToServer(*args)`

### RHeadshot

- `RHeadshot_CreateHeadFromPhoto(strPhotoPath, eMode, kOption)`
- `RHeadshot_ImportHeadFromObj(*args)`

### RIBuildingGeneratorObject

- `RIBuildingGeneratorObject_GenerateBuilding(kSettings, kInfo)`
- `RIBuildingGeneratorObject_IsBuildingRoot(spObject)`
- `RIBuildingGeneratorObject_IsFloor(spObject)`
- `RIBuildingGeneratorObject_IsUnit(spObject)`
- `RIBuildingGeneratorObject_IsWall(spObject)`
- `RIBuildingGeneratorObject_GetBuildingRoot(spObject)`
- `RIBuildingGeneratorObject_GetFloorByChild(spObject)`
- `RIBuildingGeneratorObject_GetUnitByChild(spObject)`

### RImage

- `RImage_CreateImage()`
- `RImage_SetGlobalPtr(pGlobalPtr)`

### RMath

- `RMath_ACos(fValue)`
- `RMath_ASin(fValue)`
- `RMath_ATan(fValue)`
- `RMath_ATan2(fY, fX)`
- `RMath_Cos(fValue)`
- `RMath_Exp(fValue)`
- `RMath_FAbs(fValue)`
- `RMath_FMod(fX, fY)`
- `RMath_InvSqrt(fValue)`
- `RMath_Log(fValue)`
- `RMath_Pow(fBase, fExponent)`
- `RMath_Sin(fValue)`
- `RMath_Sqr(fValue)`
- `RMath_Sqrt(fValue)`
- `RMath_Tan(fValue)`
- `RMath_Sign(fValue)`
- `RMath_CopySign(fValue)`
- `RMath_UnitRandom(*args)`
- `RMath_SymmetricRandom(*args)`
- `RMath_IntervalRandom(*args)`
- `RMath_FastSin0(fAngle)`
- `RMath_FastSin1(fAngle)`
- `RMath_FastCos0(fAngle)`
- `RMath_FastCos1(fAngle)`
- `RMath_FastTan0(fAngle)`
- `RMath_FastTan1(fAngle)`
- `RMath_FastInvSin(fValue)`
- `RMath_FastInvCos(fValue)`
- `RMath_FastInvTan0(fValue)`
- `RMath_FastInvTan1(fValue)`
- `RMath_FastInvSqrt_Walsh(tValue)`
- `RMath_FastSqrt_Walsh(tValue)`
- `RMath_FastSqrt_LogBase2(tValue)`
- `RMath_LogGamma(fX)`
- `RMath_Gamma(fX)`
- `RMath_IncompleteGamma(fA, fX)`
- `RMath_Erf(fX)`
- `RMath_Erfc(fX)`
- `RMath_ModBessel0(fX)`
- `RMath_ModBessel1(fX)`
- `RMath_Min(a, b)`
- `RMath_Max(a, b)`
- `RMath_Abs(a)`
- `RMath_Clamp(tMax, tMin, tValue)`
- `RMath_AlmostZero(*args)`
- `RMath_Equal(*args)`
- `RMath_RoundEpsilonZero(tValue)`
- `RMath_RoundAlmostZero(tValue)`
- `RMath_Round(tValue)`
- `RMath_Bezier3(a, b, c, d, t)`

### RMatrix3

- `RMatrix3_FromEulerAngle(Oreder, rx, ry, rz)`

### RQuaternion

- `RQuaternion_FindQuatBetweenHelper(A, B, NormAB)`
- `RQuaternion_FindQuatBetweenInternal(An, Bn)`
- `RQuaternion_FindQuatBetweenNormals(NormalA, NormalB)`
- `RQuaternion_FindQuatBetweenVectors(VectorA, VectorB)`

### RScene

- `RScene_GetSelectedObjects()`
- `RScene_GetAvatars(*args)`
- `RScene_GetProps()`
- `RScene_GetMDProps()`
- `RScene_GetBuildings()`
- `RScene_GetCameras()`
- `RScene_SelectObject(spObject)`
- `RScene_SelectObjects(kObjects)`
- `RScene_ClearSelectObjects()`
- `RScene_RemoveObject(spObject)`
- `RScene_FindObject(eType, strName)`
- `RScene_FindObjects(*args)`
- `RScene_FindChildObjects(spObject, eType, bAllLevel=True)`
- `RScene_Show(spObject)`
- `RScene_Hide(spObject)`
- `RScene_GetCurrentCamera()`
- `RScene_SetCurrentCamera(spCamera)`
- `RScene_GetSwitchCameraFrameIndexs(kFps)`
- `RScene_ClearSwitchCameraKeys()`
- `RScene_AddSwitchCameraKey(kSetTime, spCamera)`
- `RScene_GetRootNode()`
- `RScene_CreateCollection(strNewCollectionName)`
- `RScene_DeleteCollection(strCollectionName)`
- `RScene_MoveToCollection(*args)`
- `RScene_QueryObjectByID(strID)`

### RStatus

- `RStatus_eq_cs(eCode, kStatus)`
- `RStatus_ne_cs(eCode, kStatus)`

### RTick

- `RTick_Tps()`
- `RTick_Ms()`
- `RTick_Hns()`
- `RTick_FromSecond(*args)`
- `RTick_FromMilliSecond(*args)`
- `RTick_FromHns(*args)`
- `RTick_ToSecond(*args)`
- `RTick_ToMilliSecond(*args)`

### RTime

- `RTime_FromValue(tTick)`

### RUi

- `RUi_GetMainWindow()`
- `RUi_AddMenu(*args)`
- `RUi_FindMenu(*args)`
- `RUi_RemoveMenu(pMenu)`
- `RUi_FindToolBar(strToolBarName)`
- `RUi_AddHotKey(strKeySequence)`
- `RUi_RemoveHotKey(pAction)`
- `RUi_GetResolutionType()`
- `RUi_GetCSSType()`
- `RUi_ShowMessageBox(*args)`
- `RUi_OpenFileDialog(*args)`
- `RUi_OpenFilesDialog(*args)`
- `RUi_SaveFileDialog(*args)`
- `RUi_CreateRDialog(*args)`
- `RUi_CreateRDockWidget()`
- `RUi_AddContextMenu(spObject, strText)`
- `RUi_RemoveContextMenu(spObject, pMenu)`
- `RUi_AddContextAction(spObject, strText)`
- `RUi_RemoveContextAction(spObject, pAction)`
- `RUi_LoadLuaUI(strFilePath)`
- `RUi_CallLuaFunction(strFilePath, strFunction, kParam, kReturn)`
- `RUi_ShowProgressDialog(bShow, bCancelable=False, bPauseRender=True)`
- `RUi_SetProgressStatusString(strStatus)`
- `RUi_PushProgress(fProgress)`
- `RUi_PopProgress()`
- `RUi_IsProgressCancel()`

### RVideo

- `RVideo_LoadMediaToTarget(strObjName, strFilePath, eAction, fTargetHeight=200.0)`

### RWin32ApiKit

- `RWin32ApiKit_FindWindowByTitleName(strTitleName)`
- `RWin32ApiKit_GetForegroundWindow()`
- `RWin32ApiKit_GetWindowName(pWnd)`
- `RWin32ApiKit_GetWindowThreadProcessId(pWnd)`
- `RWin32ApiKit_SendMessageToWindow(pWnd, strMsg)`
- `RWin32ApiKit_IsWindowVisible(pWnd)`

### Other Functions

- `FastInvSqrt_Walsh_Imp(*args)`
- `FastSqrt_LogBase2_Imp(*args)`
- `CanDoSmoothCameraInterpolate(kT0, kT1)`
- `SmoothCameraTransformInterpolate(kT0, kT1, fRatio, kRts, vCameraUp, vCameraDir)`
- `__mul__(*args)`
- `__eq__(*args)`
- `__ne__(*args)`
- `__lt__(*args)`
- `Saturate(*args)`
- `abs(kTime)`
- `GetFrameIndex(kTime, kFps)`
- `GetFrameTime(kTime, kFps)`
- `IndexedFrameTime(nFrameIndex, kFps)`
- `__or__(*args)`
- `__and__(*args)`
- `__xor__(*args)`
- `BitCheck(*args)`
- `BitRemove(*args)`
- `BitInverse(*args)`
