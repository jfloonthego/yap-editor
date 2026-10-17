import {ARCHIVO_800, SOURCE_SANS_700} from "./assets/brandfonts";

/**
 * Archivo (headline) and Source Sans 3 (captions, call to action), the same typefaces as
 * jesemmhomeventures.com, SIL OFL. They are inlined as data URIs in ./assets/brandfonts.ts
 * and registered with plain @font-face rules.
 *
 * There is deliberately no delayRender() here. Every version of this file that held a render
 * handle open until the font settled eventually killed a cold-clone render, because a handle
 * that never clears is fatal while a font that never loads is merely ugly (a font served from
 * public/ competes with the OffthreadVideo frame server and can hang forever under render
 * concurrency). A data URI cannot be starved: the bytes are already in the bundle when the style
 * rule is parsed, and font-display: swap guarantees text is painted either way.
 */

export const headlineFont = '"Archivo", Arial, Helvetica, sans-serif';
export const bodyFont = '"Source Sans 3", Arial, Helvetica, sans-serif';

const STYLE_ID = "brand-fonts-face";

if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = [
    `@font-face{font-family:"Archivo";src:url(${ARCHIVO_800}) format("woff2");font-weight:800;font-style:normal;font-display:swap;}`,
    `@font-face{font-family:"Source Sans 3";src:url(${SOURCE_SANS_700}) format("woff2");font-weight:700;font-style:normal;font-display:swap;}`,
  ].join("");
  document.head.appendChild(style);
}
