

const SOCIAL_BAR_ID = process.env.NEXT_PUBLIC_ADSTERRA_SOCIAL_BAR_ID || "YOUR_SOCIAL_BAR_ID";
const DIRECT_LINK_URL =
  process.env.NEXT_PUBLIC_ADSTERRA_DIRECT_LINK_URL ||
  "https://www.adsterra.com";


export function loadSocialBar() {
  if (typeof window === "undefined" || SOCIAL_BAR_ID === "YOUR_SOCIAL_BAR_ID") {
    return { cleanup: () => {} };
  }

  const script = document.createElement("script");
  script.type = "text/javascript";
  script.src = `//pl${SOCIAL_BAR_ID}.profitablegatecpm.com/${SOCIAL_BAR_ID}.js`;
  script.async = true;
  script.dataset.adsterra = "social-bar";

  document.body.appendChild(script);

  return {
    cleanup: () => {
      const existing = document.querySelector('[data-adsterra="social-bar"]');
      if (existing) {
        existing.remove();
      }
    },
  };
}


export function triggerDirectLink() {
  if (typeof window === "undefined" || DIRECT_LINK_URL === "https://www.adsterra.com") {
    return;
  }

  window.open(DIRECT_LINK_URL, "_blank", "noopener,noreferrer");
}
