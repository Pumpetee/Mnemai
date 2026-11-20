// ---------------------------------------------------------------- VPN in one click
// proxy apps open a local port: we find it and connect; tunnel apps (OpenVPN, WireGuard, Amnezia) wrap the whole system
const VPN_APPS = [
  ["Hiddify", "proxy", [12334, 12335]],
  ["Happ", "proxy", [10808, 10809]],
  ["v2rayN", "proxy", [10808, 10809]],
  ["Clash", "proxy", [7890, 7897]],
  ["NekoRay", "proxy", [2080, 2081]],
  ["OpenVPN", "tunnel"],
  ["WireGuard", "tunnel"],
  ["AmneziaVPN", "tunnel"],
];
let VPN_SCAN = null;
function vpnScan(force) {
  if (force || !VPN_SCAN)
    VPN_SCAN = api("/api/net/detect").catch(() => ({
      proxies: [],
      tunnels: [],
    }));
  return VPN_SCAN;
}
function vpnMatch(d, [name, kind, ports]) {
  if (kind === "tunnel")
    return (d.tunnels || []).some((t) => t.toLowerCase().startsWith(name.toLowerCase().slice(0, 6)))
      ? { tunnel: true }
      : null;
  return (
    (d.proxies || []).find((p) => p.name.toLowerCase().startsWith(name.toLowerCase().slice(0, 4))) ||
    (d.proxies || []).find((p) => (ports || []).includes(p.port)) ||
    null
  );
}
function vpnButtons() {
  return `<div class="vpngrid">${VPN_APPS.map((a) => `<button class="vpnb" data-vpn="${a[0]}"><i class="vdot"></i><span class="vlogo">${esc(a[0].slice(0, 1))}</span><b>${esc(a[0])}</b><small>${a[1] === "tunnel" ? tr("на всю систему") : tr("через прокси")}</small></button>`).join("")}
  <button class="vpnb" data-vpn="manual"><i class="vdot"></i><span class="vlogo">${ic("set")}</span><b>${tr("Другой")}</b><small>${tr("вписать вручную")}</small></button></div><div class="vpnmsg"></div>`;
}
async function bindVpnButtons(box, onConnect, onManual) {
  const msg = $(".vpnmsg", box);
  const mark = (d) =>
    $$("[data-vpn]", box).forEach((b) => {
      const a = VPN_APPS.find((x) => x[0] === b.dataset.vpn);
      if (!a) return;
      const hit = vpnMatch(d, a);
      b.classList.toggle("live", !!hit);
      b.title = hit ? tr("Запущен на этом компьютере") : "";
    });
  vpnScan().then(mark);
  $$("[data-vpn]", box).forEach(
    (b) =>
      (b.onclick = async () => {
        const name = b.dataset.vpn;
        if (name === "manual") {
          onManual();
          return;
        }
        const a = VPN_APPS.find((x) => x[0] === name);
        $$(".vpnb", box).forEach((x) => x.classList.remove("sel"));
        b.classList.add("sel", "busy");
        msg.className = "vpnmsg";
        msg.innerHTML = `<span class="hint">${tr("Ищу")} ${esc(name)}…</span>`;
        const d = await vpnScan(true);
        mark(d);
        b.classList.remove("busy");
        const hit = vpnMatch(d, a);
        if (hit && hit.tunnel) {
          await onConnect("", name);
          msg.className = "vpnmsg ok";
          msg.innerHTML = `${ic("check")}<span><b>${esc(name)}</b> ${tr("работает на всю систему — Mnemai идёт через него сама. Больше ничего не нужно.")}</span>`;
          return;
        }
        if (hit) {
          await onConnect(hit.url, name);
          msg.className = "vpnmsg ok";
          msg.innerHTML = `${ic("check")}<span><b>${esc(name)}</b> ${tr("подключён")}: ${esc(hit.url.replace("://", " · "))} · ${hit.ms} ${tr("мс")}. ${tr("Все запросы к ИИ идут через него.")}</span>`;
          return;
        }
        msg.className = "vpnmsg no";
        msg.innerHTML = `${ic("x")}<span>${a[1] === "tunnel" ? `${esc(name)} ${tr("не запущен. Открой его и подключись — Mnemai пойдёт через него сама, настраивать ничего не нужно.")}` : `${esc(name)} ${tr("не найден. Открой")} ${esc(name)}, ${tr("включи подключение и нажми эту кнопку ещё раз — или введи ключ вручную, Mnemai подключится сама.")}`}</span><button class="btn l sm" data-again>${tr("Проверить ещё раз")}</button><button class="btn g sm" data-vkmanual3>${tr("Ввести ключ вручную")}</button>`;
        $("[data-again]", msg).onclick = () => b.click();
        $("[data-vkmanual3]", msg).onclick = () => {
          // auto-detect failed: lead to the manual key entry in the VPN card
          const nb = $("#netcard");
          if (!nb) return;
          const mb = $("#vkbox", nb);
          mb.hidden = false;
          $("#vkkey", nb).focus();
          nb.scrollIntoView({ behavior: "smooth", block: "start" });
        };
      }),
  );
}
