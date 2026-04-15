const RELEASES_API = 'https://api.github.com/repos/iloveflo/SQLCopilot_DesktopApp_AI_agent/releases';
const RELEASES_PAGE = 'https://github.com/iloveflo/SQLCopilot_DesktopApp_AI_agent/releases';

function inferPlatform(file) {
  const name = file.toLowerCase();
  if (name.endsWith('.exe') || name.endsWith('.msi')) return 'windows';
  if (name.endsWith('.dmg') || name.endsWith('.app.tar.gz')) return 'macOS';
  if (name.endsWith('.appimage') || name.endsWith('.deb') || name.endsWith('.rpm')) return 'linux';
  return 'other';
}

function inferLabel(file) {
  const name = file.toLowerCase();
  if (name.endsWith('.exe')) return 'EXE installer';
  if (name.endsWith('.msi')) return 'MSI installer';
  if (name.endsWith('.dmg')) return 'DMG installer';
  if (name.endsWith('.app.tar.gz')) return 'App tarball';
  if (name.endsWith('.appimage')) return 'AppImage package';
  if (name.endsWith('.deb')) return 'DEB package';
  if (name.endsWith('.rpm')) return 'RPM package';
  return 'Download asset';
}

function inferVersion(release) {
  const versionCandidates = [];

  if (release.tag_name) versionCandidates.push(release.tag_name);
  if (release.name) versionCandidates.push(release.name);
  for (const asset of release.assets || []) versionCandidates.push(asset.name);

  for (const candidate of versionCandidates) {
    const match = String(candidate).match(/(\d+\.\d+\.\d+)/);
    if (match) return match[1];
  }

  return release.tag_name || 'unknown';
}

function normalizeAssets(release) {
  return (release.assets || [])
    .filter((asset) => {
      const lower = asset.name.toLowerCase();
      return (
        !lower.includes('source code') &&
        (lower.endsWith('.exe') ||
          lower.endsWith('.msi') ||
          lower.endsWith('.dmg') ||
          lower.endsWith('.app.tar.gz') ||
          lower.endsWith('.appimage') ||
          lower.endsWith('.deb') ||
          lower.endsWith('.rpm'))
      );
    })
    .map((asset) => ({
      platform: inferPlatform(asset.name),
      label: inferLabel(asset.name),
      file: asset.name,
      url: asset.browser_download_url,
    }));
}

function sortAssets(assets) {
  const order = {
    windows: 1,
    macOS: 2,
    linux: 3,
    other: 4,
  };

  return [...assets].sort((a, b) => {
    const platformDelta = (order[a.platform] || 99) - (order[b.platform] || 99);
    if (platformDelta !== 0) return platformDelta;
    return a.file.localeCompare(b.file);
  });
}

function renderVersion(release) {
  const container = document.getElementById('versionsList');
  const version = inferVersion(release);
  const assets = sortAssets(normalizeAssets(release)).slice(0, 7);

  container.innerHTML = `
    <article class="version-card">
      <div class="version-head">
        <div>
          <h3 class="version-title">SQL Copilot Pro v${version}</h3>
          <p class="version-subtitle">7 gói cài đặt trực tiếp từ release mới nhất</p>
        </div>
        <span class="version-badge">${assets.length} files</span>
      </div>
      <div class="asset-list">
        ${assets
          .map(
            (asset) => `
              <div class="asset-row">
                <span class="asset-platform">${asset.platform}</span>
                <div class="asset-info">
                  <strong>${asset.file}</strong>
                  <span>${asset.label}</span>
                </div>
                <a
                  class="asset-download"
                  href="${asset.url}"
                  data-download-url="${asset.url}"
                  aria-label="Tải ${asset.file}"
                  title="Tải ${asset.file}"
                >
                  ↓
                </a>
              </div>
            `,
          )
          .join('')}
      </div>
    </article>
  `;

  document.getElementById('releaseVersion').textContent = `Phiên bản hiện tại: v${version}`;
  document.getElementById('releaseMeta').textContent =
    `${assets.length} file cài đặt trực tiếp • tự cập nhật từ GitHub Release mới nhất`;
  document.getElementById('allReleasesLink').href = release.html_url || RELEASES_PAGE;
}

function renderError(message) {
  document.getElementById('releaseVersion').textContent = 'Không lấy được release mới nhất';
  document.getElementById('releaseMeta').textContent = message;
  document.getElementById('versionsList').innerHTML = `
    <div class="empty-state">
      Không thể tự động đồng bộ link tải từ GitHub Release lúc này. Bạn có thể mở trang release tổng để tải thủ công:
      <br />
      <a class="inline-link" href="${RELEASES_PAGE}" target="_blank" rel="noreferrer">${RELEASES_PAGE}</a>
    </div>
  `;
}

async function loadLatestRelease() {
  try {
    const response = await fetch(RELEASES_API, {
      headers: {
        Accept: 'application/vnd.github+json',
      },
    });

    if (!response.ok) {
      throw new Error(`GitHub API trả về ${response.status}`);
    }

    const releases = await response.json();
    const latestRelease = releases.find(
      (item) => !item.draft && !item.prerelease && Array.isArray(item.assets) && item.assets.length > 0,
    );

    if (!latestRelease) {
      throw new Error('Không tìm thấy release public có asset');
    }

    renderVersion(latestRelease);

    document.querySelectorAll('.asset-download').forEach((link) => {
      link.addEventListener('click', (event) => {
        event.preventDefault();
        const downloadUrl = link.dataset.downloadUrl;
        if (!downloadUrl) return;
        window.location.assign(downloadUrl);
      });
    });
  } catch (error) {
    console.error('Failed to load latest release:', error);
    renderError('GitHub API hiện không phản hồi hoặc release mới nhất chưa public.');
  }
}

loadLatestRelease();
