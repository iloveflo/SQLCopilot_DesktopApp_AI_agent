import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const version = process.argv[2];

if (!version) {
  console.error('Usage: node scripts/sync-version.mjs <version>');
  process.exit(1);
}

if (!/^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(version)) {
  console.error(`Invalid version: ${version}`);
  process.exit(1);
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');

function updateJsonVersion(filePath) {
  const absolutePath = path.join(frontendDir, filePath);
  const content = readFileSync(absolutePath, 'utf8');
  const data = JSON.parse(content);
  data.version = version;

  if (data.packages?.['']) {
    data.packages[''].version = version;
  }

  writeFileSync(absolutePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

function updateCargoVersion(filePath) {
  const absolutePath = path.join(frontendDir, filePath);
  const content = readFileSync(absolutePath, 'utf8');
  const updated = content.replace(
    /^version\s*=\s*"[^\"]+"$/m,
    `version = "${version}"`,
  );

  if (updated === content) {
    console.error(`Could not update version in ${filePath}`);
    process.exit(1);
  }

  writeFileSync(absolutePath, updated, 'utf8');
}

updateJsonVersion('package.json');
updateJsonVersion('package-lock.json');
updateJsonVersion(path.join('src-tauri', 'tauri.conf.json'));
updateCargoVersion(path.join('src-tauri', 'Cargo.toml'));

console.log(`Synchronized frontend app version to ${version}`);
