// ---------------------------------------------------------------- boot
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key.toLowerCase() === "n") {
    e.preventDefault();
    location.hash = "";
    go("chat");
  }
});
$("#achbtn").onclick = () => achRefresh().then(() => achGallery());
applyAch();
(async () => {
  try {
    const c = await api("/api/crypto");
    if (c.on && !c.open) {
      await loadLang();
      unlockScreen();
      return;
    }
  } catch (e) {}
  try {
    const a = await api("/api/agent");
    const pt = a.profile && a.profile.ui_theme;
    if (pt && !LS.get("theme_set", false)) {
      setTheme({ mode: pt });
      LS.set("theme_set", true);
    }
    MEM.on = !a.profile || a.profile.memory_on !== false;
    MEM.asked = !a.profile || a.profile.memory_on !== false || !!a.profile.memory_asked;
    document.body.classList.toggle("mem-off", !MEM.on);
    const pl = a.profile && a.profile.lang;
    if (pl && pl !== I18N.lang) {
      I18N.lang = pl;
      LS.set("lang", pl);
    }
  } catch (e) {}
  await loadLang();
  if (I18N.lang !== "ru") i18nTree(document.body); // the side rail, titles and everything already on the page
  drawLangBtn();
  try {
    APP = await api("/api/app/info");
  } catch (e) {}
  if (APP.desktop) {
    updateLoad();
    setTimeout(updateLoad, 35000); // the quiet check starts half a minute after launch
    setInterval(updateLoad, 30 * 60 * 1000);
  }
  const [v, ...argl] = location.hash.slice(1).split("/"),
    arg = argl.join("/");
  go(v || "chat", arg);
  hideSplash();
  badge();
  setInterval(badge, 20000);
  try {
    const d = await api("/api/local");
    if (!APP.demo && !d.offer && !d.catalog.some((m) => m.installed) && d.engine) {
      const c = await post("/api/local/offer", { state: "shown", claim: true }).catch(() => ({}));
      if (c.claimed) setTimeout(() => welcomeFlow(), 700);
    }
  } catch (e) {}
  setTimeout(() => {
    if (!MEM.asked && !APP.demo && !$(".wlc")) memAsk(); // the tour didn't run (a model already here): ask alone
  }, 1600);
})();
setTimeout(sourcesAsk, 1500);
