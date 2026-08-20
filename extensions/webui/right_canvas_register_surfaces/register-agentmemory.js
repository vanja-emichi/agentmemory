function waitForElement(selector, timeoutMs = 3000) {
  const found = document.querySelector(selector);
  if (found) return Promise.resolve(found);
  return new Promise((resolve) => {
    const timeout = globalThis.setTimeout(() => {
      observer.disconnect();
      resolve(document.querySelector(selector));
    }, timeoutMs);
    const observer = new MutationObserver(() => {
      const element = document.querySelector(selector);
      if (!element) return;
      globalThis.clearTimeout(timeout);
      observer.disconnect();
      resolve(element);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
}

export default async function registerAgentMemorySurface(canvas) {
  canvas.registerSurface({
    id: "agentmemory",
    title: "Memory",
    icon: "memory",
    order: 45,
    modalPath: "/plugins/agentmemory/webui/main.html",
    async open() {
      const panel = await waitForElement('[data-surface-id="agentmemory"] .agentmemory-panel');
      if (!panel) throw new Error("AgentMemory surface panel did not mount.");
    },
    async close() {},
  });
}
