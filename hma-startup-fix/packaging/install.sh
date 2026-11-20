#!/var/jb/bin/sh
set -eu
PATH=/var/jb/usr/bin:/var/jb/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
PKG=/var/jb/usr/libexec/hma-heap-fix
STATE=/var/jb/var/lib/hma-heap-fix
die() { echo "HMA Helper: $*" >&2; exit 1; }
hash() { sha256sum "$1" | cut -d ' ' -f 1; }
mkdir -p "$STATE"
chmod 700 "$STATE"
[ -f "$PKG/HmaGoHeapFix.dylib" ] || die 'helper missing'
command -v ldid >/dev/null || die 'ldid is required'
APPS=$(find /private/var/containers/Bundle/Application -mindepth 2 -maxdepth 2 -type d -name HMASecureVPN.app)
COUNT=$(printf '%s\n' "$APPS" | grep -c 'HMASecureVPN.app$' || true)
[ "$COUNT" = 1 ] || die 'install exactly one HMA VPN 6.0.1 build 13689 first'
APP=$APPS
FRAME=$APP/Frameworks/MimicNetworking.framework
TARGET=$FRAME/MimicNetworking
[ -f "$TARGET" ] || die 'MimicNetworking not found'
CURRENT=$(hash "$TARGET")
ORIGINAL=1b092b0e3fbe1d5f8837d08f7241aea195aec27fc3d01d857acfbf799abb8f0a
if [ -f "$STATE/app-path" ] && [ -f "$STATE/installed.sha256" ]; then
    PREVIOUS=$(cat "$STATE/app-path")
    INSTALLED=$(cat "$STATE/installed.sha256")
    if [ "$PREVIOUS" = "$APP" ] && [ "$CURRENT" = "$INSTALLED" ]; then
        if [ -f "$FRAME/HmaGoHeapFix.dylib" ] && [ "$(hash "$FRAME/HmaGoHeapFix.dylib")" = "$(hash "$PKG/HmaGoHeapFix.dylib")" ]; then
            echo 'HMA Helper is already installed.'
            exit 0
        fi
        die 'helper changed; refusing to overwrite existing installation'
    fi
fi
[ "$CURRENT" = "$ORIGINAL" ] || die "unsupported or modified HMA framework ($CURRENT); no changes made"
[ ! -e "$FRAME/HmaGoHeapFix.dylib" ] || die 'an unmanaged helper exists; no changes made'
if [ -f "$STATE/MimicNetworking.original" ]; then
    [ "$(hash "$STATE/MimicNetworking.original")" = "$ORIGINAL" ] || die 'backup hash mismatch'
else
    cp -p "$TARGET" "$STATE/MimicNetworking.original"
    [ "$(hash "$STATE/MimicNetworking.original")" = "$ORIGINAL" ] || die 'backup verification failed'
fi
printf '%s\n' "$APP" > "$STATE/app-path"
TMP=$FRAME/.MimicNetworking.hmaheap-new
HELPER_TMP=$FRAME/.HmaGoHeapFix.hmaheap-new
COMMITTED=0
cleanup() {
    rm -f "$TMP" "$HELPER_TMP"
    if [ "$COMMITTED" = 0 ]; then
        rm -f "$FRAME/HmaGoHeapFix.dylib"
        echo 'HMA Helper: installation incomplete; original framework retained.' >&2
    fi
}
trap cleanup EXIT
cp -p "$STATE/MimicNetworking.original" "$TMP"
dd if="$PKG/header-counts.bin" of="$TMP" bs=1 seek=16 count=8 conv=notrunc 2>/dev/null
dd if="$PKG/load-command.bin" of="$TMP" bs=1 seek=5832 count=56 conv=notrunc 2>/dev/null
[ "$(hash "$TMP")" = 76aa2afe5d494622cc314476226be7b4a7a715e2e293858ae63538fe25e12792 ] || die 'patched bytes failed verification'
ldid -S "$TMP"
cp "$PKG/HmaGoHeapFix.dylib" "$HELPER_TMP"
chown _installd:_installd "$TMP" "$HELPER_TMP"
chmod 644 "$TMP" "$HELPER_TMP"
EXPECTED=$(hash "$TMP")
printf '%s\n' "$EXPECTED" > "$STATE/installed.sha256"
printf '%s\n' "$(hash "$HELPER_TMP")" > "$STATE/helper.sha256"
killall HMASecureVPN >/dev/null 2>&1 || true
mv "$HELPER_TMP" "$FRAME/HmaGoHeapFix.dylib"
mv "$TMP" "$TARGET"
COMMITTED=1
[ "$(hash "$TARGET")" = "$EXPECTED" ] || die 'installed framework verification failed; backup kept'
echo 'HMA Helper installed. Open HMA VPN normally.'
