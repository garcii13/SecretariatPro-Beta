export const platforms = ['windows-x64', 'macos-arm64', 'macos-x86_64'];

export async function detectInstaller(navigator) {
  const ua = navigator.userAgent || '';
  // iPad desktop mode also advertises MacIntel. Never offer a desktop installer.
  if (/Android|iPhone|iPad|iPod/i.test(ua) ||
      (/Mac/i.test(navigator.platform || '') && navigator.maxTouchPoints > 1)) return null;
  let hints = navigator.userAgentData || {};
  try {
    if (hints.getHighEntropyValues) {
      hints = { ...hints, ...await hints.getHighEntropyValues(['platform', 'architecture', 'bitness']) };
    }
  } catch { /* Browser permissions can withhold architecture. Keep manual choices. */ }
  if (hints.mobile) return null;
  const os = hints.platform || (/Windows/i.test(ua) ? 'Windows' : /Macintosh|Mac OS X/i.test(ua) ? 'macOS' : '');
  if (os === 'Windows') {
    if (/arm/i.test(hints.architecture || '') || /ARM|aarch64/i.test(ua)) return null;
    if (hints.bitness === '32' || /Win32|i[3-6]86|WOW64/i.test(ua)) return null;
    return hints.bitness === '64' || /Win64|x64|amd64/i.test(ua) ? 'windows-x64' : null;
  }
  if (os === 'macOS') {
    if (hints.architecture === 'arm') return 'macos-arm64';
    if (hints.architecture === 'x86' && hints.bitness === '64') return 'macos-x86_64';
    // MacIntel and "Intel Mac OS X" are also reported by Apple Silicon browsers.
  }
  return null;
}
