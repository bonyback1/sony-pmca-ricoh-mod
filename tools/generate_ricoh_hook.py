import glob
import math

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
    # Ricoh GR Positive Film: gentle filmic S-curve with -0.33 EV baked in for rich, dense positive film colors
    return make_filmic_curve(slope=1.25, toe_lift=4, shoulder_max=1020, center=0.48, ev_offset=-0.33)

def gen_curve_neg():
    # Ricoh Negative Film: lifted matte shadows (toe_lift=36), +0.33 EV baked in for soft airy look, gentle contrast
    return make_filmic_curve(slope=1.08, toe_lift=36, shoulder_max=985, center=0.50, ev_offset=0.33)

def gen_curve_hcbw():
    # Ricoh High Contrast B&W: punchy contrast (slope=1.85), deep rich blacks preserving dark textures
    return make_filmic_curve(slope=1.85, toe_lift=0, shoulder_max=1023, center=0.50, ev_offset=0.0)

def gen_curve_daido():
    # Moriyama Daido: gritty, high-contrast graphic street B&W (slope=2.38), -0.33 EV baked in
    return make_filmic_curve(slope=2.38, toe_lift=0, shoulder_max=1023, center=0.50, ev_offset=-0.33)

def gen_curve_xpro():
    # Ricoh Cross Process: vivid contrast with cross-process tones (slope=1.30, toe_lift=8)
    return make_filmic_curve(slope=1.30, toe_lift=8, shoulder_max=1018, center=0.46, ev_offset=0.0)

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
.field private static sOriginalLB:I
.field private static sOriginalCC:I
.field private static sHasSavedOriginalWB:Z

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


