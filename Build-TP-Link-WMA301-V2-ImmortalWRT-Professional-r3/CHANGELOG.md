# Changelog

## R3

- الاعتماد على `defconfig/mt7981-ax3000.config` من المصدر في وقت البناء بدل `.config` ثابت.
- تصحيح النموذج الحقيقي للمصدر: `CONFIG_TARGET_mediatek_mt7981=y` meta-target مع per-device selector تحت `CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_*`.
- إزالة namespace الخاطئ `CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_*`.
- إضافة `prepare-config.py` لإزالة جميع الأجهزة من defconfig ثم تحديد WMA301 واحد فقط.
- إصلاح التحقق من `SUBTARGETS:=filogic ...` عندما يكون filogic أول عنصر.
- إضافة source-contract validation لعقد WMA301 وbootloader.
- فصل صلاحيات البناء عن صلاحيات النشر.
- التحقق من checksums الأصلية للهدف قبل تجميع الصور.
- منع نشر ASR3000 أو layout شقيق ضمن بناء WMA301 المحدد.
- إضافة اختبارات سلامة إيجابية وسلبية.
