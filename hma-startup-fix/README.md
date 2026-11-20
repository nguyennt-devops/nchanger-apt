# HMA Helper 1.0.1

Rootless Debian package `store.nguyennt.hmaheapfix` for the observed Go startup heap crash in HMA VPN 6.0.1 build 13689. Requires the original framework SHA-256 `1b092b0e3fbe1d5f8837d08f7241aea195aec27fc3d01d857acfbf799abb8f0a`.

Add `https://raw.githubusercontent.com/nguyennt-devops/nchanger-apt/main/repo/` in Sileo and install **HMA Helper**. This HTTPS source was refreshed successfully by APT on the test iPhone and returned the published package filename, size and SHA-256. The custom domain `https://repo.nguyennt.store/repo/` serves the package but currently returns HTTP 503 for absent `InRelease` / `Release.gpg`; use the Raw URL while that host issue remains. HMA must already be installed separately. An unsupported or manually modified framework is refused before patching. Remove the package in Sileo to restore the backed-up original framework, unless HMA has changed since installation.

Verified on iPhone 8 / iOS 16.7.16 / palera1n rootless. Install, same-version reinstall, removal with original-hash restoration, and reinstall were tested with dpkg on that device. The resulting app opens to its subscription screen. Other devices, VPN account flows, VPN connection and the embedded MimicHMA extension are unverified. The extension is not modified. This is not a subscription unlock.

This package contains a source-built compatibility shim, shell maintainer scripts and a 64-byte Mach-O header delta. It does not redistribute HMA executable/framework code, user data or credentials. The shim changes only the mmap import in MimicNetworking and uses a non-overwriting Mach VM reservation before mapping Go heap addresses below 8 GiB. It does not disable runtime bounds checks or hook mmap globally.

Backup: `/var/jb/var/lib/hma-heap-fix/MimicNetworking.original`. Backups remain after package removal. App updates can remove the patch; only reinstall if the framework still has the supported hash.

The source in this directory corresponds to the published installer and shim. Build the shim for arm64 iOS with Zig/Clang, sign it with ldid in the jailbreak environment, and use the included Python package builder with an independently supplied original framework and the signed shim. No original HMA files are included here.
