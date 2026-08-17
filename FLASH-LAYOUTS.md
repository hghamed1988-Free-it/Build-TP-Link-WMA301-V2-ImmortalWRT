# WMA301 flash-layout contract

| Profile | تعريف المصدر | المخرجات التي تشترطها R3 |
|---|---|---|
| `tplink_wma301` | WMA301 الأساسي | `factory.bin`, `sysupgrade.bin` |
| `tplink_wma301-stock` | `stock layout` | `factory.bin`, `sysupgrade.bin` |
| `tplink_wma301-ubootmod` | `OpenWrt layout` | `sysupgrade.itb`, `preloader.bin`, `bl31-uboot.fip` |

عند تفعيل initramfs قد تظهر صور recovery/initramfs إضافية تحمل اسم الـprofile، ويتم جمعها فقط إذا كانت من نفس profile المختار ومسجلة في checksums الخاصة بالهدف.

## قاعدة الأمان

- لا تعتمد على اسم الجهاز وحده لتحديد layout الحالي.
- لا تستخدم ملفات bootloader من `ubootmod` على stock layout دون مسار تثبيت موثق ومؤكد للجهاز نفسه.
- هذه الحزمة لا تقوم بالتفليش؛ مهمتها بناء الناتج والتحقق من هوية الهدف والمخرجات.
