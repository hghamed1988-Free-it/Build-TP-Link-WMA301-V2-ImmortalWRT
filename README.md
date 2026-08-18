# TP-Link WMA301 — ImmortalWRT Professional R9.1 Self-Contained — Correct Device Selection

هذه النسخة تعالج مباشرة خطأ R8: `No such file or directory: scripts/device_profiles.py`.

## أهم تغيير
R9 لا تعتمد على أي ملفات `scripts/*.py` في مستودعك. كل منطق التحقق مضمّن داخل `.github/workflows/build.yml` ويُنشأ مؤقتًا على GitHub Runner.

لذلك تحتاج إلى استبدال ملف واحد فقط: `.github/workflows/build.yml`.

## البروفيلات الآمنة
- `tplink_wma301`
- `tplink_wma301-stock`
- `tplink_wma301_2.1`

`tplink_wma301-ubootmod` غير معروض في Workflow العادي لأنه يغيّر تخطيط U-Boot/OpenWrt.

## بوابات التحقق
- تحقق تعريف الجهاز من المصدر الحالي.
- target نهائي `mediatek/filogic`.
- جهاز واحد فقط ومطابق للبروفايل المطلوب.
- رفض ASR3000 وubootmod وأي sibling profile.
- تحقق `profiles.json` و`sha256sums`.
- Manifest وSHA-256 نهائي قبل رفع Artifact.

## الاستخدام
استبدل `.github/workflows/build.yml` بملف R9، ثم شغّل Run جديدًا من Actions. لا تستخدم Re-run لتشغيل قديم.


## R9.1 change only
The workflow is otherwise kept the same. Device selection now uses the single-profile symbol `CONFIG_TARGET_mediatek_filogic_DEVICE_<profile>=y`; the multi-profile `CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_<profile>=y` symbol is explicitly removed/rejected.
