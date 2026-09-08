import glob
import math

def pts_to_bytes(pts):
    b = bytearray()
    for v in pts:
        b.append(v & 0xff)
        b.append((v >> 8) & 0xff)
    return b

def gen_curve_pos():
    pts = []
    for i in range(1024):
        x = (i / 1023.0 - 0.48) * -8.0
        y = 1.0 / (1.0 + math.exp(x))
        y0 = 1.0 / (1.0 + math.exp(0.48 * 8.0))
        y1 = 1.0 / (1.0 + math.exp(-0.52 * 8.0))
        norm = (y - y0) / (y1 - y0) * 1023.0
        pts.append(max(0, min(1023, round(norm))))
    return pts

def gen_curve_neg():
    pts = []
    for i in range(1024):
        t = i / 1023.0
        s = t * t * (3 - 2 * t)
        val = 35 + s * (990 - 35)
        pts.append(max(0, min(1023, round(val))))
    return pts

def gen_curve_hcbw():
    pts = []
    for i in range(1024):
        x = (i / 1023.0 - 0.50) * -11.0
        y = 1.0 / (1.0 + math.exp(x))
        y0 = 1.0 / (1.0 + math.exp(0.50 * 11.0))
        y1 = 1.0 / (1.0 + math.exp(-0.50 * 11.0))
        norm = (y - y0) / (y1 - y0) * 1023.0
        pts.append(max(0, min(1023, round(norm))))
    return pts

def gen_curve_daido():
    pts = []
    for i in range(1024):
        x = (i / 1023.0 - 0.50) * -16.0
        y = 1.0 / (1.0 + math.exp(x))
        y0 = 1.0 / (1.0 + math.exp(0.50 * 16.0))
        y1 = 1.0 / (1.0 + math.exp(-0.50 * 16.0))
        norm = (y - y0) / (y1 - y0) * 1023.0
        pts.append(max(0, min(1023, round(norm))))
    return pts

def gen_curve_xpro():
    pts = []
    for i in range(1024):
        t = i / 1023.0
        s = 1.0 / (1.0 + math.exp(-(t - 0.45) * 10.0))
        s0 = 1.0 / (1.0 + math.exp(0.45 * 10.0))
        s1 = 1.0 / (1.0 + math.exp(-0.55 * 10.0))
        norm = (s - s0) / (s1 - s0) * 1023.0
        pts.append(max(0, min(1023, round(norm))))
    return pts

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

    const/4 v0, 0x0
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaPos:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaNeg:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaHcbw:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaDaido:[B
    sput-object v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sGammaXpro:[B

    const/16 v0, 0x9

    # 1. Positive Film Matrix
    new-array v1, v0, [I
    fill-array-data v1, :array_pos_matrix
    sput-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sPositiveFilmMatrix:[I

    # 2. Negative Film Matrix
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

    # 5. Cross Process Matrix
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
        0x49c
        -0x6e
        -0x2e
        -0x32
        0x474
        -0x42
        -0x1e
        -0x50
        0x46e
    .end array-data

    :array_neg_matrix
    .array-data 4
        0x410
        -0xa
        -0xa
        -0x1e
        0x3f2
        0xa
        -0x28
        -0x14
        0x3e8
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
        0x47e
        -0x64
        0x1e
        0x64
        0x44c
        -0x78
        -0x50
        0x32
        0x406
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

.method public static applyHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;Ljava/lang/String;)Z
    .locals 5
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
    invoke-virtual {{v2, v3}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V

    :cond_4
    # 2. Commit parameters to hardware HAL
    invoke-virtual {{v1, p1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V

    # 3. Write 1024-point 10-bit Gamma Table
    invoke-static {{p0}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getCameraEx(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)Lcom/sony/scalar/hardware/CameraEx;
    move-result-object v2
    if-eqz v2, :cond_5
    invoke-virtual {{v2}}, Lcom/sony/scalar/hardware/CameraEx;->createGammaTable()Lcom/sony/scalar/hardware/CameraEx$GammaTable;
    move-result-object v3
    if-eqz v3, :cond_5
    const/4 v4, 0x1
    invoke-virtual {{v3, v4}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->setPictureEffectGammaForceOff(Z)V

    invoke-static {{p2}}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getGammaBytes(Ljava/lang/String;)[B
    move-result-object v4
    if-eqz v4, :cond_5
    new-instance v0, Ljava/io/ByteArrayInputStream;
    invoke-direct {{v0, v4}}, Ljava/io/ByteArrayInputStream;-><init>([B)V
    invoke-virtual {{v3, v0}}, Lcom/sony/scalar/hardware/CameraEx$GammaTable;->write(Ljava/io/InputStream;)I
    invoke-virtual {{v2, v3}}, Lcom/sony/scalar/hardware/CameraEx;->setExtendedGammaTable(Lcom/sony/scalar/hardware/CameraEx$GammaTable;)V

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
    sget-object v2, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIdentityMatrix:[I
    invoke-virtual {{v1, v2}}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    invoke-virtual {{v0, p1}}, Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;->setParameters(Landroid/util/Pair;)V

    :cond_3
    const/4 v0, 0x0
    sput-boolean v0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->sIsRicohActive:Z
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :catch_0

    return-void

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
    const-string v0, "\u68ee\u5c71\u5927\u9053\u98ce\u7c97\u7c9e\u9ad8\u5bf9\u6bd4\u9ed1\u767d (Moriyama Daido B&W)"
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

