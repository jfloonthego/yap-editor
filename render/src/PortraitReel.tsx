// A vertical (phone) video: the video fills the whole 9:16 frame so the speaker is never covered. A soft scrim carries the headline at the top,
// captions sit in the lower third, and the brand is a small mark in the corner (name when there is no logo) with an optional tagline pill at the bottom.
import React from "react";
import {AbsoluteFill, Audio, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";

import {BRAND} from "./brand";
import {bodyFont, headlineFont} from "./fonts";
import type {LandscapeProps} from "./types";

export const PortraitReel: React.FC<LandscapeProps> = ({clip, audio, headline, captions, brand: override}) => {
  const brand = {...BRAND, ...(override ?? {})};
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const cue = captions.find((c) => time >= c.from && time <= c.to);
  let opacity = 1;
  if (cue && cue.to - cue.from > 0.2) {
    opacity = interpolate(time, [cue.from, cue.from + 0.08, cue.to - 0.05, cue.to], [0, 1, 1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  }
  return (
    <AbsoluteFill style={{backgroundColor: "#000", fontFamily: bodyFont}}>
      <OffthreadVideo src={staticFile(clip)} muted={Boolean(audio)} style={{width: "100%", height: "100%", objectFit: "cover"}} />
      {audio ? <Audio src={staticFile(audio)} /> : null}
      <div style={{position: "absolute", left: 0, right: 0, top: 0, height: 520, background: "linear-gradient(180deg, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0) 100%)"}} />
      <div style={{position: "absolute", left: 0, right: 0, bottom: 0, height: 420, background: "linear-gradient(0deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 100%)"}} />
      <div style={{position: "absolute", left: 56, right: 56, top: 120, textAlign: "left", fontFamily: headlineFont, fontWeight: 800, fontSize: 70, lineHeight: 1.08, letterSpacing: -1, color: "#fff", textShadow: "0 3px 14px rgba(0,0,0,0.55)"}}>{headline}</div>
      <div style={{position: "absolute", left: 56, top: 44, display: "flex", alignItems: "center", gap: 14}}>
        {brand.logo ? <div style={{background: "#fff", borderRadius: 14, padding: "6px 14px", opacity: 0.95}}><Img src={staticFile(brand.logo)} style={{height: 54, width: "auto", display: "block"}} /></div>
          : <div style={{fontFamily: headlineFont, fontWeight: 800, fontSize: 36, color: "#fff", textShadow: "0 2px 10px rgba(0,0,0,0.6)"}}>{brand.name}</div>}
      </div>
      {cue ? (
        <div style={{position: "absolute", left: 60, right: 60, top: 1180, textAlign: "center"}}>
          <span style={{opacity, fontFamily: bodyFont, fontWeight: 700, fontSize: 64, lineHeight: 1.16, color: "#fff", letterSpacing: -0.5, textShadow: "0 3px 12px rgba(0,0,0,0.75), 0 1px 3px rgba(0,0,0,0.8)"}}>{cue.text.toLowerCase()}</span>
        </div>
      ) : null}
      {brand.tagline || brand.url ? (
        <div style={{position: "absolute", left: 0, right: 0, bottom: 70, display: "flex", flexDirection: "column", alignItems: "center", gap: 10}}>
          {brand.tagline ? <div style={{background: brand.cta, color: brand.ctaText, fontFamily: bodyFont, fontWeight: 700, fontSize: 38, padding: "14px 40px", borderRadius: 999}}>{brand.tagline}</div> : null}
          {brand.url ? <div style={{color: "#fff", fontFamily: bodyFont, fontWeight: 700, fontSize: 30, textShadow: "0 2px 8px rgba(0,0,0,0.7)"}}>{brand.url}</div> : null}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
