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