# direct methods
.method static constructor <clinit>()V
    .locals 2

    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I
    sput v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z

    const/4 v0, 0x0
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaPos:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaNeg:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaHcbw:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaDaido:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaXpro:[B

    const/16 v0, 0x9

    # 1. Positive Film Matrix (1148, -84, -40, -36, 1118, -58, -24, -68, 1116)
    new-array v1, v0, [I
    fill-array-data v1, :array_pos_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sPositiveFilmMatrix:[I

    # 2. Negative Film Matrix (1046, -16, -6, -26, 1026, 24, -36, -16, 1076)
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

    # 5. Cross Process Matrix (1130, -86, -20, 70, 1070, -116, -60, 30, 1054)
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
        0x47c
        -0x54
        -0x28
        -0x24
        0x45e
        -0x3a
        -0x18
        -0x44
        0x45c
    .end array-data

    :array_neg_matrix
    .array-data 4
        0x416
        -0x10
        -0x6
        -0x1a
        0x402
        0x18
        -0x24
        -0x10
        0x434
    .end array-data

    :array_hcbw_matrix
    .array-data 4
        0x132
        0x259
        0x75
        0x132
        0x259
        0x75
        0x132
        0x259
        0x75
    .end array-data

    :array_daido_matrix
    .array-data 4
        0x233
        0x166
        0x67
        0x233
        0x166
        0x67
        0x233
        0x166
        0x67
    .end array-data

    :array_xpro_matrix
    .array-data 4
        0x46a
        -0x56
        -0x14
        0x46
        0x42e
        -0x74
        -0x3c
        0x1e
        0x41e
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
    const/4 v0, 0x2
    return v0

    :cond_neg
    const-string v0, "retro-photo"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_xpro
    const/4 v0, 0x4
    return v0

    :cond_xpro
    const-string v0, "watercolor"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_zero
    const/4 v0, -0x3
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
    const/4 v0, -0x1
    return v0

    :cond_neg
    const-string v0, "retro-photo"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_xpro
    const/4 v0, -0x2
    return v0

    :cond_xpro
    const-string v0, "watercolor"
    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_zero
    const/4 v0, 0x2
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

    invoke-static {{p2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getRGBMatrix(Ljava/lang/String;)[I
    move-result-object v3
    if-nez v3, :cond_0
    return v0

    :cond_0
    :try_start_0
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
    # 1. Turn off native effect to avoid hardware conflict
    iget-object v2, p1, Landroid/util/Pair;->second:Ljava/lang/Object;
    check-cast v2, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;
    if-eqz v2, :cond_4
    const-string v4, "off"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setPictureEffect(Ljava/lang/String;)V

    # Force standard neutral baseline to prevent stacking with camera Clear/Vivid/etc.
    const-string v4, "standard"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorMode(Ljava/lang/String;)V

    const/4 v4, 0x0
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setContrast(I)V
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSaturation(I)V
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSharpness(I)V

    # Force DRO and HDR to off directly on modifier in the same Pair (atomic commit)
    const-string v4, "off"
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setDROMode(Ljava/lang/String;)V
    invoke-virtual {{v2, v4}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setHDRMode(Ljava/lang/String;)V

    # Backup original user WB shifts on first apply
    sget-boolean v4, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    if-nez v4, :cond_wb_saved

    :try_start_wb_get
    invoke-virtual {{v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getLightBalanceForWhiteBalance()I
    move-result v4
    sput v4, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I

    invoke-virtual {{v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->getColorCompensationForWhiteBalance()I
    move-result v4
    sput v4, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I

    const/4 v4, 0x1
    sput-boolean v4, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    :try_end_wb_get
    .catch Ljava/lang/Throwable; {{:try_start_wb_get .. :try_end_wb_get}} :catch_wb_get

    :cond_wb_saved
    :goto_wb_apply
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

    :catch_wb_get
    move-exception v4
    goto :goto_wb_apply

    :catch_wb_set
    move-exception v4

    :goto_matrix
    invoke-virtual {{v2, v3}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V

    :cond_4
    # 2. Single atomic commit of parameters to hardware HAL
    invoke-virtual {{v1, p1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V

    # 3. Write 1024-point 10-bit Gamma Table & guarantee release of DeviceBuffer
    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v2
    if-eqz v2, :cond_5

    invoke-virtual {{v2}}, Lcom/sony/scalar/hardware/CameraEx;->createGammaTable()Lcom/sony/scalar/hardware/CameraEx$GammaTable;
    move-result-object v3
    if-eqz v3, :cond_5

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

    # Critical: Release native DMA DeviceBuffer
    invoke-virtual {{v3}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->release()V
    goto :cond_5

    :catchall_gt
    move-exception v4
    invoke-virtual {{v3}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->release()V
    throw v4

    :cond_5
    const/4 v2, 0x1
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    const-string v2, "RicohHook"
    const-string v3, "Ricoh preset applied successfully."
    invoke-static {{v2, v3}}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :catch_0

    const/4 v0, 0x1
    return v0

    :catch_0
    move-exception v1
    const-string v2, "RicohHook"
    invoke-virtual {{v1}}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
    move-result-object v1
    invoke-static {{v2, v1}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I
    const/4 v0, 0x0
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

    sget-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    if-nez v0, :cond_0
    return-void

    :cond_0
    :try_start_0
    const-string v0, "RicohHook"
    const-string v1, "Resetting Ricoh effects to neutral..."
    invoke-static {{v0, v1}}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v0
    if-eqz v0, :cond_1
    const/4 v1, 0x0
    invoke-virtual {{v0, v1}}, Lcom/sony/scalar/hardware/CameraEx;->setExtendedGammaTable(Lcom/sony/scalar/hardware/CameraEx$GammaTable;)V

    :cond_1
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
    # Pass null to bypass RGB matrix multiplication hardware
    const/4 v2, 0x0
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    const-string v2, "standard"
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorMode(Ljava/lang/String;)V
    const/4 v2, 0x0
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setContrast(I)V
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSaturation(I)V
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setSharpness(I)V

    # Restore original user WB shift
    sget-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    if-eqz v2, :cond_wb_reset

    :try_start_wb_res
    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalLB:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setLightBalanceForWhiteBalance(I)V

    sget v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sOriginalCC:I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setColorCompensationForWhiteBalance(I)V

    const/4 v2, 0x0
    sput-boolean v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sHasSavedOriginalWB:Z
    :try_end_wb_res
    .catch Ljava/lang/Throwable; {{:try_start_wb_res .. :try_end_wb_res}} :catch_wb_res

    :cond_wb_reset
    :goto_wb_done
    invoke-virtual {{v0, p1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V

    :cond_3
    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :catch_0

    return-void

    :catch_wb_res
    move-exception v2
    goto :goto_wb_done

    :catch_0
    move-exception v0
    const-string v1, "RicohHook"
    invoke-virtual {{v0}}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
    move-result-object v0
    invoke-static {{v1, v0}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I
    return-void
.end method

.method public static onTerminateHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)V
    .locals 1

    const/4 v0, 0x0
    invoke-static {{p0, v0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->resetHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;)V
    return-void
.end method

.method public static getFilterName(Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    if-eqz p0, :cond_none

    const-string v0, "pop-color"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_neg
    const-string v0, "\u7406\u5149 GR \u6b63\u7247"
    return-object v0

    :cond_check_neg
    const-string v0, "retro-photo"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_hcbw
    const-string v0, "\u7406\u5149\u8d1f\u7247"
    return-object v0

    :cond_check_hcbw
    const-string v0, "richtone-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_daido
    const-string v0, "\u9ad8\u5bf9\u6bd4\u9ed1\u767d"
    return-object v0

    :cond_check_daido
    const-string v0, "rough-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_xpro
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98ce"
    return-object v0

    :cond_check_xpro
    const-string v0, "watercolor"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_none
    const-string v0, "\u6b63\u8d1f\u9006\u51b2"
    return-object v0

    :cond_none
    const/4 v0, 0x0
    return-object v0
.end method

.method public static getFilterGuide(Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    if-eqz p0, :cond_none

    const-string v0, "pop-color"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_neg
    const-string v0, "\u7406\u5149 GR \u6b63\u7247\u8272\u5f69\u6548\u679c (Ricoh Positive Film)"
    return-object v0

    :cond_check_neg
    const-string v0, "retro-photo"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_hcbw
    const-string v0, "\u7406\u5149\u8d1f\u7247\u80f6\u7247\u8272\u5f69\u6548\u679c (Ricoh Negative Film)"
    return-object v0

    :cond_check_hcbw
    const-string v0, "richtone-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_daido
    const-string v0, "\u9ad8\u5bf9\u6bd4\u9ed1\u767d\u80f6\u7247\u6548\u679c (Ricoh High Contrast B&W)"
    return-object v0

    :cond_check_daido
    const-string v0, "rough-mono"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_check_xpro
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98ce\u7c97\u7c8a\u9ad8\u5bf9\u6bd4\u9ed1\u767d (Moriyama Daido B&W)"
    return-object v0

    :cond_check_xpro
    const-string v0, "watercolor"
    invoke-virtual {{p0, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_none
    const-string v0, "\u6b63\u8d1f\u9006\u51b2\u72ec\u7279\u8272\u5f69\u53cd\u51b2\u6548\u679c (Ricoh Cross Process)"
    return-object v0

    :cond_none
    const/4 v0, 0x0
    return-object v0
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

