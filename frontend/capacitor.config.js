const appUrl = process.env.CAPACITOR_SERVER_URL || "http://10.0.2.2:3000";

module.exports = {
  appId: "com.creatorai.studio",
  appName: "CreatorAI",
  webDir: "public",
  server: {
    // 10.0.2.2 is the host computer from an Android emulator. Set
    // CAPACITOR_SERVER_URL to the deployed HTTPS site for a release build.
    url: appUrl,
    cleartext: appUrl.startsWith("http://"),
  },
};
