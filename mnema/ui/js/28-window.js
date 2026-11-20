// ---------------------------------------------------------------- closing the window (desktop)
window.mnemaAskClose = function () {
  if ($(".closebox")) return;
  const pop = document.createElement("div");
  pop.className = "modal";
  pop.innerHTML = `<div class="card closebox"><button class="lmx" data-x title="Отмена">×</button><h2>Закрыть Mnemai?</h2><div class="opt">
     <button data-c="tray"><div class="cpic tray"><div class="cw"><i></i><i></i><i></i></div><div class="tb"><span class="tl"><em></em></span><span class="tc"></span><span class="tc"></span></div></div><div><b>Свернуть в трей</b><span>Окно спрячется, Mnemai продолжит учиться</span></div></button>
     <button data-c="quit"><div class="cpic quit"><div class="cw"><i></i><i></i><i></i></div><div class="zz"><b>z</b><b>z</b><b>z</b></div></div><div><b>Закрыть совсем</b><span>Обучение остановится до следующего запуска</span></div></button></div>
   <label><input type="checkbox" id="crem"> Запомнить выбор — поменять можно в настройках</label></div>`;
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  $("[data-x]", pop).onclick = () => pop.remove(); // changed my mind: the window stays
  $$("[data-c]", pop).forEach(
    (b) =>
      (b.onclick = () => {
        const rem = $("#crem").checked;
        pop.remove();
        if (window.pywebview && window.pywebview.api.close_choice) window.pywebview.api.close_choice(b.dataset.c, rem);
      }),
  );
};

// ---------------------------------------------------------------- open network settings (tray → desktop)
window.mnemaOpenNet = function () {
  if (location.hash === "#settings/net") go("settings", "net");
  else location.hash = "settings/net";
};
