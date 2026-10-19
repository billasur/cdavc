import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const vendorDirectory = dirname(fileURLToPath(import.meta.url));
const showcaseDirectory = dirname(vendorDirectory);
const manifestPath = join(vendorDirectory, "manifest.json");
const lockPath = join(showcaseDirectory, "package-lock.json");

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));
const sha256 = (contents) => createHash("sha256").update(contents).digest("hex");

const manifest = await readJson(manifestPath);
const lockfile = await readJson(lockPath);
const rootPackage = lockfile.packages?.[""];

if (!rootPackage || lockfile.lockfileVersion !== 3) {
  throw new Error("showcase/package-lock.json must be an npm lockfile v3");
}

for (const [packageName, packageInfo] of Object.entries(manifest.packages)) {
  const expectedVersion = packageInfo.version;
  const declaredVersion = rootPackage.devDependencies?.[packageName];
  const lockedPackage = lockfile.packages?.[`node_modules/${packageName}`];

  if (declaredVersion !== expectedVersion) {
    throw new Error(`${packageName}: package.json is not pinned to ${expectedVersion}`);
  }
  if (lockedPackage?.version !== expectedVersion) {
    throw new Error(`${packageName}: package-lock.json is not pinned to ${expectedVersion}`);
  }

  for (const [packageEntry, vendoredName] of Object.entries(packageInfo.entries)) {
    const vendoredPath = join(vendorDirectory, vendoredName);
    const contents = await readFile(vendoredPath);
    if (!contents.length) {
      throw new Error(`${vendoredName}: vendored file is empty`);
    }
    if (!manifest.files?.[vendoredName]) {
      throw new Error(`${vendoredName}: missing manifest checksum`);
    }
    if (sha256(contents) !== manifest.files[vendoredName]) {
      throw new Error(`${vendoredName}: SHA-256 checksum mismatch`);
    }
    process.stdout.write(`verified ${packageName}@${expectedVersion} ${packageEntry} -> ${vendoredName}\n`);
  }
}

for (const [fileName, expectedHash] of Object.entries(manifest.files)) {
  const contents = await readFile(join(vendorDirectory, fileName));
  if (sha256(contents) !== expectedHash) {
    throw new Error(`${fileName}: SHA-256 checksum mismatch`);
  }
}

process.stdout.write(`verified ${Object.keys(manifest.files).length} checked-in vendor files\n`);
