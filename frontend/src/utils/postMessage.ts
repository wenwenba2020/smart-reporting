/**
 * Send a structured message from the host page to an iframe or parent window.
 * Used for WorkPilot integration (Task 17).
 */
export function postMessageToParent(type: string, payload: unknown): void {
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ source: 'smart_reporting', type, payload }, '*');
  }
}

export function postMessageToIframe(
  iframe: HTMLIFrameElement,
  type: string,
  payload: unknown
): void {
  iframe.contentWindow?.postMessage(
    { source: 'smart_reporting', type, payload },
    '*'
  );
}
