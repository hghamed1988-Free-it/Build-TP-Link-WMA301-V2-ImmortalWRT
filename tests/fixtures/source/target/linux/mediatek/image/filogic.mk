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
  IMAGE/factory.bin := append-ubi | check-size $$$$(IMAGE_SIZE)
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
endef
TARGET_DEVICES += tplink_wma301
define Device/tplink_wma301-stock
  DEVICE_VENDOR := TP-Link
  DEVICE_MODEL := WMA301
  DEVICE_VARIANT := (stock layout)
  DEVICE_DTS := mt7981b-tplink-wma301-stock
  DEVICE_DTS_DIR := ../dts
  SUPPORTED_DEVICES += mediatek,mt7981-spim-snand-rfb
  DEVICE_PACKAGES := kmod-mt7915e kmod-mt7981-firmware mt7981-wo-firmware
  UBINIZE_OPTS := -E 5
  BLOCKSIZE := 128k
  PAGESIZE := 2048
  IMAGE_SIZE := 65536k
  KERNEL_IN_UBI := 1
  IMAGES += factory.bin
  IMAGE/factory.bin := append-ubi | check-size $$$$(IMAGE_SIZE)
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
endef
TARGET_DEVICES += tplink_wma301-stock
define Device/tplink_wma301-ubootmod
  DEVICE_VENDOR := TP-Link
  DEVICE_MODEL := WMA301
  DEVICE_VARIANT := (OpenWrt layout)
  DEVICE_DTS := mt7981b-tplink-wma301-ubootmod
  SUPPORTED_DEVICES += tplink,wma301 mediatek,mt7981
  DEVICE_DTS_DIR := ../dts
  DEVICE_PACKAGES := kmod-mt7915e kmod-mt7981-firmware mt7981-wo-firmware
  UBINIZE_OPTS := -E 5
  BLOCKSIZE := 128k
  PAGESIZE := 2048
  KERNEL_IN_UBI := 1
  UBOOTENV_IN_UBI := 1
  IMAGES := sysupgrade.itb
  KERNEL_INITRAMFS_SUFFIX := -recovery.itb
  KERNEL := kernel-bin | gzip
  IMAGE/sysupgrade.itb := append-kernel | fit gzip
  ARTIFACTS := preloader.bin bl31-uboot.fip
  ARTIFACT/preloader.bin := mt7981-bl2 spim-nand-ddr3
  ARTIFACT/bl31-uboot.fip := mt7981-bl31-uboot tplink_wma301
endef
TARGET_DEVICES += tplink_wma301-ubootmod
