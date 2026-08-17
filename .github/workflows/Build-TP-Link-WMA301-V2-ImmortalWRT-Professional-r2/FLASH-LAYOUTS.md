# WMA301 flash-layout profiles

المصدر المحدد في هذا المشروع يحتوي حاليًا على ثلاثة تعريفات منفصلة لـ TP-Link WMA301:

| Profile | وصف المصدر | المخرجات الأساسية المتوقعة |
|---|---|---|
| `tplink_wma301` | WMA301 profile الأساسي | `factory.bin`, `sysupgrade.bin`, وinitramfs عند تفعيله |
| `tplink_wma301-stock` | `stock layout` | `factory.bin`, `sysupgrade.bin`, وinitramfs عند تفعيله |
| `tplink_wma301-ubootmod` | `OpenWrt layout` | `sysupgrade.itb`, recovery initramfs، `preloader.bin`, `bl31-uboot.fip` |

## قاعدة الأمان

لا تستخدم ملفات `preloader.bin` أو `bl31-uboot.fip` إلا عندما يكون الجهاز بالفعل على التخطيط المقصود وتوجد خطوات تثبيت مؤكدة لذلك التخطيط. خطأ bootloader أخطر من خطأ ترقية نظام عادي.
