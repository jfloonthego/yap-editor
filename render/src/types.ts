export type Caption = {
  from: number;
  to: number;
  text: string;
};

import type {Brand} from "./brand";

export type LandscapeProps = {
  clip: string;
  audio?: string;
  headline: string;
  captions: Caption[];
  durationInSeconds?: number;
  fps?: number;
  brand?: Partial<Brand>;
};

// A Dispo deal walkthrough (see DealWalkthrough.tsx). Prices are pre-formatted strings such as "$165,000".
export type DealProps = {
  clip: string;
  headline: string;          // the street address, or the city when the address is hidden
  location?: string;
  facts?: string;            // "2 bed · 1 bath · 992 sqft"
  price?: string;
  spread?: string;
  rent?: string;
  offerBy?: string;          // "Oct 26 at 12:12 PM PT"
  url: string;               // where buyers make an offer
  clipDurationInSeconds: number;
  introSeconds?: number;
  outroSeconds?: number;
  fps?: number;
  brand?: Partial<Brand>;
};
