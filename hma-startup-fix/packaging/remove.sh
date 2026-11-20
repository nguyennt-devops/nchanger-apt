#!/var/jb/bin/sh
set -eu
PATH=/var/jb/usr/bin:/var/jb/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
STATE=/var/jb/var/lib/hma-heap-fix
hash() { sha256sum "$1" | cut -d ' ' -f 1; }
[ -f "$STATE/app-path" ] || exit 0
APP=$(cat "$STATE/app-path")
case "$APP" in /private/var/containers/Bundle/Application/*/HMASecureVPN.app) ;; *) echo 'Invalid saved HMA path' >&2; exit 1;; esac
FRAME=$APP/Frameworks/MimicNetworking.framework
TARGET=$FRAME/MimicNetworking
if [ ! -f "$TARGET" ]; then echo 'HMA no longer installed; backup kept.'; exit 0; fi
if [ ! -f "$STATE/installed.sha256" ]; then echo 'No installed patch recorded; backup kept.'; exit 0; fi
CURRENT=$(hash "$TARGET")
EXPECTED=$(cat "$STATE/installed.sha256")
if [ "$CURRENT" != "$EXPECTED" ]; then
    echo 'HMA framework changed after patch; leaving current app untouched. Backup kept.'
    exit 0
fi
[ "$(hash "$STATE/MimicNetworking.original")" = 1b092b0e3fbe1d5f8837d08f7241aea195aec27fc3d01d857acfbf799abb8f0a ] || { echo 'Original backup invalid; refusing removal' >&2; exit 1; }
TMP=$FRAME/.MimicNetworking.hmaheap-restore
cp -p "$STATE/MimicNetworking.original" "$TMP"
killall HMASecureVPN >/dev/null 2>&1 || true
mv "$TMP" "$TARGET"
if [ -f "$FRAME/HmaGoHeapFix.dylib" ] && [ -f "$STATE/helper.sha256" ] && [ "$(hash "$FRAME/HmaGoHeapFix.dylib")" = "$(cat "$STATE/helper.sha256")" ]; then
    rm -f "$FRAME/HmaGoHeapFix.dylib"
fi
rm -f "$STATE/installed.sha256" "$STATE/helper.sha256"
echo 'Original HMA framework restored. Original backup retained.'
