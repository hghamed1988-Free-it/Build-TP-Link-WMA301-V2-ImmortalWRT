# Flash safety

R7 builds only the upstream base profile `tplink_wma301`.

Expected base-profile outputs:

- `*-tplink_wma301-squashfs-factory.bin`
- `*-tplink_wma301-squashfs-sysupgrade.bin`
- `*-tplink_wma301-initramfs-kernel.bin` when initramfs is enabled

The upstream tree also contains two **different flash-layout profiles**:

- `tplink_wma301-stock` — stock layout
- `tplink_wma301-ubootmod` — OpenWrt U-Boot layout

Those profiles are intentionally excluded from R7 to avoid accidentally building a layout that does not match the physical router.

Do not flash a file merely because the model name contains WMA301. Before flashing, verify the router hardware/version label and its current bootloader/flash layout. `factory`, `sysupgrade`, stock-layout, and U-Boot-modified-layout images are not interchangeable.
