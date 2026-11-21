const portrait = document.querySelector("#portrait");
const age = document.querySelector("#age");
const emotion = document.querySelector("#emotion");
const signal = document.querySelector("#signal");
const demo = document.querySelector("#demo");
const notice = document.querySelector("#notice");
const buttons = [...document.querySelectorAll("[data-care]")];
const help = document.querySelector("#help");
let ready = false;
let caring = false;
let careVersion = 0;

function setControls() {
  buttons.forEach(button => { button.disabled = !ready || caring; });
}

function show(state) {
  portrait.dataset.face = state.action.face;
  age.textContent = `가상 월령 ${state.age_months}개월`;
  if (emotion.textContent !== state.emotion) emotion.textContent = state.emotion;
  signal.textContent = state.signal || "";
  signal.hidden = !state.signal;
  demo.hidden = !state.demo;
}

async function request(path, options) {
  const response = await fetch(path, { signal: AbortSignal.timeout(5000), ...options });
  if (!response.ok) throw new Error("요청에 실패했어요.");
  return response.json();
}

async function poll() {
  const version = careVersion;
  try {
    if (caring) return;
    const state = await request("/api/baby");
    if (version === careVersion) {
      show(state);
      if (!ready) notice.textContent = "";
      ready = true;
    }
  } catch {
    if (version === careVersion) {
      ready = false;
      notice.textContent = "아기 상태에 연결할 수 없어요. 다시 연결하고 있어요.";
    }
  } finally {
    setControls();
    setTimeout(poll, 1000);
  }
}

buttons.forEach(button => button.addEventListener("click", async () => {
  if (caring || !ready) return;
  caring = true;
  careVersion += 1;
  setControls();
  try {
    const state = await request("/api/baby/care", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: button.dataset.care }),
    });
    show(state);
    notice.textContent = "";
  } catch {
    notice.textContent = "돌봄 요청을 확인할 수 없어요. 화면에서 아기의 상태를 확인해 주세요.";
  } finally {
    caring = false;
    setControls();
  }
}));

document.querySelector('.top a').addEventListener("click", () => { help.open = true; });
request("/api/baby/sources").then(sources => {
  const list = document.querySelector("#sources");
  for (const { name, url } of sources) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = url;
    link.textContent = name;
    link.rel = "noreferrer";
    item.append(link);
    list.append(item);
  }
}).catch(() => {
  const item = document.createElement("li");
  item.textContent = "자료 출처는 저장소의 docs/baby_behavior/sources.csv에서 확인할 수 있어요.";
  document.querySelector("#sources").append(item);
});

poll();
