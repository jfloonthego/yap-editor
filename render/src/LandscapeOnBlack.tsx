// Geometry measured from the reference reel's frames: 31.7% band, persistent
// headline, and lowercase lower-third captions. Branded: logo card on top, gradient ground,
// three-color line around the band, and a call-to-action pill underneath (see ./brand.ts).

import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import {BRAND} from "./brand";
import {bodyFont, headlineFont} from "./fonts";
import {LandscapeProps} from "./types";

export const W = 1080;
export const H = 1920;
export const VID_W = W;
export const VID_H = Math.round((W / 16) * 9);
export const VID_TOP = Math.round((H - VID_H) / 2);
export const TEMPLATE_DIMS = {width: W, height: H};

export const LandscapeOnBlack: React.FC<LandscapeProps> = ({
  clip,
  audio,
  headline,
  captions,
  brand: brandOverride,
}) => {
  const brand = {...BRAND, ...(brandOverride ?? {})};
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const activeCaption = captions.find((caption) => time >= caption.from && time <= caption.to);

  let captionOpacity = 1;
  if (activeCaption && activeCaption.to - activeCaption.from > 0.2) {
    captionOpacity = interpolate(
      time,
      [activeCaption.from, activeCaption.from + 0.08, activeCaption.to - 0.05, activeCaption.to],
      [0, 1, 1, 0],
      {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
    );
  }
  // For cues at or below 0.2s, four strictly-increasing interpolation stops do
  // not exist in the window and interpolate throws, so opacity stays at 1.

  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${brand.bgTop} 0%, ${brand.bgBottom} 100%)`, fontFamily: bodyFont}}>
      <div style={{position: "absolute", top: 96, left: 0, right: 0, display: "flex", justifyContent: "center"}}>
        {brand.logo ? (
          <div style={{background: "#ffffff", borderRadius: 32, padding: "20px 34px", boxShadow: "0 12px 40px rgba(0,0,0,0.35)"}}>
            <Img src={staticFile(brand.logo)} style={{height: 170, width: "auto", display: "block"}} />
          </div>
        ) : (
          <div style={{fontFamily: headlineFont, fontWeight: 800, fontSize: 70, color: brand.textColor, letterSpacing: -1}}>{brand.name}</div>
        )}
      </div>
      {[VID_TOP - 10, VID_TOP + VID_H].map((y) => (
        <div key={y} style={{position: "absolute", left: 0, width: W, top: y, height: 10, background: `linear-gradient(90deg, ${brand.accentFrom}, ${brand.accentMid}, ${brand.accentTo})`}} />
      ))}
      <div
        style={{
          position: "absolute",
          top: VID_TOP,
          left: 0,
          width: VID_W,
          height: VID_H,
          overflow: "hidden",
        }}
      >
        <OffthreadVideo
          src={staticFile(clip)}
          muted={Boolean(audio)}
          style={{
            width: VID_W,
            height: VID_H,
            objectFit: "cover",
            display: "block",
          }}
        />
        {audio ? <Audio src={staticFile(audio)} /> : null}
        {activeCaption ? (
          <div
            style={{
              position: "absolute",
              left: 54,
              right: 54,
              top: Math.round(VID_H * 0.6),
              pointerEvents: "none",
            }}
          >
            <span
              style={{
                opacity: captionOpacity,
                fontFamily: bodyFont,
                fontSize: 60,
                fontWeight: 700,
                color: "#ffffff",
                lineHeight: 1.14,
                letterSpacing: -0.5,
                display: "inline",
                textShadow: "0 2px 10px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.7)",
              }}
            >
              {activeCaption.text.toLowerCase()}
            </span>
          </div>
        ) : null}
      </div>
      <div
        style={{
          position: "absolute",
          left: 60,
          right: 60,
          bottom: H - VID_TOP + 26,
          textAlign: "center",
          fontFamily: headlineFont,
          fontSize: 64,
          fontWeight: 800,
          color: "#ffffff",
          lineHeight: 1.12,
          letterSpacing: -1,
        }}
      >
        {headline}
      </div>
      <div style={{position: "absolute", left: 0, right: 0, top: VID_TOP + VID_H + 90, display: "flex", flexDirection: "column", alignItems: "center", gap: 18}}>
        {brand.tagline ? <div style={{background: brand.cta, color: brand.ctaText, fontFamily: bodyFont, fontWeight: 700, fontSize: 46, padding: "20px 48px", borderRadius: 999}}>{brand.tagline}</div> : null}
        {brand.url ? <div style={{color: brand.textColor, opacity: 0.85, fontFamily: bodyFont, fontWeight: 700, fontSize: 36, letterSpacing: 1}}>{brand.url}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
