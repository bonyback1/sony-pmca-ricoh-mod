import glob
import math
import os
import sys

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

def pts_to_bytes(pts):
    b = bytearray()
    for v in pts:
        b.append(v & 0xff)
        b.append((v >> 8) & 0xff)
    return b

def make_filmic_curve(slope=1.2, toe_lift=0, shoulder_max=1023, center=0.5, ev_offset=0.0):
    factor = math.pow(2.0, ev_offset)
    pts = []
    for i in range(1024):
        # Linear exposure scaling baked directly into tone curve
        t_raw = (i / 1023.0) * factor
        t = min(1.0, max(0.0, t_raw))
        if t < center:
            norm_t = t / center
            val = math.pow(norm_t, slope) * center
        else:
            norm_t = (1.0 - t) / (1.0 - center)
            val = 1.0 - math.pow(norm_t, slope) * (1.0 - center)
        scaled = toe_lift + val * (shoulder_max - toe_lift)
        pts.append(max(0, min(1023, round(scaled))))
    return pts

def gen_curve_pos():
    # Decomposed from authentic GR3-P-V3 Plady.cube
    cube_path = os.path.join(os.path.dirname(__file__), "..", "GR3-P-V3 Plady.cube")
    if os.path.exists(cube_path):
        from tools.color_bench.decompose_cube import decompose_cube
        return decompose_cube(cube_path)["gamma_1024"]
    return make_filmic_curve(slope=1.25, toe_lift=4, shoulder_max=1020, center=0.48, ev_offset=-0.33)

def gen_curve_neg():
    # Decomposed from authentic GR3-N-V3 Plady.cube
    cube_path = os.path.join(os.path.dirname(__file__), "..", "GR3-N-V3 Plady.cube")
    if os.path.exists(cube_path):
        from tools.color_bench.decompose_cube import decompose_cube
        return decompose_cube(cube_path)["gamma_1024"]
    return make_filmic_curve(slope=1.08, toe_lift=36, shoulder_max=985, center=0.50, ev_offset=0.33)

def gen_curve_hcbw():
    # Ricoh High Contrast B&W: punchy contrast (slope=1.85), deep rich blacks preserving dark textures
    return make_filmic_curve(slope=1.85, toe_lift=0, shoulder_max=1023, center=0.50, ev_offset=0.0)

def gen_curve_daido():
    # Moriyama Daido: gritty, high-contrast graphic street B&W (slope=2.38), -0.33 EV baked in
    return make_filmic_curve(slope=2.38, toe_lift=0, shoulder_max=1023, center=0.50, ev_offset=-0.33)

def gen_curve_xpro():
    # Decomposed directly from authentic Leica_SteveMcCurry.cube
    cube_path = os.path.join(os.path.dirname(__file__), "..", "Leica_SteveMcCurry.cube")
    if os.path.exists(cube_path):
        from tools.color_bench.decompose_cube import decompose_cube
        return decompose_cube(cube_path)["gamma_1024"]
    return make_filmic_curve(slope=1.35, toe_lift=0, shoulder_max=1020, center=0.46, ev_offset=0.0)

curves = {
    'pos': pts_to_bytes(gen_curve_pos()),
    'neg': pts_to_bytes(gen_curve_neg()),
    'hcbw': pts_to_bytes(gen_curve_hcbw()),
    'daido': pts_to_bytes(gen_curve_daido()),
    'xpro': pts_to_bytes(gen_curve_xpro()),
}

def format_array_data(data):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'0x{b:02x}t' for b in chunk)
        lines.append(f'        {hex_str}')
    return '\n'.join(lines)

