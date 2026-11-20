HMA Helper 1.0.1

Rootless jailbreak package, architecture iphoneos-arm64, iOS 15.x-16.x.
Requires an existing HMA VPN 6.0.1 build 13689 installation with SHA-256:
1b092b0e3fbe1d5f8837d08f7241aea195aec27fc3d01d857acfbf799abb8f0a

Fixes the observed Go 1.16.7-pqtls startup heap reservation failure.
Verified on iPhone 8, iOS 16.7.16, palera1n rootless. Other devices unverified.
VPN connection and MimicHMA tunnel extension are not verified or modified.

This package contains only a compatibility shim, maintainer scripts and a
64-byte Mach-O header change. It does not contain HMA app executables,
framework code, account data or an app license. Install HMA separately.

Installation verifies the original framework, saves a backup under
/var/jb/var/lib/hma-heap-fix, applies the header dependency, signs the
framework with ldid and closes HMA so the next launch uses the fix.
The shim reserves low addresses without overwriting existing mappings.

Remove this package in Sileo to restore the original framework. If HMA was
updated/replaced after patching, removal leaves the changed app untouched.
Original backups are retained. App updates may remove the patch; reinstall
only if the new app still has the exact supported framework hash.

Already manually patched HMA installations must be restored to the original
framework before installing this package; unmanaged modifications are refused.
Original HMA entitlements and data are not changed. No subscription bypass.
