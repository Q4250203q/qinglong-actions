const $ = (id) => document.getElementById(id);

function tick() {
  const now = new Date();
  const bj = new Date(now.getTime() + 8 * 3600 * 1000);
  const hh = String(bj.getUTCHours()).padStart(2, "0");
  const mm = String(bj.getUTCMinutes()).padStart(2, "0");
  const ss = String(bj.getUTCSeconds()).padStart(2, "0");
  $("clock").textContent = `${hh}:${mm}:${ss}`;
}

async function j(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "请求失败");
  return data;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function statusClass(status) {
  if (status === "success") return "ok";
  if (!status) return "";
  return "fail";
}

function statusLabel(status) {
  if (status === "success") return "成功";
  if (!status) return "尚未执行";
  return status;
}

function renderTasks(tasks, busy) {
  const box = $("task-list");
  if (!tasks.length) {
    box.innerHTML = '<p class="empty">还没有任务。yyb：先加一条。</p>';
    return;
  }
  box.innerHTML = tasks.map((t) => {
    const last = t.last || {};
    return `
    <article class="task">
      <div class="task-top">
        <div>
          <h4>${escapeHtml(t.name)}</h4>
          <p>${escapeHtml(t.desc || "")}</p>
        </div>
        <div class="row">
          <span class="pill ${t.enabled ? "" : "off"}">${t.enabled ? "启用" : "停用"}</span>
          <span class="pill ${statusClass(last.status)}">${statusLabel(last.status)}</span>
        </div>
      </div>
      <div class="meters">
        <div class="meter"><span>脚本 / cron</span><b>${escapeHtml(t.script)} · ${escapeHtml(t.cron)}</b></div>
        <div class="meter"><span>下次执行</span><b>${escapeHtml(t.next_run || "—")}</b></div>
      </div>
      <div class="row">
        <button class="btn" data-run="${t.id}" ${busy ? "disabled" : ""}>执行</button>
        <button class="btn ghost" data-toggle="${t.id}">切换</button>
        ${last.log ? `<button class="btn ghost" data-log="${escapeHtml(last.log)}">看日志</button>` : ""}
        <button class="btn danger" data-delete="${t.id}" data-name="${escapeHtml(t.name)}" data-script="${escapeHtml(t.script)}">删除</button>
      </div>
    </article>`;
  }).join("");
  box.querySelectorAll("[data-run]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await j(`/api/tasks/${btn.dataset.run}/run`, { method: "POST" });
        refresh();
      } catch (err) {
        $("line-yyb").textContent = err.message;
      }
    };
  });
  box.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await j(`/api/tasks/${btn.dataset.toggle}/toggle`, { method: "POST" });
        refresh();
      } catch (err) {
        $("line-yyb").textContent = err.message;
      }
    };
  });
  box.querySelectorAll("[data-log]").forEach((btn) => {
    btn.onclick = () => {
      $("log-select").value = btn.dataset.log;
      openLog(btn.dataset.log);
    };
  });
  box.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.onclick = async () => {
      const name = btn.dataset.name;
      const script = btn.dataset.script;
      if (!confirm(`从看板删除「${name}」？`)) return;
      const alsoFile = confirm(`同时删除脚本文件 ${script}？\n公共依赖不会删。取消则只下看板。`);
      try {
        const qs = alsoFile ? "?delete_file=1" : "";
        await j(`/api/tasks/${btn.dataset.delete}${qs}`, { method: "DELETE" });
        $("line-yyb").textContent = alsoFile
          ? `已删除任务「${name}」，并尝试移除 ${script}。`
          : `已从看板删除「${name}」。`;
        $("line-shaniu").textContent = "删干净了。柜子里空出一格。";
        refresh();
      } catch (err) {
        $("line-yyb").textContent = err.message;
      }
    };
  });
}

function renderScripts(scripts) {
  const box = $("script-list");
  const badge = $("script-count");
  if (badge) badge.textContent = String((scripts || []).length);
  if (!scripts.length) {
    box.innerHTML = '<p class="empty">scripts/ 里还没有脚本。</p>';
    return;
  }
  box.innerHTML = scripts.map((s) => {
    const used = (s.tasks || []).map((t) => t.name).join("、") || "未挂看板";
    const locked = s.protected;
    return `
    <article class="script-row">
      <div>
        <h5>${escapeHtml(s.name)}</h5>
        <p>${escapeHtml(used)} · ${escapeHtml(String(s.size))}B · ${escapeHtml(s.mtime)}</p>
      </div>
      <button class="btn danger" data-del-script="${escapeHtml(s.name)}" ${locked ? "disabled" : ""}>${locked ? "保护" : "删除脚本"}</button>
    </article>`;
  }).join("");
  box.querySelectorAll("[data-del-script]").forEach((btn) => {
    btn.onclick = async () => {
      const name = btn.dataset.delScript;
      if (!confirm(`删除脚本 ${name}？挂在它上面的看板任务会一起下掉。`)) return;
      try {
        const data = await j(`/api/scripts/${encodeURIComponent(name)}`, { method: "DELETE" });
        const n = (data.removed_tasks || []).length;
        $("line-yyb").textContent = n
          ? `已删除 ${name}，并下掉 ${n} 条看板任务。`
          : `已删除脚本 ${name}。`;
        $("line-shaniu").textContent = "柜子清出一格。需要再传随时喊我。";
        refresh();
      } catch (err) {
        $("line-yyb").textContent = err.message;
      }
    };
  });
}

