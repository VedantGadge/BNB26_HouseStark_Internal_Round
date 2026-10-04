import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const candidates = [
  process.env.JAVA_HOME,
  process.platform === "darwin"
    ? "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
    : undefined,
].filter(Boolean);

const javaHome = candidates.find((candidate) => {
  const java = join(candidate, "bin", process.platform === "win32" ? "java.exe" : "java");
  if (!existsSync(java)) return false;
  const result = spawnSync(java, ["-version"], { encoding: "utf8" });
  return /version "21(?:\.|\")/.test(`${result.stdout}${result.stderr}`);
});

if (!javaHome) {
  console.error("Android builds require JDK 21. Set JAVA_HOME to a JDK 21 installation.");
  process.exit(1);
}

const env = { ...process.env, JAVA_HOME: javaHome };
const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, { stdio: "inherit", env, ...options });
  if (result.status !== 0) process.exit(result.status ?? 1);
};

run(process.platform === "win32" ? "npx.cmd" : "npx", ["cap", "sync", "android"]);
run(process.platform === "win32" ? "gradlew.bat" : "./gradlew", ["assembleDebug"], {
  cwd: "android",
});
