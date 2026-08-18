define Device/abt_asr3000
  DEVICE_VENDOR := ABT
  DEVICE_MODEL := ASR3000
  DEVICE_DTS := mt7981b-abt-asr3000
  IMAGES += factory.bin
  IMAGE/factory.bin := append-ubi
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
endef
TARGET_DEVICES += abt_asr3000

define Device/tplink_wma301
  DEVICE_VENDOR := TP-Link
  DEVICE_MODEL := WMA301
  DEVICE_DTS := mt7981b-tplink-wma301
  DEVICE_DTS_DIR := ../dts
  SUPPORTED_DEVICES += mediatek,mt7981-spim-snand-rfb
  DEVICE_PACKAGES := kmod-mt7915e kmod-mt7981-firmware mt7981-wo-firmware
  UBINIZE_OPTS := -E 5
  BLOCKSIZE := 128k
  PAGESIZE := 2048
  IMAGE_SIZE := 116736k
  KERNEL_IN_UBI := 1
  IMAGES += factory.bin
  IMAGE/factory.bin := append-ubi | check-size $$(IMAGE_SIZE)
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
  KERNEL = kernel-bin | lzma | fit lzma dtb
  KERNEL_INITRAMFS = kernel-bin | lzma | fit lzma dtb with-initrd
endef
TARGET_DEVICES += tplink_wma301

define Device/tplink_wma301-stock
  DEVICE_VENDOR := TP-Link
  DEVICE_MODEL := WMA301
  DEVICE_VARIANT := (stock layout)
  DEVICE_DTS := mt7981b-tplink-wma301-stock
  IMAGES += factory.bin
  IMAGE/factory.bin := append-ubi
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
endef
TARGET_DEVICES += tplink_wma301-stock

define Device/tplink_wma301-ubootmod
  DEVICE_VENDOR := TP-Link
  DEVICE_MODEL := WMA301
  DEVICE_VARIANT := (OpenWrt layout)
  DEVICE_DTS := mt7981b-tplink-wma301-ubootmod
  IMAGES := sysupgrade.itb
  KERNEL_INITRAMFS_SUFFIX := -recovery.itb
endef
TARGET_DEVICES += tplink_wma301-ubootmod