smali_content = f'''.class public Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;
.super Ljava/lang/Object;
.source "RicohHook.java"

# static fields
.field private static final TAG:Ljava/lang/String; = "RicohHook"

.field private static sIsRicohActive:Z
.field private static sAppliedPreset:Ljava/lang/String;
.field private static sAppliedCameraHash:I
.field private static sCachedLocale:Ljava/util/Locale;
.field private static sCachedLangType:I
.field private static sBypassOriginal:Z
.field private static sActivePreset:Ljava/lang/String;
.field private static sCompareBadge:Landroid/widget/TextView;
.field private static sOriginalLB:I
.field private static sOriginalCC:I
.field private static sHasSavedOriginalWB:Z

.field private static sOriginalColorMode:Ljava/lang/String;
.field private static sHasSavedOriginalColorMode:Z
.field private static sOriginalContrast:I
.field private static sOriginalSaturation:I
.field private static sOriginalSharpness:I
.field private static sHasSavedOriginalTone:Z
.field private static sOriginalDRO:Ljava/lang/String;
.field private static sHasSavedOriginalDRO:Z
.field private static sOriginalHDR:Ljava/lang/String;
.field private static sHasSavedOriginalHDR:Z

.field private static sGammaPos:[B
.field private static sGammaNeg:[B
.field private static sGammaHcbw:[B
.field private static sGammaDaido:[B
.field private static sGammaXpro:[B

.field public static final sPositiveFilmMatrix:[I
.field public static final sNegativeFilmMatrix:[I
.field public static final sHighContrastBwMatrix:[I
.field public static final sMoriyamaMatrix:[I
.field public static final sCrossProcessMatrix:[I
.field public static final sIdentityMatrix:[I
.field public static final sEmptyIntArray:[I


# direct methods
.method static constructor <clinit>()V
    .locals 2

    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedPreset:Ljava/lang/String;
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedCameraHash:I
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCachedLocale:Ljava/util/Locale;
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCachedLangType:I
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sActivePreset:Ljava/lang/String;
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z

    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalColorMode:Ljava/lang/String;
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalColorMode:Z
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalContrast:I
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalSaturation:I
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalSharpness:I
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalTone:Z
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalDRO:Ljava/lang/String;
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalDRO:Z
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalHDR:Ljava/lang/String;
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalHDR:Z

    new-array v1, v0, [I
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sEmptyIntArray:[I

    const/4 v0, 0x0
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaPos:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaNeg:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaHcbw:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaDaido:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaXpro:[B

    const/16 v0, 0x9

    # 1. Positive Film Matrix (991, 203, -170, -21, 1059, -14, 48, 260, 716)
    new-array v1, v0, [I
    fill-array-data v1, :array_pos_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sPositiveFilmMatrix:[I

    # 2. Negative Film Matrix (848, -54, 230, 169, 641, 214, 66, 278, 680)
    new-array v1, v0, [I
    fill-array-data v1, :array_neg_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sNegativeFilmMatrix:[I

    # 3. High Contrast B&W Matrix
    new-array v1, v0, [I
    fill-array-data v1, :array_hcbw_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHighContrastBwMatrix:[I

    # 4. Moriyama Daido Matrix
    new-array v1, v0, [I
    fill-array-data v1, :array_daido_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sMoriyamaMatrix:[I

    # 5. Leica Steve McCurry Matrix (1118, -62, -32, -23, 1070, -23, -45, -29, 1098)
    new-array v1, v0, [I
    fill-array-data v1, :array_xpro_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCrossProcessMatrix:[I

    # Identity Matrix
    new-array v0, v0, [I
    fill-array-data v0, :array_id_matrix
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIdentityMatrix:[I

    return-void

    :array_pos_matrix
    .array-data 4
        0x3df
        0xcb
        -0xaa
        -0x15
        0x423
        -0xe
        0x30
        0x104
        0x2cc
    .end array-data

    :array_neg_matrix
    .array-data 4
        0x350
        -0x36
        0xe6
        0xa9
        0x281
        0xd6
        0x42
        0x116
        0x2a8
    .end array-data

    :array_hcbw_matrix
    .array-data 4
        0x114
        0x279
        0x73
        0x114
        0x279
        0x73
        0x114
        0x279
        0x73
    .end array-data

    :array_daido_matrix
    .array-data 4
        0x271
        0x182
        0xd
        0x271
        0x182
        0xd
        0x271
        0x182
        0xd
    .end array-data

    :array_xpro_matrix
    .array-data 4
        0x45e
        -0x3e
        -0x20
        -0x17
        0x42e
        -0x17
        -0x2d
        -0x1d
        0x44a
    .end array-data

    :array_id_matrix
    .array-data 4
        0x400
        0x0
        0x0
        0x0
        0x400
        0x0
        0x0
        0x0
        0x400
    .end array-data
.end method

.method public constructor <init>()V
    .locals 0

    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static getCameraSetting(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    .locals 3

    const/4 v0, 0x0
    if-eqz p0, :cond_0

    :try_start_0
    invoke-virtual {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getCameraSetting()Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v0
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :catch_0

    if-eqz v0, :cond_0
    return-object v0

    :catch_0
    move-exception v1
    const-string v1, "RicohHook"
    const-string v2, "controller.getCameraSetting failed"
    invoke-static {{v1, v2}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :cond_0
    :try_start_1
    invoke-static {{}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getInstance()Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v0
    :try_end_1
    .catch Ljava/lang/Throwable; {{:try_start_1 .. :try_end_1}} :catch_1

    return-object v0

    :catch_1
    move-exception v0
    const-string v1, "RicohHook"
    const-string v2, "CameraSetting.getInstance failed"
    invoke-static {{v1, v2}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I
    const/4 v0, 0x0
    return-object v0
.end method

.method public static getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    .locals 3

    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraSetting(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v0
    const/4 v1, 0x0
    if-eqz v0, :cond_0

    :try_start_0
    invoke-virtual {{v0}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getCamera()Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v1
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :catch_0

    return-object v1

    :catch_0
    move-exception v0
    const-string v2, "RicohHook"
    invoke-virtual {{v0}}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
    move-result-object v0
    invoke-static {{v2, v0}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :cond_0
    return-object v1
.end method

.method public static isRicohPreset(Ljava/lang/String;)Z
    .locals 1

    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getRGBMatrix(Ljava/lang/String;)[I
    move-result-object v0
    if-eqz v0, :cond_not_ricoh

    const/4 v0, 0x1
    return v0

    :cond_not_ricoh
    const/4 v0, 0x0
    return v0
.end method

.method public static getRGBMatrix(Ljava/lang/String;)[I
    .locals 2

    const-string v0, "pop-color"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_1

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sPositiveFilmMatrix:[I
    return-object v0

    :cond_1
    const-string v0, "retro-photo"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_2

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sNegativeFilmMatrix:[I
    return-object v0

    :cond_2
    const-string v0, "richtone-mono"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_3

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHighContrastBwMatrix:[I
    return-object v0

    :cond_3
    const-string v0, "rough-mono"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_4

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sMoriyamaMatrix:[I
    return-object v0

    :cond_4
    const-string v0, "watercolor"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_5

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCrossProcessMatrix:[I
    return-object v0

    :cond_5
    const/4 v0, 0x0
    return-object v0
.end method

.method public static getGammaBytes(Ljava/lang/String;)[B
    .locals 2

    const-string v0, "pop-color"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_1

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaPos:[B
    if-nez v0, :cond_0
    const/16 v0, 0x800
    new-array v0, v0, [B
    fill-array-data v0, :array_gamma_pos
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaPos:[B
    :cond_0
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaPos:[B
    return-object v0

    :cond_1
    const-string v0, "retro-photo"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_3

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaNeg:[B
    if-nez v0, :cond_2
    const/16 v0, 0x800
    new-array v0, v0, [B
    fill-array-data v0, :array_gamma_neg
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaNeg:[B
    :cond_2
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaNeg:[B
    return-object v0

    :cond_3
    const-string v0, "richtone-mono"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_5

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaHcbw:[B
    if-nez v0, :cond_4
    const/16 v0, 0x800
    new-array v0, v0, [B
    fill-array-data v0, :array_gamma_hcbw
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaHcbw:[B
    :cond_4
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaHcbw:[B
    return-object v0

    :cond_5
    const-string v0, "rough-mono"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_7

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaDaido:[B
    if-nez v0, :cond_6
    const/16 v0, 0x800
    new-array v0, v0, [B
    fill-array-data v0, :array_gamma_daido
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaDaido:[B
    :cond_6
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaDaido:[B
    return-object v0

    :cond_7
    const-string v0, "watercolor"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_9

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaXpro:[B
    if-nez v0, :cond_8
    const/16 v0, 0x800
    new-array v0, v0, [B
    fill-array-data v0, :array_gamma_xpro
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaXpro:[B
    :cond_8
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaXpro:[B
    return-object v0

    :cond_9
    const/4 v0, 0x0
    return-object v0

    :array_gamma_pos
    .array-data 1
{format_array_data(curves['pos'])}
    .end array-data

    :array_gamma_neg
    .array-data 1
{format_array_data(curves['neg'])}
    .end array-data

    :array_gamma_hcbw
    .array-data 1
{format_array_data(curves['hcbw'])}
    .end array-data

    :array_gamma_daido
    .array-data 1
{format_array_data(curves['daido'])}
    .end array-data

    :array_gamma_xpro
    .array-data 1
{format_array_data(curves['xpro'])}
    .end array-data
.end method

.method public static getWhitebalanceShiftLB(Ljava/lang/String;)I
    .locals 1

    const-string v0, "pop-color"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_neg
    const/4 v0, 0x0
    return v0

    :cond_neg
    const-string v0, "retro-photo"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_xpro
    const/4 v0, 0x2
    return v0

    :cond_xpro
    const-string v0, "watercolor"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_zero
    const/4 v0, 0x0
    return v0

    :cond_zero
    const/4 v0, 0x0
    return v0
.end method

.method public static getWhitebalanceShiftCC(Ljava/lang/String;)I
    .locals 1

    const-string v0, "pop-color"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_neg
    const/4 v0, 0x0
    return v0

    :cond_neg
    const-string v0, "retro-photo"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_xpro
    const/4 v0, 0x0
    return v0

    :cond_xpro
    const-string v0, "watercolor"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_zero
    const/4 v0, 0x0
    return v0

    :cond_zero
    const/4 v0, 0x0
    return v0
.end method

.method public static applyHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;Ljava/lang/String;)Z
    .locals 6
    .annotation system Ldalvik/annotation/Signature;
        value = {{
            "(",
            "Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;",
            "Landroid/util/Pair<",
            "Landroid/hardware/Camera$Parameters;",
            "Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;",
            ">;",
            "Ljava/lang/String;",
            ")Z"
        }}
    .end annotation

    const/4 v0, 0x0

    # Safety check: input parameter
    if-nez p2, :cond_check_matrix
    return v0

    :cond_check_matrix
    invoke-static {{p2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getRGBMatrix(Ljava/lang/String;)[I
    move-result-object v3
    if-nez v3, :cond_0
    return v0

    :cond_0
    # If currently bypassing for Before/After comparison, exit bypass mode cleanly
    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    if-eqz v0, :cond_not_bypass
    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    invoke-static {{v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->updateCompareBadgeVisibility(Z)V

    :cond_not_bypass
    const/4 v0, 0x0
    # Fast-path deduplication: skip redundant HAL/DMA commits if same preset is already active on same CameraEx
    sget-boolean v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    if-eqz v1, :cond_not_cached

    sget-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedPreset:Ljava/lang/String;
    if-eqz v1, :cond_not_cached

    invoke-virtual {{v1, p2}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-eqz v1, :cond_not_cached

    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v1
    if-eqz v1, :cond_not_cached

    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedCameraHash:I
    if-eqz v2, :cond_not_cached

    invoke-static {{v1}}, Ljava/lang/System;->identityHashCode(Ljava/lang/Object;)I
    move-result v1
    if-ne v1, v2, :cond_not_cached

    const/4 v0, 0x1
    return v0

    :cond_not_cached
    # Safe logging
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {{v1}}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "Applying Ricoh preset for: "
    invoke-virtual {{v1, v2}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v1
    invoke-virtual {{v1, p2}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v1
    invoke-virtual {{v1}}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    const-string v2, "RicohHook"
    invoke-static {{v2, v1}}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraSetting(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v1
    if-nez v1, :cond_1
    return v0

    :cond_1
    if-nez p1, :cond_2
    invoke-virtual {{v1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getEmptyParameters()Landroid/util/Pair;
    move-result-object p1

    :cond_2
    if-nez p1, :cond_3
    return v0

    :cond_3
    # 1. Turn off native effect and Partial Color extraction mode to avoid hardware B&W lock
    iget-object v2, p1, Landroid/util/Pair;->second:Ljava/lang/Object;
    check-cast v2, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;
    if-eqz v2, :cond_4
    const-string v4, "off"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setPictureEffect(Ljava/lang/String;)V

    :try_start_csm_apply
    const-string v4, "off"
    sput-object v4, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mMode:Ljava/lang/String;
    sget-object v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sEmptyIntArray:[I
    sput-object v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mEnabledCh:[I
    invoke-virtual {{v2, v4, v5}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorSelectMode(Ljava/lang/String;[I)V
    :try_end_csm_apply
    .catch Ljava/lang/Throwable; {{:try_start_csm_apply .. :try_end_csm_apply}} :catch_csm_apply
    goto :goto_csm_apply_done

    :catch_csm_apply
    move-exception v4

    :goto_csm_apply_done
    # Fetch live ParametersModifier once, then back up each group in an independent try/catch
    const/4 v4, 0x0
    :try_start_live_params
    invoke-virtual {{v1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getParameters()Landroid/util/Pair;
    move-result-object v5
    if-eqz v5, :goto_live_params_done

    iget-object v5, v5, Landroid/util/Pair;->second:Ljava/lang/Object;
    check-cast v5, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;
    move-object v4, v5
    :try_end_live_params
    .catch Ljava/lang/Throwable; {{:try_start_live_params .. :try_end_live_params}} :catch_live_params
    goto :goto_live_params_done

    :catch_live_params
    move-exception v5
    const/4 v4, 0x0

    :goto_live_params_done
    if-eqz v4, :cond_backups_done

    # 1a. Backup Creative Style ColorMode
    sget-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalColorMode:Z
    if-nez v5, :cond_bk_cm_done

    :try_start_bk_cm
    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getColorMode()Ljava/lang/String;
    move-result-object v5
    sput-object v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalColorMode:Ljava/lang/String;
    const/4 v5, 0x1
    sput-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalColorMode:Z
    :try_end_bk_cm
    .catch Ljava/lang/Throwable; {{:try_start_bk_cm .. :try_end_bk_cm}} :catch_bk_cm
    goto :goto_bk_cm_done

    :catch_bk_cm
    move-exception v5

    :cond_bk_cm_done
    :goto_bk_cm_done
    # 1b. Backup Contrast, Saturation, Sharpness
    sget-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalTone:Z
    if-nez v5, :cond_bk_tone_done

    :try_start_bk_tone
    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getContrast()I
    move-result v5
    sput v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalContrast:I

    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getSaturation()I
    move-result v5
    sput v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalSaturation:I

    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getSharpness()I
    move-result v5
    sput v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalSharpness:I

    const/4 v5, 0x1
    sput-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalTone:Z
    :try_end_bk_tone
    .catch Ljava/lang/Throwable; {{:try_start_bk_tone .. :try_end_bk_tone}} :catch_bk_tone
    goto :goto_bk_tone_done

    :catch_bk_tone
    move-exception v5

    :cond_bk_tone_done
    :goto_bk_tone_done
    # 1c. Backup DRO Mode
    sget-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalDRO:Z
    if-nez v5, :cond_bk_dro_done

    :try_start_bk_dro
    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getDROMode()Ljava/lang/String;
    move-result-object v5
    sput-object v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalDRO:Ljava/lang/String;
    const/4 v5, 0x1
    sput-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalDRO:Z
    :try_end_bk_dro
    .catch Ljava/lang/Throwable; {{:try_start_bk_dro .. :try_end_bk_dro}} :catch_bk_dro
    goto :goto_bk_dro_done

    :catch_bk_dro
    move-exception v5

    :cond_bk_dro_done
    :goto_bk_dro_done
    # 1d. Backup HDR Mode
    sget-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalHDR:Z
    if-nez v5, :cond_bk_hdr_done

    :try_start_bk_hdr
    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getHDRMode()Ljava/lang/String;
    move-result-object v5
    sput-object v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalHDR:Ljava/lang/String;
    const/4 v5, 0x1
    sput-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalHDR:Z
    :try_end_bk_hdr
    .catch Ljava/lang/Throwable; {{:try_start_bk_hdr .. :try_end_bk_hdr}} :catch_bk_hdr
    goto :goto_bk_hdr_done

    :catch_bk_hdr
    move-exception v5

    :cond_bk_hdr_done
    :goto_bk_hdr_done
    # 1e. Backup original user WB shifts
    sget-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    if-nez v5, :cond_bk_wb_done

    :try_start_bk_wb
    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getLightBalanceForWhiteBalance()I
    move-result v5
    sput v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I

    invoke-virtual {{v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getColorCompensationForWhiteBalance()I
    move-result v5
    sput v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I

    const/4 v5, 0x1
    sput-boolean v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    :try_end_bk_wb
    .catch Ljava/lang/Throwable; {{:try_start_bk_wb .. :try_end_bk_wb}} :catch_bk_wb
    goto :goto_bk_wb_done

    :catch_bk_wb
    move-exception v5

    :cond_bk_wb_done
    :goto_bk_wb_done
    :cond_backups_done

    # Neutralize Tone, ColorMode, DRO, HDR independently on target modifier v2
    :try_start_tone_set
    const/4 v4, 0x0
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setContrast(I)V
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSaturation(I)V
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSharpness(I)V
    :try_end_tone_set
    .catch Ljava/lang/Throwable; {{:try_start_tone_set .. :try_end_tone_set}} :catch_tone_set
    goto :goto_tone_set_done

    :catch_tone_set
    move-exception v4

    :goto_tone_set_done
    :try_start_cm_set
    const-string v4, "standard"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorMode(Ljava/lang/String;)V
    :try_end_cm_set
    .catch Ljava/lang/Throwable; {{:try_start_cm_set .. :try_end_cm_set}} :catch_cm_set
    goto :goto_cm_set_done

    :catch_cm_set
    move-exception v4

    :goto_cm_set_done
    :try_start_dro_set
    const-string v4, "off"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setDROMode(Ljava/lang/String;)V
    :try_end_dro_set
    .catch Ljava/lang/Throwable; {{:try_start_dro_set .. :try_end_dro_set}} :catch_dro_set
    goto :goto_dro_set_done

    :catch_dro_set
    move-exception v4

    :goto_dro_set_done
    :try_start_hdr_set
    const-string v4, "off"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setHDRMode(Ljava/lang/String;)V
    :try_end_hdr_set
    .catch Ljava/lang/Throwable; {{:try_start_hdr_set .. :try_end_hdr_set}} :catch_hdr_set
    goto :goto_hdr_set_done

    :catch_hdr_set
    move-exception v4

    :goto_hdr_set_done
    # Apply preset-specific hardware WB shifts
    :try_start_wb_set
    invoke-static {{p2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getWhitebalanceShiftLB(Ljava/lang/String;)I
    move-result v4
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setLightBalanceForWhiteBalance(I)V

    invoke-static {{p2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getWhitebalanceShiftCC(Ljava/lang/String;)I
    move-result v4
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorCompensationForWhiteBalance(I)V
    :try_end_wb_set
    .catch Ljava/lang/Throwable; {{:try_start_wb_set .. :try_end_wb_set}} :catch_wb_set

    goto :goto_matrix

    :catch_wb_set
    move-exception v4

    :goto_matrix
    :try_start_matrix
    invoke-virtual {{v2, v3}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    :try_end_matrix
    .catch Ljava/lang/Throwable; {{:try_start_matrix .. :try_end_matrix}} :catch_matrix
    goto :goto_matrix_done

    :catch_matrix
    move-exception v4
    const-string v4, "RicohHook"
    const-string v5, "setRGBMatrix not supported on this model (Gen 1 fallback)"
    invoke-static {{v4, v5}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :goto_matrix_done
    :cond_4
    # 2. Single atomic commit of parameters to hardware HAL
    :try_start_commit
    invoke-virtual {{v1, p1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V
    :try_end_commit
    .catch Ljava/lang/Throwable; {{:try_start_commit .. :try_end_commit}} :catch_commit
    goto :goto_commit_done

    :catch_commit
    move-exception v4
    const-string v4, "RicohHook"
    const-string v5, "setParameters failed on hardware commit"
    invoke-static {{v4, v5}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :goto_commit_done
    # 3. Write 1024-point 10-bit Gamma Table & guarantee release of DeviceBuffer
    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v2
    if-eqz v2, :cond_gamma_done

    :try_start_gamma_all
    invoke-virtual {{v2}}, Lcom/sony/scalar/hardware/CameraEx;->createGammaTable()Lcom/sony/scalar/hardware/CameraEx$GammaTable;
    move-result-object v3
    if-eqz v3, :cond_gamma_done

    :try_start_gt
    const/4 v4, 0x1
    invoke-virtual {{v3, v4}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->setPictureEffectGammaForceOff(Z)V

    invoke-static {{p2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getGammaBytes(Ljava/lang/String;)[B
    move-result-object v4
    if-eqz v4, :cond_gt_rel

    new-instance v0, Ljava/io/ByteArrayInputStream;
    invoke-direct {{v0, v4}}, Ljava/io/ByteArrayInputStream;-><init>([B)V
    invoke-virtual {{v3, v0}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->write(Ljava/io/InputStream;)I
    invoke-virtual {{v2, v3}}, Lcom/sony/scalar/hardware/CameraEx;->setExtendedGammaTable(Lcom/sony/scalar/hardware/CameraEx$GammaTable;)V

    :cond_gt_rel
    :try_end_gt
    .catchall {{:try_start_gt .. :try_end_gt}} :catchall_gt

    :try_start_rel
    # Critical: Release native DMA DeviceBuffer
    invoke-virtual {{v3}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->release()V
    :try_end_rel
    .catchall {{:try_start_rel .. :try_end_rel}} :catchall_rel
    goto :goto_gamma_released

    :catchall_gt
    move-exception v4
    :try_start_catch_rel
    invoke-virtual {{v3}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->release()V
    :try_end_catch_rel
    .catchall {{:try_start_catch_rel .. :try_end_catch_rel}} :catchall_rel
    goto :goto_gamma_released

    :catchall_rel
    move-exception v4

    :goto_gamma_released
    :cond_gamma_done
    :try_end_gamma_all
    .catch Ljava/lang/Throwable; {{:try_start_gamma_all .. :try_end_gamma_all}} :catch_gamma_all
    goto :goto_gamma_all_done

    :catch_gamma_all
    move-exception v4
    const-string v4, "RicohHook"
    const-string v5, "ExtendedGammaTable not supported on this model (Gen 1 fallback)"
    invoke-static {{v4, v5}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :goto_gamma_all_done
    if-eqz v2, :cond_cache_clear

    invoke-static {{v2}}, Ljava/lang/System;->identityHashCode(Ljava/lang/Object;)I
    move-result v3
    sput v3, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedCameraHash:I
    sput-object p2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedPreset:Ljava/lang/String;
    goto :goto_cache_done

    :cond_cache_clear
    const/4 v3, 0x0
    sput-object v3, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedPreset:Ljava/lang/String;
    sput v3, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedCameraHash:I

    :goto_cache_done
    sput-object p2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sActivePreset:Ljava/lang/String;
    const/4 v2, 0x1
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    const-string v2, "RicohHook"
    const-string v3, "Ricoh preset applied successfully."
    invoke-static {{v2, v3}}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    const/4 v0, 0x1
    return v0
.end method

.method public static resetHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;)V
    .locals 4
    .annotation system Ldalvik/annotation/Signature;
        value = {{
            "(",
            "Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;",
            "Landroid/util/Pair<",
            "Landroid/hardware/Camera$Parameters;",
            "Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;",
            ">;",
            ")V"
        }}
    .end annotation

    const/4 v0, 0x0
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedPreset:Ljava/lang/String;
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedCameraHash:I
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sActivePreset:Ljava/lang/String;
    invoke-static {{v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->updateCompareBadgeVisibility(Z)V

    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    if-nez v0, :cond_0
    return-void

    :cond_0
    const-string v0, "RicohHook"
    const-string v1, "Resetting Ricoh effects to neutral..."
    invoke-static {{v0, v1}}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v0
    if-eqz v0, :cond_1
    :try_start_res_gt
    const/4 v1, 0x0
    invoke-virtual {{v0, v1}}, Lcom/sony/scalar/hardware/CameraEx;->setExtendedGammaTable(Lcom/sony/scalar/hardware/CameraEx$GammaTable;)V
    :try_end_res_gt
    .catch Ljava/lang/Throwable; {{:try_start_res_gt .. :try_end_res_gt}} :catch_res_gt

    :cond_1
    :goto_res_gt_done
    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraSetting(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v0
    if-eqz v0, :cond_3
    if-nez p1, :cond_2
    invoke-virtual {{v0}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getEmptyParameters()Landroid/util/Pair;
    move-result-object p1

    :cond_2
    if-eqz p1, :cond_3
    iget-object v1, p1, Landroid/util/Pair;->second:Ljava/lang/Object;
    check-cast v1, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;
    if-eqz v1, :cond_3

    :try_start_res_pe
    const-string v2, "off"
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setPictureEffect(Ljava/lang/String;)V
    sput-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mMode:Ljava/lang/String;
    sget-object v3, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sEmptyIntArray:[I
    sput-object v3, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mEnabledCh:[I
    invoke-virtual {{v1, v2, v3}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorSelectMode(Ljava/lang/String;[I)V
    :try_end_res_pe
    .catch Ljava/lang/Throwable; {{:try_start_res_pe .. :try_end_res_pe}} :catch_res_pe
    goto :goto_res_pe_done

    :catch_res_pe
    move-exception v2

    :goto_res_pe_done
    :try_start_res_mat
    # Restore 3x3 identity matrix [1024,0,0, 0,1024,0, 0,0,1024] to BIONZ X ISP
    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIdentityMatrix:[I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    :try_end_res_mat
    .catch Ljava/lang/Throwable; {{:try_start_res_mat .. :try_end_res_mat}} :catch_res_mat

    :goto_res_mat_done
    # Restore only the settings that applyHook() actually backed up (never force "standard" 0,0,0)
    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalColorMode:Z
    if-eqz v2, :cond_res_cm_done

    :try_start_res_cm
    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalColorMode:Ljava/lang/String;
    if-eqz v2, :cond_res_cm_clear
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorMode(Ljava/lang/String;)V
    :try_end_res_cm
    .catch Ljava/lang/Throwable; {{:try_start_res_cm .. :try_end_res_cm}} :catch_res_cm

    :cond_res_cm_clear
    :goto_res_cm_clear
    const/4 v2, 0x0
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalColorMode:Z
    goto :cond_res_cm_done

    :catch_res_cm
    move-exception v2
    goto :goto_res_cm_clear

    :cond_res_cm_done
    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalTone:Z
    if-eqz v2, :cond_res_tone_done

    :try_start_res_tone
    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalContrast:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setContrast(I)V

    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalSaturation:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSaturation(I)V

    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalSharpness:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSharpness(I)V
    :try_end_res_tone
    .catch Ljava/lang/Throwable; {{:try_start_res_tone .. :try_end_res_tone}} :catch_res_tone

    :goto_res_tone_clear
    const/4 v2, 0x0
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalTone:Z
    goto :cond_res_tone_done

    :catch_res_tone
    move-exception v2
    goto :goto_res_tone_clear

    :cond_res_tone_done
    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalDRO:Z
    if-eqz v2, :cond_res_dro_done

    :try_start_res_dro
    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalDRO:Ljava/lang/String;
    if-eqz v2, :cond_res_dro_clear
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setDROMode(Ljava/lang/String;)V
    :try_end_res_dro
    .catch Ljava/lang/Throwable; {{:try_start_res_dro .. :try_end_res_dro}} :catch_res_dro

    :cond_res_dro_clear
    :goto_res_dro_clear
    const/4 v2, 0x0
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalDRO:Z
    goto :cond_res_dro_done

    :catch_res_dro
    move-exception v2
    goto :goto_res_dro_clear

    :cond_res_dro_done
    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalHDR:Z
    if-eqz v2, :cond_res_hdr_done

    :try_start_res_hdr
    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalHDR:Ljava/lang/String;
    if-eqz v2, :cond_res_hdr_clear
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setHDRMode(Ljava/lang/String;)V
    :try_end_res_hdr
    .catch Ljava/lang/Throwable; {{:try_start_res_hdr .. :try_end_res_hdr}} :catch_res_hdr

    :cond_res_hdr_clear
    :goto_res_hdr_clear
    const/4 v2, 0x0
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalHDR:Z
    goto :cond_res_hdr_done

    :catch_res_hdr
    move-exception v2
    goto :goto_res_hdr_clear

    :cond_res_hdr_done
    # Restore original user WB shift
    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    if-eqz v2, :cond_wb_reset

    :try_start_wb_res
    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setLightBalanceForWhiteBalance(I)V

    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorCompensationForWhiteBalance(I)V
    :try_end_wb_res
    .catch Ljava/lang/Throwable; {{:try_start_wb_res .. :try_end_wb_res}} :catch_wb_res

    :goto_wb_clear
    const/4 v2, 0x0
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z

    :cond_wb_reset
    :goto_wb_done
    :try_start_res_commit
    invoke-virtual {{v0, p1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V
    :try_end_res_commit
    .catch Ljava/lang/Throwable; {{:try_start_res_commit .. :try_end_res_commit}} :catch_res_commit

    :goto_res_commit_done
    :cond_3
    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    return-void

    :catch_res_gt
    move-exception v1
    goto :goto_res_gt_done

    :catch_res_mat
    move-exception v2
    goto :goto_res_mat_done

    :catch_wb_res
    move-exception v2
    goto :goto_wb_clear

    :catch_res_commit
    move-exception v0
    goto :goto_res_commit_done
.end method

.method public static onTerminateHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)V
    .locals 1

    const/4 v0, 0x1
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    const/4 v0, 0x0
    invoke-static {{p0, v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->resetHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;)V
    return-void
.end method

.method public static getLanguageType()I
    .locals 3

    # Default: 0 = English / Global
    const/4 v0, 0x0

    :try_start_0
    invoke-static {{}}, Ljava/util/Locale;->getDefault()Ljava/util/Locale;
    move-result-object v1
    if-eqz v1, :cond_fallback

    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCachedLocale:Ljava/util/Locale;
    if-ne v1, v2, :cond_compute_lang

    sget v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCachedLangType:I
    return v0

    :cond_compute_lang
    invoke-virtual {{v1}}, Ljava/util/Locale;->getLanguage()Ljava/lang/String;
    move-result-object v2
    if-eqz v2, :cond_cache_zero

    const-string v0, "zh"
    invoke-virtual {{v2, v0}}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :cond_cache_zero

    invoke-virtual {{v1}}, Ljava/util/Locale;->getCountry()Ljava/lang/String;
    move-result-object v2
    if-eqz v2, :cond_simp

    const-string v0, "TW"
    invoke-virtual {{v2, v0}}, Ljava/lang/String;->equalsIgnoreCase(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :cond_chk_hk
    const/4 v0, 0x1
    goto :cond_store_lang

    :cond_chk_hk
    const-string v0, "HK"
    invoke-virtual {{v2, v0}}, Ljava/lang/String;->equalsIgnoreCase(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :cond_chk_mo
    const/4 v0, 0x1
    goto :cond_store_lang

    :cond_chk_mo
    const-string v0, "MO"
    invoke-virtual {{v2, v0}}, Ljava/lang/String;->equalsIgnoreCase(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :cond_simp
    const/4 v0, 0x1
    goto :cond_store_lang

    :cond_simp
    # 2 = Simplified Chinese
    const/4 v0, 0x2
    goto :cond_store_lang

    :cond_cache_zero
    const/4 v0, 0x0

    :cond_store_lang
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCachedLocale:Ljava/util/Locale;
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCachedLangType:I
    return v0

    :cond_fallback
    # 0 = English / Global
    const/4 v0, 0x0
    return v0
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :catch_0

    :catch_0
    move-exception v1
    const/4 v0, 0x0
    return v0
.end method

.method public static getAppTitle()Ljava/lang/String;
    .locals 2

    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getLanguageType()I
    move-result v0

    const/4 v1, 0x1
    if-ne v0, v1, :cond_simp
    const-string v0, "\u7406\u5149\u76f8\u6a5f"
    return-object v0

    :cond_simp
    const/4 v1, 0x2
    if-ne v0, v1, :cond_eng
    const-string v0, "\u7406\u5149\u76f8\u673a"
    return-object v0

    :cond_eng
    const-string v0, "Ricoh Camera"
    return-object v0
.end method

.method public static getFilterName(Ljava/lang/String;)Ljava/lang/String;
    .locals 2

    if-nez p0, :cond_start
    const/4 v0, 0x0
    return-object v0

    :cond_start
    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getLanguageType()I
    move-result v1

    # 1. pop-color
    const-string v0, "pop-color"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_neg
    if-nez v1, :cond_pop_zh
    const-string v0, "Ricoh GR Positive Film"
    return-object v0
    :cond_pop_zh
    const-string v0, "\u7406\u5149 GR \u6b63\u7247"
    return-object v0

    :cond_check_neg
    # 2. retro-photo
    const-string v0, "retro-photo"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_hcbw
    if-nez v1, :cond_neg_zh
    const-string v0, "Ricoh Negative Film"
    return-object v0
    :cond_neg_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_neg_cn
    const-string v0, "\u7406\u5149 \u8ca0\u7247"
    return-object v0
    :cond_neg_cn
    const-string v0, "\u7406\u5149 \u8d1f\u7247"
    return-object v0

    :cond_check_hcbw
    # 3. richtone-mono
    const-string v0, "richtone-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_daido
    if-nez v1, :cond_hcbw_zh
    const-string v0, "High Contrast B&W"
    return-object v0
    :cond_hcbw_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_hcbw_cn
    const-string v0, "\u9ad8\u5c0d\u6bd4\u9ed1\u767d"
    return-object v0
    :cond_hcbw_cn
    const-string v0, "\u9ad8\u5bf9\u6bd4\u9ed1\u767d"
    return-object v0

    :cond_check_daido
    # 4. rough-mono
    const-string v0, "rough-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_xpro
    if-nez v1, :cond_daido_zh
    const-string v0, "Moriyama Daido B&W"
    return-object v0
    :cond_daido_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_daido_cn
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98a8"
    return-object v0
    :cond_daido_cn
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98ce"
    return-object v0

    :cond_check_xpro
    # 5. watercolor
    const-string v0, "watercolor"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_rawjpeg
    if-nez v1, :cond_xpro_zh
    const-string v0, "Steve McCurry"
    return-object v0
    :cond_xpro_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_xpro_cn
    const-string v0, "\u9ea5\u51f1\u745e Kodachrome"
    return-object v0
    :cond_xpro_cn
    const-string v0, "\u9ea6\u51ef\u745e Kodachrome"
    return-object v0

    :cond_check_rawjpeg
    # 6. setPictureStorageFormat_rawjpeg
    const-string v0, "setPictureStorageFormat_rawjpeg"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_raw
    if-nez v1, :cond_rawj_zh
    const-string v0, "RAW & JPEG"
    return-object v0
    :cond_rawj_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_rawj_cn
    const-string v0, "RAW\u8207JPEG"
    return-object v0
    :cond_rawj_cn
    const-string v0, "RAW\u4e0eJPEG"
    return-object v0

    :cond_check_raw
    # 7. setPictureStorageFormat_raw
    const-string v0, "setPictureStorageFormat_raw"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_none
    const-string v0, "RAW"
    return-object v0

    :cond_none
    const/4 v0, 0x0
    return-object v0
.end method

.method public static getFilterGuide(Ljava/lang/String;)Ljava/lang/String;
    .locals 2

    if-nez p0, :cond_start
    const/4 v0, 0x0
    return-object v0

    :cond_start
    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getLanguageType()I
    move-result v1

    # 1. pop-color
    const-string v0, "pop-color"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_neg
    if-nez v1, :cond_guide_pop_zh
    const-string v0, "Ricoh GR Positive Film color effect"
    return-object v0
    :cond_guide_pop_zh
    const-string v0, "\u7406\u5149 GR \u6b63\u7247\u8272\u5f69\u6548\u679c (Ricoh Positive Film)"
    return-object v0

    :cond_check_neg
    # 2. retro-photo
    const-string v0, "retro-photo"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_hcbw
    if-nez v1, :cond_guide_neg_zh
    const-string v0, "Ricoh Negative Film vintage color effect"
    return-object v0
    :cond_guide_neg_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_guide_neg_cn
    const-string v0, "\u7406\u5149 \u8ca0\u7247\u81a0\u7247\u8272\u5f69\u6548\u679c (Ricoh Negative Film)"
    return-object v0
    :cond_guide_neg_cn
    const-string v0, "\u7406\u5149 \u8d1f\u7247\u80f6\u7247\u8272\u5f69\u6548\u679c (Ricoh Negative Film)"
    return-object v0

    :cond_check_hcbw
    # 3. richtone-mono
    const-string v0, "richtone-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_daido
    if-nez v1, :cond_guide_hcbw_zh
    const-string v0, "High Contrast B&W monochrome film effect"
    return-object v0
    :cond_guide_hcbw_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_guide_hcbw_cn
    const-string v0, "\u9ad8\u5c0d\u6bd4\u9ed1\u767d\u81a0\u7247\u6548\u679c (Ricoh High Contrast B&W)"
    return-object v0
    :cond_guide_hcbw_cn
    const-string v0, "\u9ad8\u5bf9\u6bd4\u9ed1\u767d\u80f6\u7247\u6548\u679c (Ricoh High Contrast B&W)"
    return-object v0

    :cond_check_daido
    # 4. rough-mono
    const-string v0, "rough-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_xpro
    if-nez v1, :cond_guide_daido_zh
    const-string v0, "Moriyama Daido rough high contrast B&W"
    return-object v0
    :cond_guide_daido_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_guide_daido_cn
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98a8\u7c97\u7cf2\u9ad8\u5c0d\u6bd4\u9ed1\u767d (Moriyama Daido B&W)"
    return-object v0
    :cond_guide_daido_cn
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98ce\u7c97\u7c9d\u9ad8\u5bf9\u6bd4\u9ed1\u767d (Moriyama Daido B&W)"
    return-object v0

    :cond_check_xpro
    # 5. watercolor
    const-string v0, "watercolor"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_guide_rawjpeg
    if-nez v1, :cond_guide_xpro_zh
    const-string v0, "Authentic Leica Steve McCurry warm documentary profile"
    return-object v0
    :cond_guide_xpro_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_guide_xpro_cn
    const-string v0, "\u5f95\u5361\u5b98\u65b9 Steve McCurry \u7d93\u5178\u6696\u91d1\u5fb7\u5473\u7d00\u5be6\u8272\u5f69"
    return-object v0
    :cond_guide_xpro_cn
    const-string v0, "\u5f95\u5361\u5b98\u65b9 Steve McCurry \u7ecf\u5178\u6696\u91d1\u5fb7\u5473\u7eaa\u5b9e\u8272\u5f69"
    return-object v0

    :cond_check_guide_rawjpeg
    # 6. setPictureStorageFormat_rawjpeg
    const-string v0, "setPictureStorageFormat_rawjpeg"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_guide_raw
    if-nez v1, :cond_guide_rawj_zh
    const-string v0, "Simultaneously records both a RAW image and a JPEG image."
    return-object v0
    :cond_guide_rawj_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_guide_rawj_cn
    const-string v0, "\u540c\u6642\u8a18\u9304RAW\u5f71\u50cf\u548cJPEG\u5f71\u50cf\u3002"
    return-object v0
    :cond_guide_rawj_cn
    const-string v0, "\u540c\u65f6\u8bb0\u5f55RAW\u56fe\u50cf\u548cJPEG\u56fe\u50cf\u3002"
    return-object v0

    :cond_check_guide_raw
    # 7. setPictureStorageFormat_raw
    const-string v0, "setPictureStorageFormat_raw"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_none
    if-nez v1, :cond_guide_raw_zh
    const-string v0, "Records a RAW image."
    return-object v0
    :cond_guide_raw_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_guide_raw_cn
    const-string v0, "\u8a18\u9304RAW\u5f71\u50cf\u3002"
    return-object v0
    :cond_guide_raw_cn
    const-string v0, "\u8bb0\u5f55RAW\u56fe\u50cf\u3002"
    return-object v0

    :cond_none
    const/4 v0, 0x0
    return-object v0
.end method

.method public static filterQualityAvailability(Ljava/lang/String;Z)Z
    .locals 1

    const/4 v0, 0x1
    return v0
.end method

.method public static setupLivePreviewMenu(Landroid/view/ViewGroup;Landroid/widget/ImageView;Landroid/widget/TextView;Landroid/widget/TextView;Landroid/view/View;)V
    .locals 5
    .param p0, "rootView"    # Landroid/view/ViewGroup;
    .param p1, "bgImage"    # Landroid/widget/ImageView;
    .param p2, "itemName"    # Landroid/widget/TextView;
    .param p3, "guideText"    # Landroid/widget/TextView;
    .param p4, "listView"    # Landroid/view/View;

    :try_start_live_ui
    # 1. Remove opaque black root background so hardware EE Live View shows through
    if-eqz p0, :cond_live_bg
    const/4 v0, 0x0
    invoke-virtual {{p0, v0}}, Landroid/view/ViewGroup;->setBackgroundDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_live_bg
    # 2. Hide static sample ImageView (View.GONE = 8) and clear any pooled drawable
    if-eqz p1, :cond_live_name
    const/16 v0, 0x8
    invoke-virtual {{p1, v0}}, Landroid/widget/ImageView;->setVisibility(I)V
    const/4 v0, 0x0
    invoke-virtual {{p1, v0}}, Landroid/widget/ImageView;->setBackgroundDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_live_name
    # 3. Position filter title neatly below the 60px top header bar (x=132..628, y=66..108)
    if-eqz p2, :cond_live_guide
    new-instance v0, Landroid/widget/RelativeLayout$LayoutParams;
    const/16 v1, 0x1f0
    const/16 v2, 0x2a
    invoke-direct {{v0, v1, v2}}, Landroid/widget/RelativeLayout$LayoutParams;-><init>(II)V
    const/16 v1, 0x84
    const/16 v2, 0x42
    const/16 v3, 0xc
    const/4 v4, 0x0
    invoke-virtual {{v0, v1, v2, v3, v4}}, Landroid/widget/RelativeLayout$LayoutParams;->setMargins(IIII)V
    invoke-virtual {{p2, v0}}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V
    const/16 v1, 0xa
    const/4 v2, 0x0
    const/16 v3, 0xa
    const/4 v4, 0x0
    invoke-virtual {{p2, v1, v2, v3, v4}}, Landroid/widget/TextView;->setPadding(IIII)V

    :cond_live_guide
    # 4. Compact translucent guide strip aligned above the 60px bottom FooterGuide bar
    #    width=496px (0x1f0), height=WRAP_CONTENT (-2), ALIGN_PARENT_BOTTOM (12),
    #    margins=(132, 0, 12, 66), maxLines=2, gravity=LEFT|CENTER_VERTICAL (0x13),
    #    padding=(10, 6, 10, 6), bg=0x66000000 (40% translucent black)
    if-eqz p3, :cond_live_list
    new-instance v0, Landroid/widget/RelativeLayout$LayoutParams;
    const/16 v1, 0x1f0
    const/4 v2, -0x2
    invoke-direct {{v0, v1, v2}}, Landroid/widget/RelativeLayout$LayoutParams;-><init>(II)V
    const/16 v1, 0xc
    invoke-virtual {{v0, v1}}, Landroid/widget/RelativeLayout$LayoutParams;->addRule(I)V
    const/16 v1, 0x84
    const/4 v2, 0x0
    const/16 v3, 0xc
    const/16 v4, 0x42
    invoke-virtual {{v0, v1, v2, v3, v4}}, Landroid/widget/RelativeLayout$LayoutParams;->setMargins(IIII)V
    invoke-virtual {{p3, v0}}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V
    const/4 v1, 0x2
    invoke-virtual {{p3, v1}}, Landroid/widget/TextView;->setMaxLines(I)V
    const/16 v1, 0x13
    invoke-virtual {{p3, v1}}, Landroid/widget/TextView;->setGravity(I)V
    const/16 v1, 0xa
    const/4 v2, 0x6
    const/16 v3, 0xa
    const/4 v4, 0x6
    invoke-virtual {{p3, v1, v2, v3, v4}}, Landroid/widget/TextView;->setPadding(IIII)V
    const v1, 0x66000000
    invoke-virtual {{p3, v1}}, Landroid/widget/TextView;->setBackgroundColor(I)V

    :cond_live_list
    # 5. Subtle translucent dark rail behind the left 122x330 icon list for bright-scene contrast
    if-eqz p4, :cond_live_done
    const v1, 0x66000000
    invoke-virtual {{p4, v1}}, Landroid/view/View;->setBackgroundColor(I)V

    :cond_live_done
    :try_end_live_ui
    .catch Ljava/lang/Throwable; {{:try_start_live_ui .. :try_end_live_ui}} :catch_live_ui
    return-void

    :catch_live_ui
    move-exception v0
    const-string v1, "RicohHook"
    const-string v2, "setupLivePreviewMenu failed"
    invoke-static {{v1, v2, v0}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    return-void
.end method

.method public static getCompareBadgeText()Ljava/lang/String;
    .locals 2

    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getLanguageType()I
    move-result v1
    if-nez v1, :cond_badge_zh
    const-string v0, "ORIGINAL (BEFORE)"
    return-object v0

    :cond_badge_zh
    const/4 v0, 0x1
    if-ne v1, v0, :cond_badge_cn
    const-string v0, "\u539f\u7247\u5c0d\u6bd4 (Original)"
    return-object v0

    :cond_badge_cn
    const-string v0, "\u539f\u7247\u5bf9\u6bd4 (Original)"
    return-object v0
.end method

.method private static updateCompareBadgeVisibility(Z)V
    .locals 2
    .param p0, "visible"    # Z

    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;
    if-eqz v0, :cond_badge_vis_done

    :try_start_badge_vis
    if-eqz p0, :cond_badge_gone
    const/4 v1, 0x0
    goto :goto_badge_apply

    :cond_badge_gone
    const/16 v1, 0x8

    :goto_badge_apply
    invoke-virtual {{v0, v1}}, Landroid/widget/TextView;->setVisibility(I)V
    :try_end_badge_vis
    .catch Ljava/lang/Throwable; {{:try_start_badge_vis .. :try_end_badge_vis}} :catch_badge_vis

    :cond_badge_vis_done
    :goto_badge_vis_done
    return-void

    :catch_badge_vis
    move-exception v0
    goto :goto_badge_vis_done
.end method

.method public static attachCompareBadge(Landroid/view/ViewGroup;)V
    .locals 6
    .param p0, "baseView"    # Landroid/view/ViewGroup;

    :try_start_attach
    if-nez p0, :cond_attach_check_type
    return-void

    :cond_attach_check_type
    instance-of v2, p0, Landroid/widget/RelativeLayout;
    if-nez v2, :cond_attach_detach_old
    return-void

    :cond_attach_detach_old
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;
    if-eqz v0, :cond_attach_ctx
    invoke-virtual {{v0}}, Landroid/widget/TextView;->getParent()Landroid/view/ViewParent;
    move-result-object v1
    instance-of v2, v1, Landroid/view/ViewGroup;
    if-eqz v2, :cond_attach_ctx
    check-cast v1, Landroid/view/ViewGroup;
    invoke-virtual {{v1, v0}}, Landroid/view/ViewGroup;->removeView(Landroid/view/View;)V

    :cond_attach_ctx
    invoke-virtual {{p0}}, Landroid/view/ViewGroup;->getContext()Landroid/content/Context;
    move-result-object v1
    if-nez v1, :cond_attach_create
    return-void

    :cond_attach_create
    new-instance v0, Landroid/widget/TextView;
    invoke-direct {{v0, v1}}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCompareBadgeText()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {{v0, v1}}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    const/4 v2, -0x1
    invoke-virtual {{v0, v2}}, Landroid/widget/TextView;->setTextColor(I)V

    const/4 v2, 0x0
    const v3, 0x41b00000
    invoke-virtual {{v0, v2, v3}}, Landroid/widget/TextView;->setTextSize(IF)V

    const v2, 0x7f000000
    invoke-virtual {{v0, v2}}, Landroid/widget/TextView;->setBackgroundColor(I)V

    const/16 v2, 0x10
    const/4 v3, 0x6
    const/16 v4, 0x10
    const/4 v5, 0x6
    invoke-virtual {{v0, v2, v3, v4, v5}}, Landroid/widget/TextView;->setPadding(IIII)V

    const/16 v2, 0x11
    invoke-virtual {{v0, v2}}, Landroid/widget/TextView;->setGravity(I)V

    new-instance v1, Landroid/widget/RelativeLayout$LayoutParams;
    const/4 v2, -0x2
    const/4 v3, -0x2
    invoke-direct {{v1, v2, v3}}, Landroid/widget/RelativeLayout$LayoutParams;-><init>(II)V

    const/16 v2, 0xe
    invoke-virtual {{v1, v2}}, Landroid/widget/RelativeLayout$LayoutParams;->addRule(I)V

    const/16 v2, 0xa
    invoke-virtual {{v1, v2}}, Landroid/widget/RelativeLayout$LayoutParams;->addRule(I)V

    const/4 v2, 0x0
    const/16 v3, 0x38
    const/4 v4, 0x0
    const/4 v5, 0x0
    invoke-virtual {{v1, v2, v3, v4, v5}}, Landroid/widget/RelativeLayout$LayoutParams;->setMargins(IIII)V

    invoke-virtual {{v0, v1}}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    if-eqz v2, :cond_attach_hidden
    const/4 v3, 0x0
    goto :goto_attach_vis

    :cond_attach_hidden
    const/16 v3, 0x8

    :goto_attach_vis
    invoke-virtual {{v0, v3}}, Landroid/widget/TextView;->setVisibility(I)V
    invoke-virtual {{p0, v0}}, Landroid/view/ViewGroup;->addView(Landroid/view/View;)V
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;
    :try_end_attach
    .catch Ljava/lang/Throwable; {{:try_start_attach .. :try_end_attach}} :catch_attach
    return-void

    :catch_attach
    move-exception v0
    const-string v1, "RicohHook"
    const-string v2, "attachCompareBadge failed"
    invoke-static {{v1, v2, v0}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    return-void
.end method

.method public static detachCompareBadge(Landroid/view/ViewGroup;)V
    .locals 3
    .param p0, "baseView"    # Landroid/view/ViewGroup;

    :try_start_detach
    sget-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;
    if-eqz v0, :cond_detach_done

    if-eqz p0, :cond_detach_parent
    invoke-virtual {{p0, v0}}, Landroid/view/ViewGroup;->removeView(Landroid/view/View;)V
    goto :goto_detach_clear

    :cond_detach_parent
    invoke-virtual {{v0}}, Landroid/widget/TextView;->getParent()Landroid/view/ViewParent;
    move-result-object v1
    instance-of v2, v1, Landroid/view/ViewGroup;
    if-eqz v2, :cond_detach_clear
    check-cast v1, Landroid/view/ViewGroup;
    invoke-virtual {{v1, v0}}, Landroid/view/ViewGroup;->removeView(Landroid/view/View;)V

    :cond_detach_clear
    :goto_detach_clear
    const/4 v1, 0x0
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;

    :cond_detach_done
    :try_end_detach
    .catch Ljava/lang/Throwable; {{:try_start_detach .. :try_end_detach}} :catch_detach
    return-void

    :catch_detach
    move-exception v0
    const/4 v1, 0x0
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sCompareBadge:Landroid/widget/TextView;
    return-void
.end method

.method public static setBypassPreview(Z)V
    .locals 8
    .param p0, "bypass"    # Z

    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    if-eq v0, p0, :cond_bp_noop

    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getInstance()Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;
    move-result-object v1
    if-eqz v1, :cond_bp_noop

    if-eqz p0, :cond_bp_restore

    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    if-eqz v0, :cond_bp_noop

    const/4 v0, 0x1
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z

    const/4 v2, 0x0
    sput-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedPreset:Ljava/lang/String;

    const/4 v0, 0x0
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sAppliedCameraHash:I

    invoke-static {{v1}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v2
    if-eqz v2, :cond_bp_gt_done

    :try_start_bp_gt
    const/4 v3, 0x0
    invoke-virtual {{v2, v3}}, Lcom/sony/scalar/hardware/CameraEx;->setExtendedGammaTable(Lcom/sony/scalar/hardware/CameraEx$GammaTable;)V
    :try_end_bp_gt
    .catch Ljava/lang/Throwable; {{:try_start_bp_gt .. :try_end_bp_gt}} :catch_bp_gt
    goto :cond_bp_gt_done

    :catch_bp_gt
    move-exception v7

    :cond_bp_gt_done
    invoke-static {{v1}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraSetting(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v2
    if-eqz v2, :cond_bp_badge_on

    invoke-virtual {{v2}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getEmptyParameters()Landroid/util/Pair;
    move-result-object v3
    if-eqz v3, :cond_bp_badge_on

    iget-object v4, v3, Landroid/util/Pair;->second:Ljava/lang/Object;
    check-cast v4, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;
    if-eqz v4, :cond_bp_badge_on

    :try_start_bp_mat
    sget-object v5, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIdentityMatrix:[I
    invoke-virtual {{v4, v5}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    :try_end_bp_mat
    .catch Ljava/lang/Throwable; {{:try_start_bp_mat .. :try_end_bp_mat}} :catch_bp_mat
    goto :cond_bp_mat_done

    :catch_bp_mat
    move-exception v7

    :cond_bp_mat_done
    :try_start_bp_wb
    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    if-eqz v0, :cond_bp_wb_zero
    sget v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I
    sget v6, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I
    goto :goto_bp_wb_apply

    :cond_bp_wb_zero
    const/4 v0, 0x0
    const/4 v6, 0x0

    :goto_bp_wb_apply
    invoke-virtual {{v4, v0}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setLightBalanceForWhiteBalance(I)V
    invoke-virtual {{v4, v6}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorCompensationForWhiteBalance(I)V
    :try_end_bp_wb
    .catch Ljava/lang/Throwable; {{:try_start_bp_wb .. :try_end_bp_wb}} :catch_bp_wb
    goto :cond_bp_wb_done

    :catch_bp_wb
    move-exception v7

    :cond_bp_wb_done
    :try_start_bp_commit
    invoke-virtual {{v2, v3}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V
    :try_end_bp_commit
    .catch Ljava/lang/Throwable; {{:try_start_bp_commit .. :try_end_bp_commit}} :catch_bp_commit
    goto :cond_bp_badge_on

    :catch_bp_commit
    move-exception v7

    :cond_bp_badge_on
    const/4 v0, 0x1
    invoke-static {{v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->updateCompareBadgeVisibility(Z)V
    return-void

    :cond_bp_restore
    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    invoke-static {{v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->updateCompareBadgeVisibility(Z)V

    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sActivePreset:Ljava/lang/String;
    if-nez v2, :cond_bp_have_preset
    invoke-virtual {{v1}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getBackupEffectValue()Ljava/lang/String;
    move-result-object v2

    :cond_bp_have_preset
    if-eqz v2, :cond_bp_noop
    invoke-static {{v2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->isRicohPreset(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :cond_bp_noop

    invoke-static {{v1}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraSetting(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    move-result-object v3
    if-eqz v3, :cond_bp_noop

    invoke-virtual {{v3}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->getEmptyParameters()Landroid/util/Pair;
    move-result-object v4
    invoke-static {{v1, v4, v2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->applyHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;Ljava/lang/String;)Z

    :cond_bp_noop
    return-void
.end method

.method public static ensureFilterRestored()V
    .locals 1

    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    if-eqz v0, :cond_efr_done
    const/4 v0, 0x0
    invoke-static {{v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->setBypassPreview(Z)V

    :cond_efr_done
    return-void
.end method

.method public static handleShootingCompareKey(Landroid/view/KeyEvent;Z)I
    .locals 1
    .param p0, "event"    # Landroid/view/KeyEvent;
    .param p1, "pressed"    # Z

    if-eqz p1, :cond_hsc_apply
    if-eqz p0, :cond_hsc_apply
    invoke-virtual {{p0}}, Landroid/view/KeyEvent;->getRepeatCount()I
    move-result v0
    if-eqz v0, :cond_hsc_apply
    const/4 v0, 0x1
    return v0

    :cond_hsc_apply
    invoke-static {{p1}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->setBypassPreview(Z)V
    const/4 v0, 0x1
    return v0
.end method

.method public static handleMenuCompareKey(Landroid/view/KeyEvent;ZLandroid/widget/TextView;Ljava/lang/String;)I
    .locals 2
    .param p0, "event"    # Landroid/view/KeyEvent;
    .param p1, "pressed"    # Z
    .param p2, "itemNameView"    # Landroid/widget/TextView;
    .param p3, "selectedItemId"    # Ljava/lang/String;

    if-eqz p1, :cond_hmc_apply
    if-eqz p0, :cond_hmc_apply
    invoke-virtual {{p0}}, Landroid/view/KeyEvent;->getRepeatCount()I
    move-result v1
    if-eqz v1, :cond_hmc_apply
    const/4 v1, 0x1
    return v1

    :cond_hmc_apply
    invoke-static {{p1}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->setBypassPreview(Z)V

    if-eqz p2, :cond_hmc_done

    :try_start_hmc_ui
    if-eqz p1, :cond_hmc_restore_title
    sget-boolean v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sBypassOriginal:Z
    if-eqz v1, :cond_hmc_done
    invoke-static {{}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCompareBadgeText()Ljava/lang/String;
    move-result-object v0
    invoke-virtual {{p2, v0}}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    goto :cond_hmc_done

    :cond_hmc_restore_title
    invoke-static {{p3}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getFilterName(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    if-eqz v0, :cond_hmc_done
    invoke-virtual {{p2, v0}}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    :try_end_hmc_ui
    .catch Ljava/lang/Throwable; {{:try_start_hmc_ui .. :try_end_hmc_ui}} :catch_hmc_ui

    :cond_hmc_done
    :goto_hmc_done
    const/4 v1, 0x1
    return v1

    :catch_hmc_ui
    move-exception v0
    goto :goto_hmc_done
.end method
'''

import sys
import os
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate RicohHook.smali with calculated Gamma tables and color matrices")
    default_out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'smali', 'RicohHook.smali')
    parser.add_argument('-o', '--output', default=default_out, help=f"Path to output smali file (default: {default_out})")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(smali_content)
    print(f"Generated {args.output} (size: {len(smali_content)} bytes)")

