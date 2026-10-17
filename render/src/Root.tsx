import React from "react";
import {Composition} from "remotion";

import {LandscapeOnBlack} from "./LandscapeOnBlack";
import {DealWalkthrough} from "./DealWalkthrough";
import {PortraitReel} from "./PortraitReel";
import {DealProps, LandscapeProps} from "./types";

const defaultProps: LandscapeProps = {
  clip: "reels/sample/clip.mp4",
  headline: "the edit is not the hard part",
  captions: [
    {from: 0.0, to: 0.8, text: "Why does every edit take 3 hours"},
    {from: 0.8, to: 1.7, text: "when the talking part took 90 seconds?"},
  ],
  durationInSeconds: 17.61,
  fps: 30,
};

export const Root: React.FC = () => {
  return (
    <>
    <Composition<any, DealProps>
      id="DealWalkthrough"
      component={DealWalkthrough}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={30 * 12}
      defaultProps={{clip: "deals/sample/clip.mp4", headline: "123 Main St", location: "Fresno, CA", facts: "3 bed · 2 bath · 1,450 sqft", price: "$185,000", spread: "$65,000", rent: "$2,100", offerBy: "Oct 30 at 5:00 PM PT", url: "jesemmhomeventures.com/deals", clipDurationInSeconds: 8}}
      calculateMetadata={({props}) => {
        const fps = props.fps ?? 30;
        return {fps, durationInFrames: Math.max(1, Math.round(((props.introSeconds ?? 4) + props.clipDurationInSeconds + (props.outroSeconds ?? 5)) * fps))};
      }}
    />
    <Composition<any, LandscapeProps>
      id="PortraitReel"
      component={PortraitReel}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={Math.round((defaultProps.durationInSeconds ?? 10) * 30)}
      defaultProps={defaultProps}
      calculateMetadata={({props}) => {
        const fps = props.fps ?? 30;
        return {fps, durationInFrames: Math.max(1, Math.round((props.durationInSeconds ?? 10) * fps))};
      }}
    />
    <Composition<any, LandscapeProps>
      id="LandscapeOnBlack"
      component={LandscapeOnBlack}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={Math.round((defaultProps.durationInSeconds ?? 10) * 30)}
      defaultProps={defaultProps}
      calculateMetadata={({props}) => {
        const fps = props.fps ?? 30;
        const durationInSeconds = props.durationInSeconds ?? 10;
        return {
          fps,
          durationInFrames: Math.max(1, Math.round(durationInSeconds * fps)),
        };
      }}
    />
    </>
  );
};
