# TP-Link WMA301 V2 — ImmortalWrt Verified Build

هذه النسخة تعالج الخطأ الذي كان يسمح لـ `make defconfig` بالانتقال إلى جهاز آخر مثل `ABT ASR3000` ثم نشر ملفاته وكأنها WMA301.

## التصحيح الأساسي

المصدر الحالي يستخدم:

```text
Target:    mediatek
Subtarget: filogic
```

والاختيار الصحيح للصورة يكون بواسطة أحد الرموز التالية، حسب تخطيط الفلاش الفعلي:

```text
CONFIG_TARGET_mediatek_filogic_DEVICE_tplink_wma301=y
CONFIG_TARGET_mediatek_filogic_DEVICE_tplink_wma301-stock=y
CONFIG_TARGET_mediatek_filogic_DEVICE_tplink_wma301-ubootmod=y
```

لا تستخدم الرموز القديمة:

```text
CONFIG_TARGET_mediatek_mt7981=y
CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_...
```

## ملفات الإعداد

- `configs/tplink_wma301.config` — ملف تعريف المصدر `tplink_wma301`.
- `configs/tplink_wma301-stock.config` — تخطيط المصدر المسمى صراحةً `stock layout`.
- `configs/tplink_wma301-ubootmod.config` — تخطيط OpenWrt U-Boot، وينتج ملفات bootloader خاصة بهذا التخطيط.
- `.config` — نسخة افتراضية من `tplink_wma301.config` للمستخدم الذي يبني يدويًا.

> هذه الملفات الثلاثة ليست بدائل قابلة للتبديل أثناء التفليش. اختر الملف المطابق لتقسيمات الجهاز الحالية وطريقة الإقلاع الحالية.

## البناء بواسطة GitHub Actions

من **Actions → Build TP-Link WMA301 V2 ImmortalWrt (Verified) → Run workflow** اختر `device_profile` المطلوب.

النشر إلى GitHub Release معطل افتراضيًا. حتى عند تفعيله لا يحدث النشر إلا بعد مرور بوابات التحقق.

## بوابات الأمان المضافة

1. تثبيت فرع المصدر صراحةً على `openwrt-24.10-6.6` بدل الاعتماد على الفرع الافتراضي.
2. التأكد أن المصدر نفسه يحتوي على تعريف الجهاز المطلوب داخل `filogic.mk`.
3. تشغيل `make defconfig` ثم التحقق من أن **صورة واحدة فقط** من `mediatek/filogic` هي المحددة وهي WMA301 المطلوبة.
4. رفض البناء فورًا إذا ظهر `ABT ASR3000` في `.config`.
5. إعادة فحص الهدف بعد اكتمال البناء.
6. جمع ملفات WMA301 المحددة فقط، وعدم نسخ كل ملفات `*.bin` من الهدف.
7. عدم جمع ملفات BL2 العامة مثل `mt7981-ram-ddr3-bl2.bin` وملفات MT7986/MT7988.
8. التحقق من `profiles.json` عندما يكون موجودًا.
9. اشتراط وجود مخرجات الصورة الأساسية المتوقعة لكل profile.
10. إنشاء `SHA256SUMS-WMA301.txt` والتحقق منه قبل رفع الـArtifact أو Release.
11. حفظ `effective.config` و`SOURCE.txt` و`WMA301-BUILD-MANIFEST.json` مع كل بناء لتدقيق المصدر والهدف لاحقًا.

## البناء اليدوي

مثال للملف الأساسي:

```bash
git clone --depth 1 --single-branch --branch openwrt-24.10-6.6 \
  https://github.com/zeromake/immortalwrt-mt798x-6.6.git immortalwrt

cd immortalwrt
./scripts/feeds update -a
./scripts/feeds install -a
cp ../configs/tplink_wma301.config .config
make defconfig
../scripts/validate-config.sh tplink_wma301 .
make -j"$(nproc)"
../scripts/validate-config.sh tplink_wma301 .
```

بعد البناء استخدم أداة الجمع:

```bash
python3 ../scripts/collect-firmware.py \
  --profile tplink_wma301 \
  --source-dir . \
  --output-dir ../firmware
```

## ملاحظة تفليش مهمة

هذه الحزمة **تبني Firmware وتتحقق من أن الناتج خاص بـWMA301**، لكنها لا تستطيع تحديد تخطيط الفلاش الموجود فعليًا داخل الراوتر من دون فحص الجهاز نفسه. لا تفلش `stock` أو `ubootmod` أو ملفات bootloader اعتمادًا على الاسم فقط.
