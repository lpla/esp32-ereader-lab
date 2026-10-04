# Third-party inputs

The MIT license applies to this repository's harness source and documentation. It does not grant rights to downloaded emulator binaries/ROMs, stock firmware, or vendor UI artwork/text shown in captured screens.

Espressif QEMU and esp-emulator packages are obtained from their original release URLs; consult their distributions for applicable terms. X3/X4 stock fixtures are obtained from the public third-party repository recorded in `downloads/manifest.json`, which labels them as stock Xteink firmware. Their manufacturer authenticity was not independently authenticated. X4 Pro stock and Licorice fixtures come from the manufacturer's public XTCloud full-package API; locally computed hashes pin the downloads, and no publisher checksum/signature was supplied. No stock application binary or emulator executable is redistributed here.

The C3 networking experiment fetches CrossPoint PR #3612 source at an immutable commit and verifies its SHA256. That downloaded source is excluded from Git and retains the upstream project's license. Only the independent probe and logging adapter are bundled here. Manuals and Reddit discussions are linked as research sources; full documents/posts are not redistributed.

`evidence/` contains records of local experiments and screenshots of executed firmware. These establish only the labeled emulator/adapter observations, not physical-device behavior.
