# TP-Link WMA301 V2 — ImmortalWrt Verified Build R3

هذه الحزمة مخصصة **لبناء** ImmortalWrt لجهاز TP-Link WMA301 V2 مع بوابات تحقق تمنع نشر Firmware لجهاز آخر. وهي لا تقوم بالتفليش تلقائيًا.

## التصحيح الدقيق لنموذج Target الحالي

المصدر الحالي يعرّف MediaTek subtarget باسم `filogic`، لكن ملفه القياسي `defconfig/mt7981-ax3000.config` ما زال يستخدم **MT7981 meta-target** بهذه الصورة:

```text
CONFIG_TARGET_mediatek=y
CONFIG_TARGET_mediatek_mt7981=y
CONFIG_TARGET_MULTI_PROFILE=y
CONFIG_TARGET_PER_DEVICE_ROOTFS=y
CONFIG_HAS_SUBTARGETS=y
```

أما اختيار الجهاز نفسه فيستخدم namespace مختلفًا:

```text
CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_tplink_wma301=y
```

ولهذا كان الرمز القديم التالي خاطئًا:

```text
CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_tplink_wma301=y
```

R3 لا يحتفظ بملف `.config` ثابت قد يصبح قديمًا. بدلًا من ذلك، يقرأ `defconfig/mt7981-ax3000.config` **من المصدر الذي تم استنساخه في نفس عملية البناء**، يزيل كل الأجهزة المحددة مسبقًا، ثم يضيف WMA301 واحدًا فقط.

## Profiles المدعومة

- `tplink_wma301`
- `tplink_wma301-stock` — `stock layout`
- `tplink_wma301-ubootmod` — `OpenWrt layout`

## بوابات الأمان في R3

1. التشغيل يدوي فقط عبر `workflow_dispatch`.
2. المصدر ثابت على branch `openwrt-24.10-6.6` ويُسجل commit الفعلي مع الناتج.
3. `verify-source.py` يتحقق من:
   - وجود `filogic` في MediaTek target.
   - عقد `defconfig/mt7981-ax3000.config` الحالي.
   - تعريف WMA301 وDTS والمخرجات الحرجة لكل layout.
   - عقد bootloader لـ `ubootmod`، بما فيها DDR3 preloader المحدد في المصدر.
4. `prepare-config.py` يولد config من defconfig الرسمي للمصدر نفسه، بدل ملف config قديم منفصل.
5. إزالة جميع الأجهزة المسبقة من defconfig وإضافة WMA301 المختار فقط.
6. `make defconfig` يعقبه تحقق بأن جهازًا واحدًا فقط محدد وهو WMA301 المطلوب.
7. رفض صريح لـ `ABT ASR3000` في config وفي مخرجات البناء.
8. عدم استخدام `find ... *.bin` لجمع كل ملفات target.
9. جمع الملفات التي تحمل profile المختار فقط من `bin/targets/mediatek/filogic`.
10. التحقق من كل صورة مقابل `sha256sums` الأصلي لنظام بناء ImmortalWrt قبل النشر.
11. إنشاء checksum مستقل `SHA256SUMS-WMA301.txt` للناتج المنشور.
12. فصل صلاحيات GitHub: Job البناء `contents: read`، وJob النشر فقط يحصل على `contents: write` عند طلب Release.
13. Release معطل افتراضيًا.
14. اختبارات سلبية تتأكد أن ASR3000 وتغير عقد bootloader يؤديان إلى فشل العملية.

## الاستخدام بواسطة GitHub Actions

1. ارفع محتويات المجلد إلى مستودع GitHub.
2. افتح **Actions**.
3. شغّل **Build TP-Link WMA301 V2 ImmortalWrt (Verified R3)**.
4. اختر `device_profile` الصحيح.
5. `include_initramfs=true` افتراضيًا؛ يمكن تعطيله إذا لم تكن تحتاج صورة recovery/initramfs.
6. اترك `publish_release=false` في أول بناء.
7. بعد نجاح جميع الخطوات نزّل Artifact وراجع:
   - `SOURCE.txt`
   - `effective.config`
   - `WMA301-BUILD-MANIFEST.json`
   - `SHA256SUMS-WMA301.txt`

## البناء المحلي

بعد تثبيت متطلبات ImmortalWrt:

```bash
./scripts/build-local.sh tplink_wma301
```

لتعطيل initramfs:

```bash
INCLUDE_INITRAMFS=false ./scripts/build-local.sh tplink_wma301
```

## تخصيص الحزم

يمكن إضافة خيارات إضافية في:

```text
configs/extra.config
```

ويُمنع هذا الملف من تغيير target/device selection؛ اختيار WMA301 يظل تحت سيطرة `prepare-config.py`.

## تحذير التفليش

نجاح R3 يثبت أن الناتج بُني لتعريف WMA301 المختار وفق المصدر، لكنه **لا يثبت تخطيط الفلاش الموجود فعليًا في جهازك**. `stock` و`ubootmod` غير قابلين للتبديل. لا تكتب `preloader.bin` أو `bl31-uboot.fip` على الراوتر قبل التأكد المستقل من bootloader وتقسيمات الفلاش الحالية.
