// A Dispo deal walkthrough: a branded intro card (address or area, the facts, price and spread), your footage, and a branded outro that tells
// buyers how to make an offer. 16:9, 1920x1080. Brand comes from ./brand.ts.
import React from "react";
import {AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";

import {BRAND} from "./brand";
import {bodyFont, headlineFont} from "./fonts";
import type {DealProps} from "./types";

export const DEAL_W = 1920;
export const DEAL_H = 1080;

const fade = (frame: number, total: number, edge = 10) =>
  interpolate(frame, [0, edge, total - edge, total], [0, 1, 1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});

const Ground: React.FC<{children: React.ReactNode; brand: typeof BRAND}> = ({children, brand}) => (
  <AbsoluteFill style={{background: `linear-gradient(135deg, ${brand.bgTop} 0%, ${brand.bgBottom} 100%)`, fontFamily: bodyFont, alignItems: "center", justifyContent: "center"}}>
    <div style={{position: "absolute", left: 0, right: 0, bottom: 0, height: 14, background: `linear-gradient(90deg, ${brand.accentFrom}, ${brand.accentMid}, ${brand.accentTo})`}} />
    {children}
  </AbsoluteFill>
);

const Chip: React.FC<{label: string; value: string; accent?: boolean; brand: typeof BRAND}> = ({label, value, accent, brand}) => (
  <div style={{textAlign: "center", padding: "0 38px"}}>
    <div style={{fontSize: 30, letterSpacing: 3, textTransform: "uppercase", opacity: 0.75, color: "#fff"}}>{label}</div>
    <div style={{fontFamily: headlineFont, fontWeight: 800, fontSize: 88, color: accent ? brand.accentTo : "#fff", lineHeight: 1.1}}>{value}</div>
  </div>
);

export const DealWalkthrough: React.FC<DealProps> = (props) => {
  const {clip, headline, location, facts, price, spread, rent, offerBy, url, introSeconds = 4, outroSeconds = 5, clipDurationInSeconds, brand: override} = props;
  const brand = {...BRAND, ...(override ?? {})};
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const introF = Math.round(introSeconds * fps), outroF = Math.round(outroSeconds * fps), clipF = Math.round(clipDurationInSeconds * fps);

  const logo = (
    brand.logo ? (
      <div style={{background: "#fff", borderRadius: 28, padding: "18px 30px", boxShadow: "0 12px 40px rgba(0,0,0,0.35)"}}>
        <Img src={staticFile(brand.logo)} style={{height: 150, width: "auto", display: "block"}} />
      </div>
    ) : (
      <div style={{fontFamily: headlineFont, fontWeight: 800, fontSize: 84, color: "#fff"}}>{brand.name}</div>
    )
  );

  return (
    <AbsoluteFill style={{backgroundColor: "#000"}}>
      <Sequence from={0} durationInFrames={introF}>
        <Ground brand={brand}>
          <div style={{opacity: fade(frame, introF), display: "flex", flexDirection: "column", alignItems: "center", gap: 34, textAlign: "center", padding: "0 120px"}}>
            {logo}
            <div style={{fontFamily: headlineFont, fontWeight: 800, fontSize: 96, color: "#fff", lineHeight: 1.08}}>{headline}</div>
            {location && location !== headline ? <div style={{fontSize: 48, color: "#fff", opacity: 0.85}}>{location}</div> : null}
            {facts ? <div style={{fontSize: 52, fontWeight: 700, color: brand.accentTo}}>{facts}</div> : null}
            <div style={{display: "flex", marginTop: 8}}>
              {price ? <Chip label="Price" value={price} brand={brand} /> : null}
              {spread ? <Chip label="Est. spread" value={spread} accent brand={brand} /> : null}
              {rent ? <Chip label="Est. rent" value={rent} brand={brand} /> : null}
            </div>
          </div>
        </Ground>
      </Sequence>

      <Sequence from={introF} durationInFrames={clipF}>
        <AbsoluteFill>
          <OffthreadVideo src={staticFile(clip)} style={{width: DEAL_W, height: DEAL_H, objectFit: "cover"}} />
          {brand.logo ? (
            <div style={{position: "absolute", top: 36, right: 36, background: "#fff", borderRadius: 16, padding: "8px 16px", opacity: 0.92}}>
              <Img src={staticFile(brand.logo)} style={{height: 64, width: "auto", display: "block"}} />
            </div>
          ) : null}
        </AbsoluteFill>
      </Sequence>

      <Sequence from={introF + clipF} durationInFrames={outroF}>
        <Ground brand={brand}>
          <div style={{opacity: fade(frame - introF - clipF, outroF), display: "flex", flexDirection: "column", alignItems: "center", gap: 36, textAlign: "center", padding: "0 120px"}}>
            {logo}
            <div style={{fontFamily: headlineFont, fontWeight: 800, fontSize: 104, color: "#fff", lineHeight: 1.08}}>Make your offer</div>
            {offerBy ? <div style={{fontSize: 56, fontWeight: 700, color: brand.accentTo}}>Offers due {offerBy}</div> : null}
            <div style={{background: brand.cta, color: brand.ctaText, fontWeight: 700, fontSize: 60, padding: "26px 70px", borderRadius: 999}}>{url}</div>
            {brand.tagline ? <div style={{fontSize: 40, color: "#fff", opacity: 0.85}}>{brand.tagline}</div> : null}
          </div>
        </Ground>
      </Sequence>
    </AbsoluteFill>
  );
};
