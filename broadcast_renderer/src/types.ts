export type GraphicKind = 'scoreboard' | 'bottom' | 'profile' | 'prematch' |
  'intermission' | 'lineups' | 'top_scorers' | 'standings' | 'penalties' | 'score';

export interface GoalPhase {
  phase: string;
  key: string;
  overlay: boolean;
  reveal: boolean;
  elapsed: number;
  duration: number;
}

export interface DetailOptions {
  duration?: number;
  start?: number;
  stagger?: number;
  distance?: number;
}

declare global {
  interface Window {
    SPBroadcastMotion: typeof import('./motion').BroadcastMotion;
    startSecretariatOverlay: () => void;
    secretariatStudioReady?: boolean;
  }
}
