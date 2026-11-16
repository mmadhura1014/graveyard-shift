import "@testing-library/jest-dom";

// jsdom does not implement the async Clipboard API; stub it so copy-button
// tests can verify the onCopied callback fires. Real browsers use the native API.
if (!navigator.clipboard) {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: () => Promise.resolve() },
    configurable: true,
  });
} else if (!navigator.clipboard.writeText) {
  navigator.clipboard.writeText = () => Promise.resolve();
}
