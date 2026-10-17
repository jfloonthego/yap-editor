// The reel's brand. Edit this file (and render/public/brand/logo.png) to rebrand; a reel's props.json can also override any field under "brand".
// Defaults are Jesemm Home Ventures: the palette, fonts and tagline of jesemmhomeventures.com.
export type Brand = {
  name: string;          // shown instead of the logo when there is none
  logo: string | null;   // file under render/public, or null for no logo
  textColor: string;
  bgTop: string;         // background gradient, top
  bgBottom: string;      // background gradient, bottom
  accentFrom: string;    // the three-color line above and below the video band
  accentMid: string;
  accentTo: string;
  cta: string;           // call-to-action pill color
  ctaText: string;
  tagline: string;       // text in the pill under the band ("" to hide it)
  url: string;           // small line under the pill ("" to hide)
};

export const BRAND: Brand = {
  name: "Jesemm Home Ventures",
  textColor: "#ffffff",
  logo: "brand/logo.png",
  bgTop: "#232050",
  bgBottom: "#35316b",
  accentFrom: "#3f5ba9",
  accentMid: "#62c4cc",
  accentTo: "#fbcf6e",
  cta: "#fbcf6e",
  ctaText: "#35316b",
  tagline: "We buy houses, simple and easy",
  url: "jesemmhomeventures.com",
};