function renderTimeline(history) {
  const box = $("timeline");
  const rows = [];
  (history || []).slice(0, 8).forEach((batch) => {
    (batch.results || []).forEach((r) => {
      rows.push({
        name: r.name,
        status: r.status,
        time: batch.timestamp,
        elapsed: r.elapsed,
      });
    });
  });
  if (!rows.length) {
    box.innerHTML = '<p class="empty">还没有执行记录。</p>';
    return;
  }
  box.innerHTML = rows.slice(0, 10).map((r) => `
    <div class="tl">
      <div class="dot ${statusClass(r.status)}"></div>
      <div>
        <h5>${escapeHtml(r.name)}</h5>
        <p>${escapeHtml((r.time || "").replace("T", " ").slice(0, 19))} · ${escapeHtml(r.elapsed ?? "-")}s</p>
      </div>
      <span class="pill ${statusClass(r.status)}">${statusLabel(r.status)}</span>
    </div>
  `).join("");
}

async function loadLogs(keep) {
  const logs = await j("/api/logs");
  const sel = $("log-select");
  const current = keep ? sel.value : "";
  sel.innerHTML = `<option value="">选择日志</option>` + logs.map((l) =>
    `<option value="${escapeHtml(l.name)}">${escapeHtml(l.name)} · ${escapeHtml(l.mtime)}</option>`
  ).join("");
  if (current) sel.value = current;
}

async function openLog(name) {
  if (!name) {
    $("log-view").textContent = "选择一条日志查看。";
    return;
  }
  const data = await j(`/api/logs/${encodeURIComponent(name)}`);
  $("log-view").textContent = data.content || "(空)";
}

async function refresh() {
  try {
    const ov = await j("/api/overview");
    $("line-yyb").textContent = ov.lines.yyb;
    $("line-shaniu").textContent = ov.lines.shaniu;
    $("stat-tasks").textContent = ov.task_count;
    $("stat-on").textContent = ov.enabled_count;
    $("stat-due").textContent = ov.due_count ?? 0;
    $("stat-hist").textContent = ov.history_count;
    const site = ov.site || "/";
    const local = /127\.0\.0\.1|localhost/.test(site);
    $("site-link").href = local ? "/" : site;
    const badge = $("busy-badge");
    badge.textContent = ov.busy ? "执行中" : "空闲";
    badge.classList.toggle("busy", ov.busy);
    $("btn-all").disabled = ov.busy;
    const tasks = await j("/api/tasks");
    renderTasks(tasks, ov.busy);
    const scripts = await j("/api/scripts");
    renderScripts(scripts);
    const history = await j("/api/history");
    renderTimeline(history);
    await loadLogs(true);
    const sel = $("log-select");
    if (sel.value) await openLog(sel.value);
  } catch (err) {
    $("line-yyb").textContent = `面板接口异常：${err.message}`;
    $("line-shaniu").textContent = "傻妞先缓一缓，刷新一下再试。";
  }
}

$("btn-refresh").onclick = refresh;
$("btn-all").onclick = async () => {
  try {
    await j("/api/run-all", { method: "POST" });
    refresh();
  } catch (err) {
    $("line-yyb").textContent = err.message;
  }
};
$("log-select").onchange = (e) => openLog(e.target.value);
$("upload-form").onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target;
  const fileInput = form.querySelector('input[name="file"]');
  if (!fileInput.files.length) {
    $("line-yyb").textContent = "先选一个 .py 文件。";
    return;
  }
  const fd = new FormData(form);
  if (!form.add_task.checked) fd.delete("add_task");
  else fd.set("add_task", "1");
  try {
    const res = await fetch("/api/scripts/upload", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "上传失败");
    $("line-yyb").textContent = data.task
      ? `脚本 ${data.script} 已入库并加入看板。`
      : `脚本 ${data.script} 已保存到 scripts/。`;
    $("line-shaniu").textContent = "上传成功！傻妞已经把它收进柜子里。";
    form.reset();
    form.add_task.checked = true;
    refresh();
  } catch (err) {
    $("line-yyb").textContent = err.message;
  }
};

setInterval(tick, 1000);
tick();
refresh();
setInterval(refresh, 4000);
